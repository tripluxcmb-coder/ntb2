"""Colors sampled from the supplied bank logo and the unchanged logo bytes."""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

BLUE = "#2874C2"
SKY = "#3E8ECD"
MAGENTA = "#D23B82"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    logo = Path(__file__).resolve().parents[1] / "public" / "bank-logo.png"
    return "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode("ascii")
