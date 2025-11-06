"""
Unit tests for UI card and chart builders.

Tests verify deterministic behavior using synthetic CSV data.
All tests use monkeypatched csv_catalog.BASE to isolate from production data.
"""

from __future__ import annotations

from pathlib import Path

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis
from src.qnwis.ui.cards import (
    build_employment_share_gauge,
    build_ewi_hotlist_cards,
    build_top_sectors_cards,
)
from src.qnwis.ui.charts import salary_yoy_series, sector_employment_bar


def test_cards_and_charts(tmp_path, monkeypatch):
    """
    Test all card and chart builders with synthetic data.

    Verifies:
        - Top sectors cards return correct structure and count
        - EWI hotlist cards return correct structure
        - Employment share gauge returns all required keys
        - Salary YoY series returns correct structure
        - Sector employment bar has aligned categories and values
    """
    # Generate synthetic data in temp directory
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=120)

        # Test top sectors cards
        cards = build_top_sectors_cards(api, top_n=3)
        assert len(cards) == 3, "Should return exactly 3 cards"
        assert "kpi" in cards[0], "Cards should have kpi field"
        assert "title" in cards[0], "Cards should have title field"
        assert "subtitle" in cards[0], "Cards should have subtitle field"
        assert "unit" in cards[0], "Cards should have unit field"
        assert "meta" in cards[0], "Cards should have meta field"
        assert cards[0]["unit"] == "persons", "Unit should be 'persons'"

        # Test EWI hotlist cards
        ewi = build_ewi_hotlist_cards(api, threshold=3.0, top_n=3)
        assert len(ewi) <= 3, "Should return at most 3 cards"
        if ewi:
            assert "kpi" in ewi[0], "EWI cards should have kpi field"
            assert ewi[0]["unit"] == "percent", "EWI unit should be 'percent'"
            assert "threshold" in ewi[0]["meta"], "EWI meta should have threshold"

        # Test employment share gauge
        gauge = build_employment_share_gauge(api)
        assert set(gauge.keys()) == {
            "year",
            "male",
            "female",
            "total",
        }, "Gauge should have all required keys"
        assert isinstance(gauge["year"], int), "Year should be integer"

        # Test salary YoY series
        series = salary_yoy_series(api, "Energy")
        assert "series" in series, "Should have series key"
        assert "title" in series, "Should have title key"
        assert isinstance(series["series"], list), "Series should be a list"
        assert "Energy" in series["title"], "Title should include sector name"
        if series["series"]:
            assert "x" in series["series"][0], "Series points should have x"
            assert "y" in series["series"][0], "Series points should have y"

        # Test sector employment bar
        bar = sector_employment_bar(api, year=(api.latest_year("sector_employment") or 2024))
        assert "categories" in bar, "Bar should have categories"
        assert "values" in bar, "Bar should have values"
        assert "title" in bar, "Bar should have title"
        assert len(bar["categories"]) == len(
            bar["values"]
        ), "Categories and values should be aligned"
        assert all(
            isinstance(v, int) for v in bar["values"]
        ), "Values should be integers"

    finally:
        csvcat.BASE = old


def test_top_n_clamping(tmp_path, monkeypatch):
    """
    Test that top_n parameter is correctly clamped to 1-20 range.
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=120)

        # Test clamping to minimum
        cards = build_top_sectors_cards(api, top_n=0)
        assert len(cards) >= 1, "Should clamp to at least 1"

        # Test clamping to maximum
        cards = build_top_sectors_cards(api, top_n=100)
        assert len(cards) <= 20, "Should clamp to at most 20"

        # Test normal range
        cards = build_top_sectors_cards(api, top_n=5)
        assert len(cards) == 5, "Should return exactly 5 in normal range"

    finally:
        csvcat.BASE = old


def test_year_defaulting(tmp_path, monkeypatch):
    """
    Test that year parameter defaults to latest available year.
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=120)

        # Test with no year specified
        cards = build_top_sectors_cards(api, year=None, top_n=3)
        assert len(cards) > 0, "Should return cards for default year"
        latest = api.latest_year("sector_employment") or 2024
        assert (
            cards[0]["meta"]["year"] == latest
        ), "Should use latest year as default"

        # Test with explicit year
        cards = build_top_sectors_cards(api, year=2023, top_n=3)
        if cards:  # May be empty if 2023 not in synthetic data
            assert (
                cards[0]["meta"]["year"] == 2023
            ), "Should use specified year"

    finally:
        csvcat.BASE = old
