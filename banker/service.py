"""Backend refresh, company identity, and per-snapshot AI result isolation."""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit

from .analytics import build_profile
from .data import DataError, entity_key, load_balances
from .gateway import GatewayError, OpenRouterClient
from .recommendations import candidates, fallback_recommendations, load_products

logger = logging.getLogger(__name__)


def pretty_name(name: str) -> str:
    name = name.title()
    for wrong, right in [("Plc", "PLC"), ("Lolc", "LOLC"), ("Cic ", "CIC ")]:
        name = name.replace(wrong, right)
    return name


def valid_link(link: dict) -> bool:
    if not isinstance(link, dict) or link.get("label") not in {"Official website", "Financial statements", "Annual report"}:
        return False
    try:
        parsed = urlsplit(link.get("url", ""))
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


class BankService:
    def __init__(self, root: Path, *, ai_factory=None, paths: dict | None = None):
        self.root = root
        def configured(name: str, default: str) -> Path:
            path = Path((paths or {}).get(name) or os.getenv(name, default))
            return path if path.is_absolute() else root / path
        self.paths = [configured("BALANCES_PATH", "data/customer_balances.csv"),
                      configured("PRODUCTS_PATH", "data/products.csv"),
                      configured("COMPANY_MASTER_PATH", "data/company_master.json"),
                      configured("ACCOUNTING_MAP_PATH", "config/accounting_map.json")]
        self.currency = os.getenv("SOURCE_CURRENCY", "LKR")
        self.bank_name = os.getenv("BANK_NAME", "Nations Trust Bank")
        self.ai_factory = ai_factory or OpenRouterClient.from_env
        self.ai_available = bool(os.getenv("OPENROUTER_API_KEY")) or ai_factory is not None
        self._lock = threading.RLock()
        self._fingerprint = None
        self._cache = {}
        self._ai_locks = {}

    def refresh(self):
        # Reading fresh bytes makes same-size replacements visible immediately.
        # ETL should use an atomic rename so users never read a half-written file.
        raw = [p.read_bytes() for p in self.paths]
        fingerprint = hashlib.sha256(b"\0".join(raw)).hexdigest()
        with self._lock:
            if fingerprint == self._fingerprint:
                return
            snapshot = load_balances(raw[0])
            catalog = load_products(raw[1])
            companies, accounting = json.loads(raw[2]), json.loads(raw[3])
            if not isinstance(companies, dict) or not isinstance(accounting.get("mapping"), dict):
                raise DataError("Invalid backend company master or accounting map.")
            self.snapshot, self.catalog, self.companies, self.accounting = snapshot, catalog, companies, accounting
            self._fingerprint = fingerprint
            self._cache.clear()
            # Retain lock objects: an old request can still be completing on its old version.

    def customer_company(self, cif: str) -> dict:
        company = self.companies.get(cif)
        if company is None:
            return {"legal_name": self.snapshot.names[cif], "display_name": pretty_name(self.snapshot.names[cif]),
                    "industry": "unknown", "industry_label": "Corporate banking", "description":
                    "Company background will appear here when the relationship profile is updated.", "links": [], "is_bank": False}
        if entity_key(company["legal_name"]) not in {entity_key(n) for n in self.snapshot.aliases[cif]}:
            raise DataError("Company identity does not match the backend CIF mapping.")
        return {**company, "display_name": company.get("display_name") or pretty_name(company["legal_name"]),
                "links": [l for l in company.get("links", []) if valid_link(l)]}

    def customers(self) -> dict:
        self.refresh()
        with self._lock:
            customers = [{"cif": cif, "name": self.customer_company(cif)["display_name"]} for cif in self.snapshot.names]
            return {"customers": sorted(customers, key=lambda c: c["name"]), "bank_name": self.bank_name,
                    "default_cif": "50100120" if "50100120" in self.snapshot.names else customers[0]["cif"],
                    "version": self._fingerprint}

    def dashboard(self, cif: str) -> dict:
        self.refresh()
        with self._lock:
            profile = build_profile(self.snapshot, cif, self.accounting, self.currency)
            company = self.customer_company(profile["cif"])
            options = candidates(profile, company, self.catalog)
            profile["name"] = company["display_name"]
            version = self._fingerprint
            cache_key = (version, profile["cif"], os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"))
            priorities = copy.deepcopy(self._cache.get(cache_key)) or fallback_recommendations(profile, company, options)
            return {"profile": profile, "company": company, "priorities": priorities,
                    "bank_name": self.bank_name, "version": version, "ai_available": self.ai_available,
                    "catalog_groups": len(self.catalog)}

    def recommend(self, cif: str, version: str | None = None, force: bool = False) -> dict:
        payload = self.dashboard(cif)
        current_version = payload["version"]
        if version and current_version != version:
            raise DataError("The relationship snapshot changed. Refresh the company view.")
        key = (current_version, payload["profile"]["cif"], os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"))
        with self._lock:
            lock = self._ai_locks.setdefault(key, threading.Lock())
        with lock:
            with self._lock:
                if key in self._cache and not force:
                    return copy.deepcopy(self._cache[key])
                options = candidates(payload["profile"], payload["company"], self.catalog)
            if not self.ai_available:
                return payload["priorities"]
            try:
                result = self.ai_factory().recommend(payload["profile"], payload["company"], options)
            except GatewayError:
                # No prompt, balances, API key, company name or raw provider response is logged.
                logger.warning("OpenRouter recommendations unavailable; using local priorities.")
                result = payload["priorities"]
            with self._lock:
                if self._fingerprint == current_version:
                    self._cache[key] = copy.deepcopy(result)
            return result
