"""Bank-product candidates from the supplied catalog, informed by actual positions."""
from __future__ import annotations

import re

from .data import DataError, csv_rows, clean


def product_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def load_products(raw: bytes) -> list[dict]:
    rows = csv_rows(raw)
    if clean(rows[0][0]) != "Main Group":
        raise DataError("The backend product list needs a Main Group header.")
    names = [clean(r[0]) for r in rows[1:] if r and clean(r[0])]
    if len(names) != len(set(names)):
        raise DataError("The product list contains duplicate group names.")
    return [{"id": product_id(name), "name": name} for name in names]


def candidates(profile: dict, company: dict, catalog: list[dict]) -> list[dict]:
    rows = profile["products"]
    industry = company.get("industry", "unknown")
    finance = industry == "financial_services"
    operating = any(r["product"] == "CASA" and r["amount_mn"] > 0 for r in rows)
    td = next((r for r in rows if r["product"] == "TD"), None)
    trade = [r for r in rows if r["product"] in {"Foreign Bills", "Document Credit", "Bank Guarantee"}]
    borrowing = profile["metrics"]["assets"]["amount_mn"] > 0
    payments = profile["metrics"]["payments"]["amount_mn"] > 0
    liability_decline = (profile["metrics"]["liabilities"]["ytd"]["pct"] or 0) <= -20
    result = []
    for product in catalog:
        name = product["name"]
        if name == "Internal & Control Accounts":
            continue
        if name == "Interbank Accounts" and not company.get("is_bank", False):
            continue
        if name == "Savings & Investment Plans":
            # The supplied catalog gives no corporate eligibility for this group.
            # Keep it available in the source list; do not force a retail plan into a PLC visit.
            continue
        held = [r for r in rows if r["group"] == name and r["amount_mn"] != 0]
        historical = [r for r in rows if r["group"] == name and r["previously_nonzero"]]
        action = "Deepen relationship" if held else "Re-engage" if historical else "Explore opportunity"
        score, theme = 10, name
        why = "Align the service with the company's operating requirements."
        question = "What requirements would make this service useful for your business?"
        checks = ["Confirm the customer's purpose, existing arrangements and authorized decision-maker."]
        support = [r["id"] for r in held or historical]
        if name == "Current Accounts":
            score, theme = 65 if operating else 55, "operating_accounts"
            score += 20 if liability_decline else 0
            why = "Protect operating balances and capture a greater share of collections and supplier payments."
            question = "What has changed in your operating balances, and which collections or supplier payments could be routed through the bank?"
        elif name == "Savings Accounts":
            score, theme = 20 if operating else 10, "operating_accounts"
            why = "Explore interest-bearing operating liquidity where the company's account eligibility permits."
            checks.append("Confirm corporate account eligibility and access requirements.")
        elif name == "Fixed & Term Deposits":
            score, theme = 45 + (35 if td and (td["ytd"]["amount_mn"] or 0) < 0 else 0), "term_funding"
            why = "Review deposit retention, maturity planning and funds currently placed elsewhere."
            question = "What drove the change in deposits, and which upcoming maturities could we compete for without constraining operating liquidity?"
            checks.append("Confirm investable surplus, tenor, early-withdrawal requirements and current approved pricing.")
        elif name == "Call Deposits":
            if not operating and not td: continue
            score, theme = 60 + (10 if finance else 0), "flexible_funding"
            why = "Explore flexible short-term placement for funds that need more access than a term deposit."
            question = "Which funds need to remain accessible while awaiting disbursement, settlement or reinvestment?"
            checks.append("Confirm stable surplus, notice terms, institution limits and placement eligibility.")
        elif name == "Structured Deposits":
            if not td or td["amount_mn"] <= 0: continue
            score, theme = 22, "investment_diversification"
            why = "Discuss a treasury-led alternative only if the mandate and risk appetite support the structure."
            question = "Does your approved investment mandate allow structured payoffs and the associated liquidity and market risks?"
            checks.append("Treasury suitability review must establish payoff, capital risk, liquidity and approved mandate before any offer.")
        elif name == "Cash Margin Deposits":
            if not any(r["amount_mn"] > 0 for r in trade): continue
            score, theme = 40, "trade_collateral"
            why = "Coordinate collateral balances with live trade or guarantee requirements."
            question = "Can cash margin arrangements be aligned more efficiently with your trade and guarantee facilities?"
            checks.append("Confirm facility terms, collateral linkage and release conditions.")
        elif name == "Special Purpose Accounts":
            if finance: continue
            score, theme = 30, "special_purpose"
            why = "Explore dedicated collection or project accounts where the operating model requires separation."
            checks.append("Identify a specific legal or operating purpose and the applicable account conditions.")
        elif name == "Loans & Advances":
            score, theme = 60 if borrowing else 42, "funding"
            if historical and not held: score += 10
            why = "Match the funding structure to the operating cycle and planned disbursement or investment requirements."
            if finance:
                why = "Review institutional funding requirements against asset growth, disbursement cycles and repayment sources."
            question = "What funding requirement is not being met by the current facilities, and what is its repayment source?"
            checks.append("Assess financial statements, repayment capacity, institution exposure limits, security and credit approval.")
        elif name == "Leasing":
            if finance or industry not in {"manufacturing", "agriculture", "healthcare", "telecommunications", "diversified"}: continue
            score, theme = 45 if borrowing else 35, "funding"
            why = "Consider asset-linked finance for a confirmed equipment or vehicle investment plan."
            checks.append("Establish asset purpose, ownership terms, cash flows and credit approval.")
        elif name == "Credit Cards":
            score, theme = 25 if held else 38, "expense_controls"
            why = "Match corporate expense payments to appropriate spending controls and consolidated reporting."
            checks.append("Confirm the corporate card program, authorized users, settlement and credit requirements.")
        elif name == "Debit Cards":
            if not operating: continue
            score, theme = 20, "expense_controls"
            why = "Explore controlled access to operating account funds for approved business users."
            checks.append("Confirm corporate availability and account authority rules.")
        elif name == "Trade Finance":
            if finance or (not trade and industry not in {"agriculture", "manufacturing", "telecommunications", "diversified"}): continue
            score, theme = 70 if any(r["amount_mn"] > 0 for r in trade) else 45, "trade"
            why = "Align documentary trade and funded bills with supplier terms, collection cycles and working capital."
            question = "Where do supplier terms, trade documentation or collection timing create friction in the trade cycle?"
            checks.append("Confirm imports or exports, actual transaction documents, currencies and approved trade limits.")
            support += [r["id"] for r in trade]
        elif name == "Guarantees":
            if not trade and industry not in {"manufacturing", "diversified", "agriculture"}: continue
            score, theme = 48 if held else 38, "guarantees"
            why = "Review contract, tender and performance-security requirements alongside current guarantee usage."
            checks.append("Confirm beneficiary, contractual purpose, wording, expiry and approved non-funded limits.")
        elif name == "Remittances & Payments":
            score, theme = 65 if payments else 45, "payments"
            if historical and not held: score += 10
            why = "Capture payment flows through better settlement, reconciliation and service integration."
            question = "Which payment flows are held with other providers, and what would improve settlement and reconciliation for your team?"
            checks.append("Confirm payment corridors and currencies; remittances alone do not prove FX exposure.")
        elif name == "Treasury - Money Market & Funding":
            if not finance and not td: continue
            score, theme = 72 if finance else 45, "institutional_treasury"
            why = "Arrange a treasury discussion on short-term placements and institutional funding across the liquidity cycle."
            question = "How do you balance short-term liquidity, funding maturities and counterparty placement limits?"
            checks.append("Treasury must confirm instrument eligibility, counterparty limits, liquidity horizon and approved terms.")
        elif name == "Treasury - FX & Derivatives":
            if finance or not (trade or payments): continue
            score, theme = 62 if trade else 35, "fx"
            why = "Explore currency-risk management only where actual underlying foreign-currency exposures are established."
            question = "Which foreign-currency receipts or payments create a documented exposure, and how is it currently managed?"
            checks.append("Confirm underlying exposure, hedge policy, suitability, documentation and treasury approval. Do not propose speculative positions.")
        elif name in {"Treasury - Securities", "Treasury Bonds"}:
            if not td or td["amount_mn"] <= 0: continue
            score, theme = 40 if finance else 30, "investment_diversification"
            why = "Discuss suitable investment diversification against the company's liquidity horizon and approved mandate."
            checks.append("Establish market and interest-rate risk tolerance, liquidity needs, mandate and approved securities. Returns are not guaranteed.")
        elif name == "Interbank Accounts":
            score, theme = 65, "institutional_treasury"
            why = "Review eligible bank-to-bank settlement and funding arrangements."
        elif name == "Other Banking Services":
            if not operating and not payments: continue
            score, theme = 68, "cash_management"
            why = "Explore cash management, payroll, collections and reconciliation needs within the bank's service capabilities."
            question = "Which manual collection, payroll or reconciliation process would create the most value if improved?"
            checks.append("Confirm the specific service is offered under this group and review integration and authorization needs.")
        else:
            continue
        if not support:
            support = ["M_LIABILITIES" if operating or td else "M_ASSETS"]
        support = list(dict.fromkeys(support))
        result.append({**product, "action": action, "priority": score, "theme": theme,
                       "why_now": why, "question": question, "checks": checks,
                       "evidence_ids": support, "company_evidence_id": "C_PROFILE"})
    return sorted(result, key=lambda r: (-r["priority"], r["id"]))


def fallback_recommendations(profile: dict, company: dict, available: list[dict], limit: int = 3) -> dict:
    selected, themes = [], set()
    for candidate in available:
        if candidate["theme"] in themes:
            continue
        selected.append(dict(candidate))
        themes.add(candidate["theme"])
        if len(selected) == limit:
            break
    objective = "Understand the operating priorities, protect the existing relationship and agree a practical next step."
    if profile["metrics"]["liabilities"]["ytd"]["direction"] == "decrease":
        objective = "Understand the reduction in balances, protect the core relationship and identify funding or service opportunities."
    return {"origin": "rules", "objective": objective, "recommendations": selected,
            "company_context": company["description"]}
