"""
Unit tests for transform base functions.

Tests each transform in isolation with deterministic inputs.
"""

import pytest

from src.qnwis.data.transforms import base


def test_select_columns():
    """Test select transform."""
    rows = [
        {"x": 1, "y": 10, "z": 100},
        {"x": 2, "y": 20, "z": 200},
        {"x": 3, "y": 30, "z": 300},
    ]
    out = base.select(rows, ["x", "z"])
    assert len(out) == 3
    assert list(out[0].keys()) == ["x", "z"]
    assert out[0] == {"x": 1, "z": 100}
    assert out[1] == {"x": 2, "z": 200}

    # Test missing columns become None
    out2 = base.select(rows, ["x", "missing"])
    assert out2[0]["missing"] is None


def test_filter_equals():
    """Test filter_equals transform."""
    rows = [
        {"sector": "Energy", "year": 2023, "value": 100},
        {"sector": "Finance", "year": 2023, "value": 200},
        {"sector": "Energy", "year": 2024, "value": 110},
        {"sector": "Finance", "year": 2024, "value": 220},
    ]
    out = base.filter_equals(rows, {"sector": "Energy"})
    assert len(out) == 2
    assert all(r["sector"] == "Energy" for r in out)

    out2 = base.filter_equals(rows, {"sector": "Energy", "year": 2024})
    assert len(out2) == 1
    assert out2[0] == {"sector": "Energy", "year": 2024, "value": 110}


def test_rename_columns():
    """Test rename_columns transform."""
    rows = [
        {"old_name": 1, "keep": 10},
        {"old_name": 2, "keep": 20},
    ]
    out = base.rename_columns(rows, {"old_name": "new_name"})
    assert len(out) == 2
    assert "new_name" in out[0]
    assert "old_name" not in out[0]
    assert out[0]["new_name"] == 1
    assert out[0]["keep"] == 10


def test_to_percent():
    """Test to_percent transform."""
    rows = [
        {"ratio": 0.15, "count": 100},
        {"ratio": 0.85, "count": 200},
    ]
    out = base.to_percent(rows, ["ratio"], scale=100.0)
    assert out[0]["ratio"] == 15.0
    assert out[1]["ratio"] == 85.0
    assert out[0]["count"] == 100  # unchanged

    # Test custom scale
    out2 = base.to_percent(rows, ["ratio"], scale=1000.0)
    assert out2[0]["ratio"] == 150.0


def test_top_n_descending():
    """Test top_n transform with descending sort."""
    rows = [
        {"x": 1, "v": 10},
        {"x": 2, "v": 30},
        {"x": 3, "v": 20},
        {"x": 4, "v": 50},
        {"x": 5, "v": 40},
    ]
    out = base.top_n(rows, "v", n=3, descending=True)
    assert len(out) == 3
    assert [r["v"] for r in out] == [50, 40, 30]
    assert [r["x"] for r in out] == [4, 5, 2]


def test_top_n_ascending():
    """Test top_n transform with ascending sort."""
    rows = [
        {"x": 1, "v": 10},
        {"x": 2, "v": 30},
        {"x": 3, "v": 20},
    ]
    out = base.top_n(rows, "v", n=2, descending=False)
    assert len(out) == 2
    assert [r["v"] for r in out] == [10, 20]


def test_top_n_descending_none_defaults_true():
    """Explicit None should default to descending order."""
    rows = [
        {"x": 1, "v": 10},
        {"x": 2, "v": 20},
    ]
    out = base.top_n(rows, "v", n=1, descending=None)
    assert out and out[0]["v"] == 20


def test_top_n_negative_returns_empty():
    """Negative n should clamp to zero."""
    rows = [
        {"x": 1, "v": 10},
        {"x": 2, "v": 20},
    ]
    out = base.top_n(rows, "v", n=-1)
    assert out == []


def test_top_n_rejects_non_int_n():
    """Non-integer n should raise TypeError."""
    rows = [
        {"x": 1, "v": 10},
        {"x": 2, "v": 20},
    ]
    with pytest.raises(TypeError):
        base.top_n(rows, "v", n="two")  # type: ignore[arg-type]


def test_share_of_total_single_group():
    """Test share_of_total with single group."""
    rows = [
        {"sector": "A", "employees": 10},
        {"sector": "B", "employees": 30},
        {"sector": "C", "employees": 60},
    ]
    out = base.share_of_total(
        rows,
        group_keys=[],  # single group (all rows)
        value_key="employees",
        out_key="share_pct",
    )
    assert len(out) == 3
    assert abs(sum(r["share_pct"] for r in out) - 100.0) < 0.01
    assert abs(out[0]["share_pct"] - 10.0) < 0.01
    assert abs(out[1]["share_pct"] - 30.0) < 0.01
    assert abs(out[2]["share_pct"] - 60.0) < 0.01


def test_share_of_total_multiple_groups():
    """Test share_of_total with multiple groups."""
    rows = [
        {"year": 2023, "sector": "A", "v": 10},
        {"year": 2023, "sector": "B", "v": 30},
        {"year": 2024, "sector": "A", "v": 20},
        {"year": 2024, "sector": "B", "v": 80},
    ]
    out = base.share_of_total(
        rows,
        group_keys=["year"],
        value_key="v",
        out_key="pct",
    )
    # Year 2023: 10+30=40, so A=25%, B=75%
    year_2023 = [r for r in out if r["year"] == 2023]
    assert abs(sum(r["pct"] for r in year_2023) - 100.0) < 0.01
    assert abs(year_2023[0]["pct"] - 25.0) < 0.01
    assert abs(year_2023[1]["pct"] - 75.0) < 0.01

    # Year 2024: 20+80=100, so A=20%, B=80%
    year_2024 = [r for r in out if r["year"] == 2024]
    assert abs(sum(r["pct"] for r in year_2024) - 100.0) < 0.01
    assert abs(year_2024[0]["pct"] - 20.0) < 0.01
    assert abs(year_2024[1]["pct"] - 80.0) < 0.01


def test_yoy_basic():
    """Test yoy transform with basic time series."""
    rows = [
        {"year": 2019, "v": 100},
        {"year": 2020, "v": 110},
        {"year": 2021, "v": 99},
        {"year": 2022, "v": 120},
    ]
    out = base.yoy(rows, key="v", sort_keys=["year"])
    assert len(out) == 4
    assert out[0]["yoy_percent"] is None  # First row
    assert out[1]["yoy_percent"] == 10.0  # (110-100)/100*100
    assert out[2]["yoy_percent"] == -10.0  # (99-110)/110*100
    assert abs(out[3]["yoy_percent"] - 21.21) < 0.01  # (120-99)/99*100


def test_yoy_missing_values():
    """Test yoy transform with missing values."""
    rows = [
        {"year": 2019, "v": 100},
        {"year": 2020, "v": None},
        {"year": 2021, "v": 110},
    ]
    out = base.yoy(rows, key="v", sort_keys=["year"])
    assert out[0]["yoy_percent"] is None
    assert out[1]["yoy_percent"] is None
    assert out[2]["yoy_percent"] is None  # Previous was None


def test_rolling_avg_basic():
    """Test rolling_avg transform with basic window."""
    rows = [
        {"year": 2019, "v": 100},
        {"year": 2020, "v": 110},
        {"year": 2021, "v": 120},
        {"year": 2022, "v": 130},
    ]
    out = base.rolling_avg(rows, key="v", sort_keys=["year"], window=3)
    assert len(out) == 4
    assert out[0]["rolling_avg"] is None  # Window not filled
    assert out[1]["rolling_avg"] is None  # Window not filled
    assert out[2]["rolling_avg"] == 110.0  # mean(100,110,120)
    assert out[3]["rolling_avg"] == 120.0  # mean(110,120,130)


def test_rolling_avg_window_2():
    """Test rolling_avg with window of 2."""
    rows = [
        {"year": 2019, "v": 100},
        {"year": 2020, "v": 110},
        {"year": 2021, "v": 99},
    ]
    out = base.rolling_avg(rows, key="v", sort_keys=["year"], window=2)
    assert out[0]["rolling_avg"] is None
    assert out[1]["rolling_avg"] == 105.0  # mean(100,110)
    assert out[2]["rolling_avg"] == 104.5  # mean(110,99)


def test_rolling_avg_custom_out_key():
    """Test rolling_avg with custom output key."""
    rows = [
        {"year": 2019, "v": 100},
        {"year": 2020, "v": 110},
        {"year": 2021, "v": 120},
    ]
    out = base.rolling_avg(
        rows,
        key="v",
        sort_keys=["year"],
        window=2,
        out_key="avg_2yr",
    )
    assert "avg_2yr" in out[1]
    assert "rolling_avg" not in out[1]


def test_composed_transforms():
    """Test composing multiple transforms."""
    rows = [
        {"year": 2023, "sector": "Energy", "employees": 100},
        {"year": 2024, "sector": "Energy", "employees": 130},
        {"year": 2023, "sector": "Finance", "employees": 200},
        {"year": 2024, "sector": "Finance", "employees": 180},
    ]

    # Filter Energy, compute YoY, then select columns
    out = base.filter_equals(rows, {"sector": "Energy"})
    out = base.yoy(out, key="employees", sort_keys=["year"])
    out = base.select(out, ["year", "employees", "yoy_percent"])

    assert len(out) == 2
    assert list(out[0].keys()) == ["year", "employees", "yoy_percent"]
    assert out[1]["yoy_percent"] == 30.0


def test_top_n_with_select():
    """Test top_n followed by select."""
    rows = [
        {"x": 1, "v": 10, "extra": "a"},
        {"x": 2, "v": 30, "extra": "b"},
        {"x": 3, "v": 20, "extra": "c"},
    ]
    out = base.top_n(rows, "v", n=2)
    out = base.select(out, ["x", "v"])

    assert len(out) == 2
    assert [r["v"] for r in out] == [30, 20]
    assert "extra" not in out[0]
