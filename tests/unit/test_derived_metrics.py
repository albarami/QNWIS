"""Unit tests for derived metric computations."""

from src.qnwis.data.derived.metrics import cagr, share_of_total, yoy_growth


def test_share_of_total_basic() -> None:
    """Test basic share of total calculation."""
    rows = [{"data": {"year": 2023, "v": 60}}, {"data": {"year": 2023, "v": 40}}]
    out = share_of_total(rows, value_key="v", group_key="year")
    assert len(out) == 2
    assert round(out[0]["data"]["share_percent"], 1) == 60.0
    assert round(out[1]["data"]["share_percent"], 1) == 40.0


def test_share_of_total_multiple_years() -> None:
    """Test share of total with multiple year groups."""
    rows = [
        {"data": {"year": 2022, "v": 50}},
        {"data": {"year": 2022, "v": 50}},
        {"data": {"year": 2023, "v": 60}},
        {"data": {"year": 2023, "v": 40}},
    ]
    out = share_of_total(rows, value_key="v", group_key="year")
    assert len(out) == 4
    # 2022 group
    assert round(out[0]["data"]["share_percent"], 1) == 50.0
    assert round(out[1]["data"]["share_percent"], 1) == 50.0
    # 2023 group
    assert round(out[2]["data"]["share_percent"], 1) == 60.0
    assert round(out[3]["data"]["share_percent"], 1) == 40.0


def test_share_of_total_custom_out_key() -> None:
    """Test share of total with custom output key."""
    rows = [{"data": {"year": 2023, "v": 60}}, {"data": {"year": 2023, "v": 40}}]
    out = share_of_total(rows, value_key="v", group_key="year", out_key="custom_share")
    assert "custom_share" in out[0]["data"]
    assert round(out[0]["data"]["custom_share"], 1) == 60.0


def test_share_of_total_none_values() -> None:
    """Test share of total with None values."""
    rows = [
        {"data": {"year": 2023, "v": 60}},
        {"data": {"year": 2023, "v": None}},
    ]
    out = share_of_total(rows, value_key="v", group_key="year")
    assert out[0]["data"]["share_percent"] == 100.0
    assert out[1]["data"]["share_percent"] is None


def test_share_of_total_string_numbers() -> None:
    """Test share of total with string numeric values."""
    rows = [{"data": {"year": 2023, "v": "60"}}, {"data": {"year": 2023, "v": "40"}}]
    out = share_of_total(rows, value_key="v", group_key="year")
    assert round(out[0]["data"]["share_percent"], 1) == 60.0
    assert round(out[1]["data"]["share_percent"], 1) == 40.0


def test_yoy_growth_basic() -> None:
    """Test basic year-over-year growth calculation."""
    rows = [{"data": {"year": 2022, "v": 100}}, {"data": {"year": 2023, "v": 110}}]
    out = yoy_growth(rows, value_key="v")
    g2023 = [r for r in out if r["data"].get("year") == 2023][0]["data"]["yoy_percent"]
    assert round(g2023, 1) == 10.0


def test_yoy_growth_decline() -> None:
    """Test YoY growth with declining values."""
    rows = [{"data": {"year": 2022, "v": 100}}, {"data": {"year": 2023, "v": 90}}]
    out = yoy_growth(rows, value_key="v")
    g2023 = [r for r in out if r["data"].get("year") == 2023][0]["data"]["yoy_percent"]
    assert round(g2023, 1) == -10.0


def test_yoy_growth_first_year() -> None:
    """Test YoY growth for first year (no previous year)."""
    rows = [{"data": {"year": 2022, "v": 100}}]
    out = yoy_growth(rows, value_key="v")
    assert out[0]["data"]["yoy_percent"] is None


def test_yoy_growth_multiple_years() -> None:
    """Test YoY growth across multiple years."""
    rows = [
        {"data": {"year": 2020, "v": 100}},
        {"data": {"year": 2021, "v": 110}},
        {"data": {"year": 2022, "v": 121}},
    ]
    out = yoy_growth(rows, value_key="v")
    g2021 = [r for r in out if r["data"].get("year") == 2021][0]["data"]["yoy_percent"]
    g2022 = [r for r in out if r["data"].get("year") == 2022][0]["data"]["yoy_percent"]
    assert round(g2021, 1) == 10.0
    assert round(g2022, 1) == 10.0


def test_yoy_growth_custom_out_key() -> None:
    """Test YoY growth with custom output key."""
    rows = [{"data": {"year": 2022, "v": 100}}, {"data": {"year": 2023, "v": 110}}]
    out = yoy_growth(rows, value_key="v", out_key="custom_growth")
    assert "custom_growth" in out[1]["data"]


def test_yoy_growth_zero_previous() -> None:
    """Test YoY growth when previous year value is zero."""
    rows = [{"data": {"year": 2022, "v": 0}}, {"data": {"year": 2023, "v": 100}}]
    out = yoy_growth(rows, value_key="v")
    g2023 = [r for r in out if r["data"].get("year") == 2023][0]["data"]["yoy_percent"]
    assert g2023 is None


def test_share_of_total_non_numeric_values() -> None:
    """Share of total gracefully handles non-numeric values."""
    rows = [
        {"data": {"year": 2023, "v": "n/a"}},
        {"data": {"year": 2023, "v": None}},
        {"data": {"year": 2023, "v": "50"}},
    ]
    out = share_of_total(rows, value_key="v", group_key="year")
    assert out[0]["data"]["share_percent"] is None
    assert out[1]["data"]["share_percent"] is None
    assert out[2]["data"]["share_percent"] == 100.0


def test_yoy_growth_non_numeric_values() -> None:
    """YoY growth returns None when encountering non-numeric data."""
    rows = [
        {"data": {"year": 2022, "v": "n/a"}},
        {"data": {"year": 2023, "v": "100"}},
        {"data": {"year": 2024, "v": "invalid"}},
    ]
    out = yoy_growth(rows, value_key="v")
    # 2023 lacks numeric previous year value -> None
    data_2023 = [r for r in out if r["data"].get("year") == 2023][0]["data"]
    assert data_2023["yoy_percent"] is None
    # 2024 cannot parse its own value -> None
    data_2024 = [r for r in out if r["data"].get("year") == 2024][0]["data"]
    assert data_2024["yoy_percent"] is None


def test_cagr_basic() -> None:
    """Test basic CAGR calculation."""
    result = cagr(100, 121, 2)
    assert result is not None
    assert round(result, 1) == 10.0


def test_cagr_one_year() -> None:
    """Test CAGR for one year period."""
    result = cagr(100, 110, 1)
    assert result is not None
    assert round(result, 1) == 10.0


def test_cagr_decline() -> None:
    """Test CAGR with declining values."""
    result = cagr(121, 100, 2)
    assert result is not None
    assert result < 0


def test_cagr_zero_years() -> None:
    """Test CAGR with zero years (invalid)."""
    result = cagr(100, 121, 0)
    assert result is None


def test_cagr_negative_years() -> None:
    """Test CAGR with negative years (invalid)."""
    result = cagr(100, 121, -1)
    assert result is None


def test_cagr_zero_start_value() -> None:
    """Test CAGR with zero start value (invalid)."""
    result = cagr(0, 121, 2)
    assert result is None


def test_cagr_negative_start_value() -> None:
    """Test CAGR with negative start value (invalid)."""
    result = cagr(-100, 121, 2)
    assert result is None


def test_cagr_zero_end_value() -> None:
    """Test CAGR with zero end value (invalid)."""
    result = cagr(100, 0, 2)
    assert result is None


def test_cagr_ten_years() -> None:
    """Test CAGR over longer period."""
    # If something grows from 100 to ~259.37 in 10 years at 10% CAGR
    result = cagr(100, 259.37, 10)
    assert result is not None
    assert 9.9 < result < 10.1
