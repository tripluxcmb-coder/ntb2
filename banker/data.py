"""Read backend snapshots. A zero or null is a confirmed zero, never an error."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


class DataError(ValueError):
    pass


def clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").strip().split())


def entity_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def normalize_cif(value: str) -> str:
    value = clean(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise DataError("Enter an exact CIF using letters, digits, underscores or hyphens.")
    return value


def parse_amount(value: str) -> int | None:
    """None records a source null during merging; it becomes final zero afterward."""
    value = clean(value)
    if value.casefold() in {"", "null", "none", "nan", "na", "n/a"}:
        return None
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?", value):
        raise DataError("Amounts must be numeric, with at most two decimal places.")
    amount = Decimal(value.replace(",", ""))
    if abs(amount) > Decimal("1000000000000000"):
        raise DataError("Amount is outside the supported numeric range.")
    return int(amount * 100)


def parse_month(value: str) -> str | None:
    month_names = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
    match = re.fullmatch(r"([A-Za-z]{3,9})[- /](\d{2}|\d{4})", value)
    if match and match[1][:3].lower() in month_names:
        year = int(match[2]) + (2000 if len(match[2]) == 2 else 0)
        return f"{year:04d}-{month_names[match[1][:3].lower()]:02d}"
    if re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", value):
        return date.fromisoformat(value if len(value) == 10 else value + "-01").strftime("%Y-%m")
    serial = value.replace(",", "")
    if serial.isdigit() and 30000 <= int(serial) <= 80000:
        return (date(1899, 12, 30) + timedelta(days=int(serial))).strftime("%Y-%m")
    return None


def csv_rows(raw: bytes) -> list[list[str]]:
    if not raw or len(raw) > 50 * 1024 * 1024:
        raise DataError("Backend CSV must be nonempty and smaller than 50 MB.")
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeError:
        text = raw.decode("cp1252")
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error:
        raise DataError("The backend CSV could not be parsed.") from None
    if len(rows) < 2 or len(rows) > 250001:
        raise DataError("Backend CSV must contain between one and 250,000 data rows.")
    return rows


@dataclass
class Series:
    cif: str
    product: str
    side: str
    values: dict[str, int]
    rows: tuple[int, ...]


@dataclass
class Snapshot:
    names: dict[str, str]
    aliases: dict[str, list[str]]
    series: list[Series]
    months: list[str]
    opening: str
    sha256: str
    row_count: int


def load_balances(source: bytes | str | Path) -> Snapshot:
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    rows = csv_rows(raw)
    headers = [clean(v) for v in rows[0]]
    if len(headers) != len(set(headers)):
        raise DataError("Backend CSV contains duplicate column names.")
    required = {"CIF", "Customer Full Name", "Product", "Payment Type"}
    if not required <= set(headers):
        raise DataError("Backend CSV requires CIF, Customer Full Name, Product and Payment Type.")
    idx = {h: i for i, h in enumerate(headers)}
    baseline = [h for h in headers if entity_key(h) in {"yearendbalance", "openingbalance"}]
    if len(baseline) != 1:
        raise DataError("Include one year End Balance column for the previous December opening balance.")
    month_columns = {}
    for header in headers:
        if header in required or header in baseline:
            continue
        month = parse_month(header)
        if month is None:
            if any(i < len(r) and clean(r[i]) for r in rows[1:] for i in [idx[header]]):
                raise DataError(f"Unrecognized backend column {header!r}.")
            continue
        if month in month_columns:
            raise DataError("Multiple source columns refer to the same month.")
        month_columns[month] = idx[header]
    months = sorted(month_columns)
    if not months:
        raise DataError("No reporting month exists in the backend file.")
    if len({m[:4] for m in months}) != 1:
        raise DataError("Use one calendar year's monthly columns with its previous December opening.")
    opening = f"{int(months[0][:4])-1}-12"
    columns = {opening: idx[baseline[0]], **month_columns}
    cells = defaultdict(list)
    source_rows = defaultdict(list)
    aliases = defaultdict(list)
    display_choices = defaultdict(list)
    products = {}
    count = 0
    for line, row in enumerate(rows[1:], 2):
        if not any(clean(v) for v in row):
            continue
        if len(row) > len(headers) and any(clean(v) for v in row[len(headers):]):
            raise DataError(f"Backend row {line} has too many cells.")
        row += [""] * max(0, len(headers) - len(row))
        cif = normalize_cif(row[idx["CIF"]])
        name = clean(row[idx["Customer Full Name"]])
        product_raw, side = clean(row[idx["Product"]]), clean(row[idx["Payment Type"]]).upper()
        if not name or not product_raw or side not in {"CR", "DR"}:
            raise DataError(f"Backend row {line} needs a company, product and CR/DR side.")
        product = products.setdefault(product_raw.casefold(), product_raw)
        key = cif, product, side
        source_rows[key].append(line)
        if name not in aliases[cif]:
            aliases[cif].append(name)
        observed = []
        for month, index in columns.items():
            value = parse_amount(row[index])
            if value is not None:
                cells[*key, month].append((value, line))
                observed.append(month)
        display_choices[cif].append((max(observed, default=""), -line, name))
        count += 1
    if not count:
        raise DataError("The backend contains no customer rows.")
    series = []
    for key, lines in sorted(source_rows.items()):
        values = {}
        for month in columns:
            populated = cells[*key, month]
            if len(populated) > 1:
                raise DataError(f"Overlapping backend records for {key[0]}, {key[1]}, {key[2]}, {month}. Resolve the source grain.")
            values[month] = populated[0][0] if populated else 0
        series.append(Series(*key, values, tuple(lines)))
    return Snapshot({k: max(v)[2] for k, v in display_choices.items()}, dict(aliases), series,
                    months, opening, hashlib.sha256(raw).hexdigest(), count)
