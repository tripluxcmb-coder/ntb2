from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

from banker.analytics import build_profile, million_text
from banker.data import DataError, load_balances, parse_amount
from banker.recommendations import candidates, fallback_recommendations, load_products
from banker.service import BankService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def snapshot():
    return load_balances(ROOT / "data/customer_balances.csv")


@pytest.fixture
def accounting():
    return json.loads((ROOT / "config/accounting_map.json").read_text())


def csv_source(rows, months=None):
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(["CIF", "Customer Full Name", "Product", "Payment Type", "year End Balance", *(months or ["Jan-26", "Feb-26"])])
    writer.writerows(rows)
    return text.getvalue().encode()


def test_updated_snapshot_shape(snapshot):
    assert len(snapshot.names) == 14 and snapshot.row_count == 74
    assert snapshot.opening == "2025-12"
    assert snapshot.months[-1] == "2026-09"
    assert len(snapshot.aliases["50223711"]) == 2


def test_all_source_cells_reconcile_including_final_null_zero(snapshot):
    # Independent CSV control for all cells and the previous December balance.
    rows = list(csv.DictReader((ROOT / "data/customer_balances.csv").open(encoding="utf-8-sig")))
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    headers = {f"{name}-26": f"2026-{i:02d}" for i, name in enumerate(month_names, 1)}
    headers["year End Balance"] = "2025-12"
    control = defaultdict(int)
    for row in rows:
        for header, month in headers.items():
            value = row[header].replace(",", "").strip()
            control[row["CIF"], row["Product"], row["Payment Type"], month] += int(Decimal(value or "0") * 100)
    for series in snapshot.series:
        for month, value in series.values.items():
            assert value == control[series.cif, series.product, series.side, month]


def test_assets_liabilities_exclude_nonfunded_and_payments(snapshot, accounting):
    p = build_profile(snapshot, "50100120", accounting)
    assert p["metrics"]["assets"]["amount_mn"] == 1.092816
    assert p["metrics"]["liabilities"]["amount_mn"] == 56.691975
    assert p["metrics"]["contingent"]["amount_mn"] == 0
    assert p["metrics"]["payments"]["amount_mn"] == 65.256803
    assert p["metrics"]["liabilities"]["ytd"]["amount_mn"] == -1003.19244
    assert p["metrics"]["liabilities"]["mom"]["amount_mn"] == -28.044819
    assert p["metrics"]["assets"]["ytd"]["amount_mn"] == .298698
    assert p["opening_month"] == "2025-12"


def test_zero_is_a_final_balance_and_produces_full_decline(snapshot, accounting):
    profile = build_profile(snapshot, "50201635", accounting)
    loan = next(r for r in profile["products"] if r["product"] == "LN")
    assert loan["amount_mn"] == 0 and loan["current_zero"] is True
    assert loan["ytd"]["amount_mn"] == -1250 and loan["ytd"]["pct"] == -100
    assert loan["mom"]["amount_mn"] == 0
    assert loan["ytd"]["display"] == "-1,250.00"
    assert "missing" not in str(profile).lower()
    assert "imputed" not in str(profile).lower()


def test_name_segments_merge_before_final_zero(snapshot, accounting):
    profile = build_profile(snapshot, "50223711", accounting)
    casa = next(r for r in profile["products"] if r["product"] == "CASA" and r["side"] == "CR")
    assert casa["opening_mn"] == 2558.889825
    assert casa["history"][1]["amount_mn"] == 4306.339129
    assert casa["amount_mn"] == 456.680636
    assert casa["ytd"]["amount_mn"] == -2102.209189


def test_january_mom_uses_december_opening(accounting):
    raw = csv_source([["00120", "Example PLC", "CASA", "CR", "100", "150"]], ["Jan-26"])
    profile = build_profile(load_balances(raw), "00120", accounting)
    assert profile["metrics"]["liabilities"]["mom"]["amount_mn"] == .00005
    assert profile["metrics"]["liabilities"]["mom"] == profile["metrics"]["liabilities"]["ytd"]
    with pytest.raises(DataError, match="No customer"):
        build_profile(load_balances(raw), "120", accounting)


def test_unknown_previous_calendar_month_is_not_an_older_month(accounting):
    raw = csv_source([["1", "Example PLC", "CASA", "CR", "100", "150", "200"]], ["Jan-26", "Mar-26"])
    profile = build_profile(load_balances(raw), "1", accounting)
    assert profile["metrics"]["liabilities"]["mom"]["amount_mn"] is None
    assert profile["metrics"]["liabilities"]["ytd"]["amount_mn"] == .0001


@pytest.mark.parametrize("value,expected", [("", None), ("null", None), ("NaN", None), ("0", 0),
                                            ("1,234.56",123456), ("(10.25)",-1025)])
def test_null_and_exact_amount_parsing(value, expected):
    assert parse_amount(value) == expected


@pytest.mark.parametrize("value", ["1,2", "abc", "Infinity", "12.345", "1e4"])
def test_structural_numeric_defects_are_rejected(value):
    with pytest.raises(DataError): parse_amount(value)


def test_duplicate_populated_values_rejected():
    raw = csv_source([["1", "Example PLC", "CASA", "CR", "100", "0", "1"],
                      ["1", "Example PLC", "CASA", "CR", "", "0", ""]])
    with pytest.raises(DataError, match="Overlapping"): load_balances(raw)


def test_small_nonzero_is_not_displayed_as_zero():
    assert million_text(413500, signed=True) == "+0.004135"
    assert million_text(1) == "0.00000001"
    assert million_text(0, signed=True) == "0.00"


def test_all_bank_product_groups_and_internal_accounts_exclusion(snapshot, accounting):
    catalog = load_products((ROOT / "data/products.csv").read_bytes())
    assert len(catalog) == 22
    assert catalog[-1]["name"] == "Treasury Bonds"
    companies = json.loads((ROOT / "data/company_master.json").read_text())
    for cif in snapshot.names:
        profile = build_profile(snapshot, cif, accounting)
        choices = candidates(profile, companies[cif], catalog)
        result = fallback_recommendations(profile, companies[cif], choices)
        assert len(result["recommendations"]) == 3
        assert len({r["theme"] for r in result["recommendations"]}) == 3
        assert not any(c["name"] in {"Internal & Control Accounts", "Interbank Accounts"} for c in choices)
        assert all(c["name"] in {r["name"] for r in catalog} for c in choices)


def test_recommendations_change_with_customer_profile_and_balances():
    service = BankService(ROOT)
    central = service.dashboard("50100120")["priorities"]["recommendations"]
    haycarb = service.dashboard("50688593")["priorities"]["recommendations"]
    assert [c["name"] for c in central] != [c["name"] for c in haycarb]
    assert central[0]["name"] == "Current Accounts"
    assert any(c["name"] == "Trade Finance" for c in haycarb)


def test_bank_source_dictionary_can_reclassify_card_credit_balances(snapshot, accounting):
    accounting["mapping"]["CARD|CR"]["category"] = "payments"
    profile = build_profile(snapshot, "50100120", accounting)
    assert profile["metrics"]["liabilities"]["amount_mn"] == 54.153992
    assert profile["metrics"]["payments"]["amount_mn"] == 67.794786
