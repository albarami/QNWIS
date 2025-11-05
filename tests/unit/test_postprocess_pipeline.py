"""
Unit tests for postprocess pipeline executor.

Tests YAML-driven pipeline application.
"""

import pytest

from src.qnwis.data.deterministic.models import Row, TransformStep
from src.qnwis.data.deterministic.postprocess import apply_postprocess


def test_empty_pipeline():
    """Test that empty pipeline returns rows unchanged."""
    rows = [
        Row(data={"x": 1, "y": 10}),
        Row(data={"x": 2, "y": 20}),
    ]
    steps = []
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 2
    assert out[0].data == {"x": 1, "y": 10}
    assert out[1].data == {"x": 2, "y": 20}
    assert trace == []


def test_single_transform():
    """Test pipeline with single transform."""
    rows = [
        Row(data={"x": 1, "v": 10}),
        Row(data={"x": 2, "v": 30}),
        Row(data={"x": 3, "v": 20}),
    ]
    steps = [
        TransformStep(name="top_n", params={"sort_key": "v", "n": 2, "descending": True}),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 2
    assert [r.data["v"] for r in out] == [30, 20]
    assert trace == ["top_n"]


def test_pipeline_compose():
    """Test pipeline with multiple transforms in sequence."""
    rows = [
        Row(data={"year": 2023, "sector": "Energy", "employees": 100}),
        Row(data={"year": 2024, "sector": "Energy", "employees": 130}),
        Row(data={"year": 2023, "sector": "Finance", "employees": 200}),
        Row(data={"year": 2024, "sector": "Finance", "employees": 220}),
    ]
    steps = [
        TransformStep(
            name="filter_equals",
            params={"where": {"sector": "Energy"}},
        ),
        TransformStep(
            name="yoy",
            params={"key": "employees", "sort_keys": ["year"], "out_key": "yoy_percent"},
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 2
    assert out[0].data["sector"] == "Energy"
    assert out[1].data["sector"] == "Energy"
    assert out[0].data["yoy_percent"] is None
    assert out[1].data["yoy_percent"] == 30.0
    assert trace == ["filter_equals", "yoy"]


def test_share_of_total_pipeline():
    """Test share_of_total in pipeline."""
    rows = [
        Row(data={"sector": "A", "employees": 10}),
        Row(data={"sector": "B", "employees": 30}),
        Row(data={"sector": "C", "employees": 60}),
    ]
    steps = [
        TransformStep(
            name="share_of_total",
            params={
                "group_keys": [],
                "value_key": "employees",
                "out_key": "share_percent",
            },
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 3
    total = sum(r.data["share_percent"] for r in out)
    assert abs(total - 100.0) < 0.01
    assert trace == ["share_of_total"]


def test_rename_and_select_pipeline():
    """Test rename followed by select."""
    rows = [
        Row(data={"old_name": 1, "keep": 10, "drop": 100}),
        Row(data={"old_name": 2, "keep": 20, "drop": 200}),
    ]
    steps = [
        TransformStep(
            name="rename_columns",
            params={"mapping": {"old_name": "new_name"}},
        ),
        TransformStep(
            name="select",
            params={"columns": ["new_name", "keep"]},
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 2
    assert "new_name" in out[0].data
    assert "keep" in out[0].data
    assert "drop" not in out[0].data
    assert "old_name" not in out[0].data
    assert trace == ["rename_columns", "select"]


def test_rolling_avg_pipeline():
    """Test rolling_avg in pipeline."""
    rows = [
        Row(data={"year": 2019, "v": 100}),
        Row(data={"year": 2020, "v": 110}),
        Row(data={"year": 2021, "v": 120}),
        Row(data={"year": 2022, "v": 130}),
    ]
    steps = [
        TransformStep(
            name="rolling_avg",
            params={"key": "v", "sort_keys": ["year"], "window": 3},
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 4
    assert out[2].data["rolling_avg"] == 110.0
    assert out[3].data["rolling_avg"] == 120.0
    assert trace == ["rolling_avg"]


def test_complex_pipeline():
    """Test complex multi-step pipeline."""
    rows = [
        Row(data={"year": 2023, "sector": "Energy", "employees": 100}),
        Row(data={"year": 2024, "sector": "Energy", "employees": 130}),
        Row(data={"year": 2023, "sector": "Finance", "employees": 200}),
        Row(data={"year": 2024, "sector": "Finance", "employees": 180}),
        Row(data={"year": 2023, "sector": "ICT", "employees": 50}),
        Row(data={"year": 2024, "sector": "ICT", "employees": 55}),
    ]
    steps = [
        # Filter to 2024 only
        TransformStep(name="filter_equals", params={"where": {"year": 2024}}),
        # Get top 2 by employees
        TransformStep(name="top_n", params={"sort_key": "employees", "n": 2}),
        # Select specific columns
        TransformStep(name="select", params={"columns": ["sector", "employees"]}),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 2
    assert set(out[0].data.keys()) == {"sector", "employees"}
    assert [r.data["employees"] for r in out] == [180, 130]
    assert trace == ["filter_equals", "top_n", "select"]


def test_to_percent_pipeline():
    """Test to_percent in pipeline."""
    rows = [
        Row(data={"ratio": 0.15, "count": 100}),
        Row(data={"ratio": 0.85, "count": 200}),
    ]
    steps = [
        TransformStep(
            name="to_percent",
            params={"columns": ["ratio"], "scale": 100.0},
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 2
    assert out[0].data["ratio"] == 15.0
    assert out[1].data["ratio"] == 85.0
    assert out[0].data["count"] == 100  # unchanged
    assert trace == ["to_percent"]


def test_unknown_transform_raises():
    """Test that unknown transform name raises ValueError."""
    rows = [Row(data={"x": 1})]
    steps = [TransformStep(name="unknown_transform", params={})]
    with pytest.raises(ValueError, match="Unknown transform step 'unknown_transform'"):
        apply_postprocess(rows, steps)


def test_pipeline_with_missing_params():
    """Test pipeline handles missing optional params."""
    rows = [
        Row(data={"x": 1, "v": 10}),
        Row(data={"x": 2, "v": 30}),
    ]
    # top_n with only required params
    steps = [
        TransformStep(name="top_n", params={"sort_key": "v", "n": 1}),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 1
    assert out[0].data["v"] == 30  # Default descending=True
    assert trace == ["top_n"]


def test_top_n_negative_clamped():
    """top_n clamps negative n to zero rows."""
    rows = [
        Row(data={"x": 1, "v": 10}),
        Row(data={"x": 2, "v": 20}),
    ]
    steps = [
        TransformStep(name="top_n", params={"sort_key": "v", "n": -5}),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert out == []
    assert trace == ["top_n"]


def test_yoy_in_pipeline():
    """Test YoY calculation in pipeline context."""
    rows = [
        Row(data={"year": 2022, "sector": "ICT", "salary": 10000}),
        Row(data={"year": 2023, "sector": "ICT", "salary": 11000}),
        Row(data={"year": 2024, "sector": "ICT", "salary": 12100}),
    ]
    steps = [
        TransformStep(
            name="yoy",
            params={"key": "salary", "sort_keys": ["year"]},
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    assert len(out) == 3
    assert out[0].data["yoy_percent"] is None
    assert out[1].data["yoy_percent"] == 10.0
    assert out[2].data["yoy_percent"] == 10.0
    assert trace == ["yoy"]


def test_share_of_total_with_groups():
    """Test share_of_total with multiple groups in pipeline."""
    rows = [
        Row(data={"year": 2023, "sector": "A", "v": 10}),
        Row(data={"year": 2023, "sector": "B", "v": 30}),
        Row(data={"year": 2024, "sector": "A", "v": 20}),
        Row(data={"year": 2024, "sector": "B", "v": 80}),
    ]
    steps = [
        TransformStep(
            name="share_of_total",
            params={
                "group_keys": ["year"],
                "value_key": "v",
                "out_key": "pct",
            },
        ),
    ]
    out, trace = apply_postprocess(rows, steps)
    year_2023 = [r for r in out if r.data["year"] == 2023]
    total_2023 = sum(r.data["pct"] for r in year_2023)
    assert abs(total_2023 - 100.0) < 0.01
    assert trace == ["share_of_total"]
