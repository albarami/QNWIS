"""
Unit tests for SVG renderer module.

Tests the deterministic SVG chart generation functions.
"""

from __future__ import annotations

from src.qnwis.ui.svg import bar_chart_svg, line_chart_svg


def test_bar_chart_svg_basic() -> None:
    """Test basic bar chart SVG generation."""
    svg = bar_chart_svg("Test Chart", ["A", "B"], [10.0, 20.0])
    assert svg.startswith("<svg")
    assert "rect" in svg
    assert "Test Chart" in svg
    assert "</svg>" in svg


def test_bar_chart_svg_empty() -> None:
    """Test bar chart SVG with empty data."""
    svg = bar_chart_svg("Empty", [], [])
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Empty" in svg


def test_bar_chart_svg_escaping() -> None:
    """Test that special characters are escaped in SVG."""
    svg = bar_chart_svg("Test & <Title>", ["A & B"], [10.0])
    assert "&amp;" in svg
    assert "&lt;" in svg
    assert "&gt;" in svg
    assert "<Title>" not in svg  # Should be escaped


def test_line_chart_svg_basic() -> None:
    """Test basic line chart SVG generation."""
    svg = line_chart_svg(
        "Line Test", [{"x": 2019, "y": 1.0}, {"x": 2020, "y": 2.0}]
    )
    assert svg.startswith("<svg")
    assert "path" in svg
    assert "Line Test" in svg
    assert "</svg>" in svg


def test_line_chart_svg_empty() -> None:
    """Test line chart SVG with empty data."""
    svg = line_chart_svg("Empty Line", [])
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Empty Line" in svg


def test_line_chart_svg_single_point() -> None:
    """Test line chart SVG with single data point."""
    svg = line_chart_svg("Single", [{"x": 2020, "y": 5.0}])
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_line_chart_svg_none_values() -> None:
    """Test line chart SVG handles None values correctly."""
    svg = line_chart_svg(
        "With Nones",
        [{"x": 2019, "y": 1.0}, {"x": 2020, "y": None}, {"x": 2021, "y": 3.0}],
    )
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_svg_deterministic() -> None:
    """Test that SVG generation is deterministic."""
    categories = ["Cat1", "Cat2", "Cat3"]
    values = [100.0, 200.0, 150.0]
    svg1 = bar_chart_svg("Test", categories, values)
    svg2 = bar_chart_svg("Test", categories, values)
    assert svg1 == svg2


def test_line_chart_svg_deterministic() -> None:
    """Test that line chart SVG generation is deterministic."""
    points = [{"x": 2019, "y": 1.5}, {"x": 2020, "y": 2.5}, {"x": 2021, "y": 1.8}]
    svg1 = line_chart_svg("Test", points)
    svg2 = line_chart_svg("Test", points)
    assert svg1 == svg2
