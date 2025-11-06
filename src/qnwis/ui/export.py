"""
PNG and CSV export utilities for QNWIS UI.

Provides matplotlib-based PNG chart generation and CSV table exports.
All functions work on synthetic data via DataAPI with deterministic output.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io

import matplotlib

matplotlib.use("Agg")  # headless, deterministic backend
import matplotlib.pyplot as plt  # noqa: E402

from ..data.api.client import DataAPI  # noqa: E402

plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 150


def _etag_bytes(payload: bytes) -> str:
    """
    Generate ETag from payload bytes using SHA256.

    Args:
        payload: Binary content to hash

    Returns:
        SHA256 hexdigest as ETag value
    """
    return hashlib.sha256(payload).hexdigest()


def png_salary_yoy(api: DataAPI, sector: str) -> tuple[bytes, str]:
    """
    Render YoY salary series to PNG chart.

    Args:
        api: DataAPI instance for querying data
        sector: Sector name to query

    Returns:
        Tuple of (png_bytes, etag_value)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> png_data, etag = png_salary_yoy(api, "Energy")
        >>> png_data.startswith(b"\\x89PNG")
        True
    """
    pts = api.yoy_salary_by_sector(sector)
    xs = [p["year"] for p in pts if p.get("yoy_percent") is not None]
    ys = [
        p.get("y", p.get("yoy_percent")) for p in pts if p.get("yoy_percent") is not None
    ]

    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    ax.plot(xs, ys, marker="o")
    ax.set_title(f"Salary YoY - {sector}")
    ax.set_xlabel("Year")
    ax.set_ylabel("YoY %")
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)

    data = buf.getvalue()
    return data, _etag_bytes(data)


def png_sector_employment_bar(api: DataAPI, year: int) -> tuple[bytes, str]:
    """
    Bar chart: employees by sector for a given year.

    Args:
        api: DataAPI instance for querying data
        year: Target year for employment data

    Returns:
        Tuple of (png_bytes, etag_value)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> png_data, etag = png_sector_employment_bar(api, 2024)
        >>> png_data.startswith(b"\\x89PNG")
        True
    """
    rows = api.sector_employment(year)
    cats = [r.sector for r in rows]
    vals = [r.employees for r in rows]

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    ax.bar(cats, vals)
    ax.set_title(f"Sector Employment - {year}")
    ax.set_ylabel("Employees")
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.3)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)

    data = buf.getvalue()
    return data, _etag_bytes(data)


def csv_sector_employment(api: DataAPI, year: int) -> tuple[bytes, str]:
    """
    Yield CSV of sector employment for a given year.

    Args:
        api: DataAPI instance for querying data
        year: Target year for employment data

    Returns:
        Tuple of (csv_bytes, etag_value)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> csv_data, etag = csv_sector_employment(api, 2024)
        >>> b"year,sector,employees" in csv_data
        True
    """
    rows = api.sector_employment(year)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["year", "sector", "employees"])
    for r in rows:
        w.writerow([r.year, r.sector, r.employees])

    data = buf.getvalue().encode("utf-8")
    return data, _etag_bytes(data)


def csv_top_sectors(api: DataAPI, year: int, top_n: int = 5) -> tuple[bytes, str]:
    """
    CSV of top-N sectors by employment.

    Args:
        api: DataAPI instance for querying data
        year: Target year for employment data
        top_n: Number of top sectors to return

    Returns:
        Tuple of (csv_bytes, etag_value)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> csv_data, etag = csv_top_sectors(api, 2024, top_n=5)
        >>> b"year,sector,employees" in csv_data
        True
    """
    rows = api.top_sectors_by_employment(year, top_n)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["year", "sector", "employees"])
    for r in rows:
        w.writerow([year, r["sector"], r["employees"]])

    data = buf.getvalue().encode("utf-8")
    return data, _etag_bytes(data)


def b64img(png_bytes: bytes) -> str:
    """
    Return data URI for inline IMG tag.

    Args:
        png_bytes: PNG image data

    Returns:
        Data URI string for use in HTML img src attribute

    Example:
        >>> uri = b64img(b"test")
        >>> uri.startswith("data:image/png;base64,")
        True
    """
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
