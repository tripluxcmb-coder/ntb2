"""Exact bank-side assets, liabilities, monthly and calendar-YTD movements."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .data import DataError, Snapshot, normalize_cif

MILLION_MINOR = Decimal("100000000")
CATEGORIES = {"assets": "Bank assets", "liabilities": "Bank liabilities",
              "contingent": "Non-funded facilities", "payments": "Payment activity"}


def month_label(month: str, full: bool = False) -> str:
    return date.fromisoformat(month + "-01").strftime("%B %Y" if full else "%b %Y")


def prior_month(month: str) -> str:
    y, m = map(int, month.split("-"))
    return f"{y - (m == 1):04d}-{12 if m == 1 else m - 1:02d}"


def millions(value: int) -> float:
    return float(Decimal(value) / MILLION_MINOR)


def million_text(value: int, signed: bool = False) -> str:
    unrounded = Decimal(value) / MILLION_MINOR
    # A small real amount must not look like a confirmed zero.
    places = 8 if value != 0 and abs(unrounded) < Decimal(".01") else 2
    amount = unrounded.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    result = f"{amount:+,.{places}f}" if signed and value != 0 else f"{amount:,.{places}f}"
    return result.rstrip("0").rstrip(".") if places > 2 else result


def movement(current: int, comparison: int | None) -> dict:
    if comparison is None:
        return {"amount_mn": None, "display": "—", "pct": None, "direction": "unavailable"}
    delta = current - comparison
    pct = float((Decimal(delta) / comparison * 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)) if comparison > 0 else None
    return {"amount_mn": millions(delta), "display": million_text(delta, True), "pct": pct,
            "direction": "increase" if delta > 0 else "decrease" if delta < 0 else "unchanged"}


def build_profile(snapshot: Snapshot, cif: str, accounting: dict, currency: str = "LKR") -> dict:
    cif = normalize_cif(cif)
    if cif not in snapshot.names:
        raise DataError("No customer matches that CIF.")
    latest = snapshot.months[-1]
    previous = prior_month(latest)
    dates = [snapshot.opening] + snapshot.months
    totals = {category: {m: 0 for m in dates} for category in CATEGORIES}
    rows, facts = [], []
    observed_groups = set()
    raw_series = [s for s in snapshot.series if s.cif == cif]
    for i, series in enumerate(raw_series, 1):
        rule = accounting["mapping"].get(series.product + "|" + series.side)
        if not rule or rule.get("category") not in CATEGORIES:
            raise DataError(f"Add an accounting-map entry for {series.product} {series.side} in the backend configuration.")
        category = rule["category"]
        for month in dates:
            totals[category][month] += series.values[month]
        current, opening = series.values[latest], series.values[snapshot.opening]
        previous_value = series.values.get(previous)
        mom, ytd = movement(current, previous_value), movement(current, opening)
        if current != 0:
            observed_groups.add(rule["group"])
        row = {"id": f"P{i:02d}", "product": series.product, "side": series.side,
               "label": rule["label"], "category": category, "group": rule["group"],
               "amount_mn": millions(current), "display": million_text(current),
               "opening_mn": millions(opening), "opening_display": million_text(opening),
               "mom": mom, "ytd": ytd, "current_zero": current == 0,
               "previously_nonzero": any(v != 0 for m, v in series.values.items() if m != latest),
               "history": [{"month": m, "amount_mn": millions(series.values[m])} for m in dates]}
        rows.append(row)
        facts.append({"id": row["id"], "kind": "product", "title": row["label"], "category": category,
                      "amount_mn": row["amount_mn"], "display": row["display"], "mom": mom, "ytd": ytd,
                      "text": f"{row['label']}: {row['display']} Mn; monthly movement {mom['display']} Mn; YTD movement {ytd['display']} Mn."})
    metrics = {}
    for category, title in CATEGORIES.items():
        values = totals[category]
        metrics[category] = {"title": title, "amount_mn": millions(values[latest]),
            "display": million_text(values[latest]), "opening_mn": millions(values[snapshot.opening]),
            "opening_display": million_text(values[snapshot.opening]),
            "mom": movement(values[latest], values.get(previous)),
            "ytd": movement(values[latest], values[snapshot.opening])}
        facts.insert(len(metrics)-1, {"id": "M_" + category.upper(), "kind": "total", "title": title,
            "category": category, **metrics[category],
            "text": f"{title}: {metrics[category]['display']} Mn; monthly movement {metrics[category]['mom']['display']} Mn; YTD movement {metrics[category]['ytd']['display']} Mn."})
    position = []
    for m in dates:
        position.append({"month": m, "label": month_label(m),
                         **{c: millions(totals[c][m]) for c in CATEGORIES}})
    net_funding = totals["liabilities"][latest] - totals["assets"][latest]
    highlights = []
    for category in ["liabilities", "assets"]:
        metric = metrics[category]
        highlights.append({"title": metric["title"], "fact_id": "M_" + category.upper(),
                           "text": f"{metric['display']} Mn at {month_label(latest)}. "
                                   f"Month-on-month {metric['mom']['display']} Mn; YTD {metric['ytd']['display']} Mn."})
    meaningful = [r for r in rows if r["mom"]["amount_mn"] is not None and r["mom"]["amount_mn"] != 0]
    for row in sorted(meaningful, key=lambda r: abs(r["mom"]["amount_mn"]), reverse=True)[:2]:
        highlights.append({"title": row["label"], "fact_id": row["id"],
            "text": f"Balance is now {row['display']} Mn. Monthly movement {row['mom']['display']} Mn; YTD {row['ytd']['display']} Mn."})
    return {"cif": cif, "name": snapshot.names[cif], "aliases": snapshot.aliases[cif],
            "reporting_month": latest, "reporting_label": month_label(latest, True),
            "previous_label": month_label(previous), "opening_month": snapshot.opening,
            "opening_label": month_label(snapshot.opening), "currency": currency, "unit": f"{currency} Mn",
            "metrics": metrics, "net_funding_mn": millions(net_funding), "net_funding_display": million_text(net_funding),
            "funding_role": "Net funding relationship" if net_funding >= 0 else "Net funded relationship",
            "products": rows, "facts": facts, "highlights": highlights, "position_history": position,
            "active_products": sum(r["amount_mn"] != 0 for r in rows),
            "active_groups": sorted(observed_groups), "version": snapshot.sha256}
