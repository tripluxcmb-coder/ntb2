"""Validate and atomically replace backend snapshots without any web upload UI."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from app import ROOT
from banker.data import load_balances
from banker.recommendations import load_products


def atomic_replace(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix="snapshot_", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Update a local backend data snapshot.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--balances", type=Path)
    group.add_argument("--products", type=Path)
    args = parser.parse_args()
    if args.balances:
        raw = args.balances.read_bytes()
        load_balances(raw)
        destination = Path(os.getenv("BALANCES_PATH", "data/customer_balances.csv"))
    else:
        raw = args.products.read_bytes()
        load_products(raw)
        destination = Path(os.getenv("PRODUCTS_PATH", "data/products.csv"))
    atomic_replace(destination if destination.is_absolute() else ROOT / destination, raw)
    print("Backend snapshot updated. The dashboard will refresh automatically.")


if __name__ == "__main__":
    main()
