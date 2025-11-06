"""
HTML dashboard renderer for QNWIS UI.

Provides functions to generate self-contained HTML dashboards with embedded
PNG charts and KPI cards. All output is deterministic and based on synthetic data.
"""

from __future__ import annotations

from ..data.api.client import DataAPI
from .export import b64img, png_salary_yoy, png_sector_employment_bar

CSS = """
body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:16px;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.card{border:1px solid #ddd;border-radius:8px;padding:12px;background:#fff;}
.h1{font-size:20px;font-weight:700;margin:0 0 12px;}
.kpi{font-size:28px;font-weight:700;}
.small{color:#666;font-size:12px;}
img{max-width:100%;border:1px solid #eee;border-radius:4px;}
"""


def render_dashboard_html(
    api: DataAPI, year: int | None = None, sector: str = "Energy"
) -> str:
    """
    Build minimal dashboard HTML with two charts and 8 KPI cards.

    Args:
        api: DataAPI instance for querying data
        year: Target year (defaults to latest available)
        sector: Sector name for salary YoY chart

    Returns:
        Complete HTML document as string with embedded base64 PNG images

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> html = render_dashboard_html(api, sector="Energy")
        >>> "<html>" in html
        True
        >>> "QNWIS Dashboard" in html
        True
        >>> "img src=" in html
        True
    """
    y = year if year is not None else (api.latest_year("sector_employment") or 2024)

    # Build cards
    top_cards = api.top_sectors_by_employment(y, top_n=4)
    ewi_cards = api.early_warning_hotlist(y, threshold=3.0, top_n=4)

    # Charts -> PNG -> base64
    sal_png, _ = png_salary_yoy(api, sector=sector)
    emp_png, _ = png_sector_employment_bar(api, year=y)
    sal_img = b64img(sal_png)
    emp_img = b64img(emp_png)

    # Assemble HTML (no external assets)
    cards_html = "".join(
        f'<div class="card"><div class="h1">{c.get("sector", c.get("title", "Sector"))}</div>'
        f'<div class="kpi">{c.get("employees", c.get("drop_percent", ""))}</div>'
        f'<div class="small">{("employees" if c.get("employees") else "drop %")}</div></div>'
        for c in top_cards
    )

    ewi_html = "".join(
        f'<div class="card"><div class="h1">{c.get("sector", c.get("title", "Sector"))}</div>'
        f'<div class="kpi">{c.get("drop_percent", 0)}</div>'
        f'<div class="small">EWI drop (%)</div></div>'
        for c in ewi_cards
    )

    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>QNWIS Dashboard (Synthetic)</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head>
<body>
<h1>QNWIS Dashboard - Synthetic - {y}</h1>
<div class="grid">
  <div class="card"><div class="h1">Salary YoY - {sector}</div><img src="{sal_img}" alt="Salary YoY"/></div>
  <div class="card"><div class="h1">Sector Employment - {y}</div><img src="{emp_img}" alt="Sector employment"/></div>
</div>
<h2>Top sectors</h2>
<div class="grid">{cards_html}</div>
<h2>Early Warning Hotlist</h2>
<div class="grid">{ewi_html}</div>
</body></html>"""

    return html
