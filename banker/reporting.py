"""Exact local SVG charts for a self-contained printable visit brief."""
from __future__ import annotations

import html

from .branding import BLUE, MAGENTA


def position_svg(profile: dict) -> str:
    history = profile["position_history"]
    width, height, left, right, top, bottom = 1050, 365, 100, 75, 60, 80
    values = [row[key] for row in history for key in ["assets", "liabilities"]]
    minimum, maximum = min(0, min(values)), max(0, max(values))
    span = max(1, maximum-minimum)
    lower, upper = minimum-span*.17, maximum+span*.2
    def x(i): return left + i * (width-left-right) / max(1, len(history)-1)
    def y(v): return top + (upper-v) * (height-top-bottom) / (upper-lower)
    def amount(value):
        places = 8 if value != 0 and abs(value) < .01 else 2
        text = f"{value:,.{places}f}"
        return text.rstrip("0").rstrip(".") if places > 2 else text
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Bank assets and liabilities in millions">']
    for fraction in [0, .5, 1]:
        value = minimum + (maximum-minimum)*fraction
        yy = y(value)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e0e9f3"/><text x="{left-12}" y="{yy+4:.1f}" text-anchor="end" fill="#3c526b" font-size="13">{value:,.2f}</text>')
    for i, row in enumerate(history):
        out.append(f'<text x="{x(i):.1f}" y="{height-19}" text-anchor="middle" fill="#3c526b" font-size="12">{html.escape(row["label"])}</text>')
    for category, color in [("assets", BLUE), ("liabilities", MAGENTA)]:
        path = " ".join(f"{x(i):.1f},{y(row[category]):.1f}" for i, row in enumerate(history))
        out.append(f'<polyline points="{path}" stroke="{color}" stroke-width="3" fill="none"/>')
        for i, row in enumerate(history):
            value = row[category]
            higher = value >= row["liabilities"] if category == "assets" else value > row["assets"]
            offset = -15 if higher else 23
            # Alternate rows to keep long million-unit labels apart in printed charts.
            if i % 2:
                offset += -23 if higher else 23
            text_color = "#175897" if category == "assets" else "#A52A64"
            out.append(f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="4" fill="{color}"><title>{html.escape(row["label"])}: {amount(value)} Mn</title></circle>')
            out.append(f'<text x="{x(i):.1f}" y="{y(value)+offset:.1f}" text-anchor="middle" fill="{text_color}" font-size="14" font-weight="600" style="paint-order:stroke;stroke:white;stroke-width:3px;stroke-linejoin:round">{amount(value)} Mn</text>')
    out.append(f'<text x="100" y="20" font-size="14" fill="{BLUE}">Bank assets</text><text x="225" y="20" font-size="14" fill="{MAGENTA}">Bank liabilities</text><text x="{width-right}" y="20" text-anchor="end" font-size="13" fill="#3c526b">{html.escape(profile["unit"])}</text></svg>')
    return "".join(out)
