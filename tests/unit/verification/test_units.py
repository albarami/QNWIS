"""
Unit tests for verification units module.

Tests percent normalization (0.11 vs 11) and sum-to-one tolerance.
"""

import pytest
from src.qnwis.verification.units import (
    normalize_percent_value,
    is_percent_indicator,
    validate_percent_range,
    format_percent,
)
from src.qnwis.orchestration.verification import (
    _check_percent_bounds,
    _check_sum_to_one,
    _check_yoy,
    VerificationIssue,
)


def test_normalize_decimal_to_percent():
    """Test normalizing decimal (0-1) to percent (0-100)."""
    # 0.11 should become 11.0
    result = normalize_percent_value(0.11)
    assert result == pytest.approx(11.0)

    # 0.5 should become 50.0
    result = normalize_percent_value(0.5)
    assert result == pytest.approx(50.0)


def test_normalize_keeps_percent_scale():
    """Test values already in percent scale are unchanged."""
    # 11.0 should stay 11.0 (not become 1100)
    result = normalize_percent_value(11.0)
    assert result == pytest.approx(11.0)

    # 50.0 should stay 50.0
    result = normalize_percent_value(50.0)
    assert result == pytest.approx(50.0)


def test_normalize_world_bank_indicators():
    """Test World Bank indicators are not double-scaled."""
    # World Bank unemployment is already in percent
    result = normalize_percent_value(11.5, indicator_id="SL.UEM.TOTL.ZS")
    assert result == pytest.approx(11.5)  # No *100

    # Female unemployment
    result = normalize_percent_value(9.8, indicator_id="SL.UEM.TOTL.FE.ZS")
    assert result == pytest.approx(9.8)


def test_normalize_with_explicit_unit_metadata():
    """Test normalization respects explicit unit metadata."""
    # Explicit percent unit
    result = normalize_percent_value(
        15.0,
        metadata={"unit": "percent"}
    )
    assert result == pytest.approx(15.0)

    # Explicit decimal unit
    result = normalize_percent_value(
        0.15,
        metadata={"unit": "decimal"}
    )
    assert result == pytest.approx(15.0)


def test_is_percent_indicator_recognizes_world_bank():
    """Test recognition of World Bank percent indicators."""
    assert is_percent_indicator("SL.UEM.TOTL.ZS")
    assert is_percent_indicator("SL.TLF.CACT.FE.ZS")
    assert is_percent_indicator("NY.GDP.MKTP.KD.ZG")

    assert not is_percent_indicator("SP.POP.TOTL")  # Absolute count
    assert not is_percent_indicator("SL.EMP.TOTL")  # Count


def test_validate_percent_range_accepts_valid():
    """Test percent range validation accepts valid values."""
    assert validate_percent_range(0.0)
    assert validate_percent_range(50.0)
    assert validate_percent_range(100.0)


def test_validate_percent_range_rejects_invalid():
    """Test percent range validation rejects invalid values."""
    assert not validate_percent_range(-5.0)
    assert not validate_percent_range(105.0)


def test_validate_percent_range_allows_over_100_for_growth():
    """Test percent range validation can allow >100 for growth rates."""
    # Default: reject >100
    assert not validate_percent_range(150.0)

    # With flag: accept >100
    assert validate_percent_range(150.0, allow_over_100=True)
    assert not validate_percent_range(-5.0, allow_over_100=True)  # Still reject negative


def test_format_percent():
    """Test percent formatting."""
    assert format_percent(11.5) == "11.50%"
    assert format_percent(50.0) == "50.00%"
    assert format_percent(11.5, decimals=1) == "11.5%"


def test_check_percent_bounds_accepts_valid():
    """Test bounds checking accepts valid percent values."""
    metrics = {
        "unemployment_percent": 11.5,
        "female_percent": 48.2,
        "male_percent": 51.8,
    }

    issues = _check_percent_bounds(metrics)

    assert len(issues) == 0


def test_check_percent_bounds_rejects_out_of_range():
    """Test bounds checking rejects out-of-range percentages."""
    metrics = {
        "unemployment_percent": 105.0,  # Over 100
        "female_percent": -5.0,  # Negative
    }

    issues = _check_percent_bounds(metrics)

    assert len(issues) == 2
    assert any("unemployment_percent" in issue.detail for issue in issues)
    assert any("female_percent" in issue.detail for issue in issues)


def test_check_percent_bounds_skips_yoy():
    """Test bounds checking skips yoy_percent (has wider bounds)."""
    metrics = {
        "yoy_percent": 150.0,  # Would be invalid for regular percent
        "unemployment_percent": 11.5,  # Valid
    }

    issues = _check_percent_bounds(metrics)

    # Should not flag yoy_percent
    assert len(issues) == 0


def test_check_yoy_accepts_reasonable_growth():
    """Test YoY check accepts reasonable growth rates."""
    metrics = {"yoy_percent": 5.2}
    issues = _check_yoy(metrics)
    assert len(issues) == 0

    metrics = {"yoy_percent": -10.0}  # Decline
    issues = _check_yoy(metrics)
    assert len(issues) == 0


def test_check_yoy_rejects_extreme_outliers():
    """Test YoY check rejects extreme outliers."""
    metrics = {"yoy_percent": 250.0}  # Over 200% growth
    issues = _check_yoy(metrics)
    assert len(issues) == 1
    assert "yoy_outlier" in issues[0].code

    metrics = {"yoy_percent": -150.0}  # Over -100% decline
    issues = _check_yoy(metrics)
    assert len(issues) == 1


def test_check_sum_to_one_accepts_valid_split():
    """Test sum-to-one check accepts valid gender splits."""
    metrics = {
        "male_percent": 51.8,
        "female_percent": 48.2,
        "total_percent": 100.0,
    }

    issues = _check_sum_to_one(metrics)

    assert len(issues) == 0


def test_check_sum_to_one_uses_tolerance():
    """Test sum-to-one check uses tolerance for rounding."""
    # Slight rounding error should be tolerated
    metrics = {
        "male_percent": 51.7,
        "female_percent": 48.2,  # Sum = 99.9 (within 0.5 tolerance)
        "total_percent": 100.0,
    }

    issues = _check_sum_to_one(metrics)

    assert len(issues) == 0


def test_check_sum_to_one_rejects_invalid_sum():
    """Test sum-to-one check rejects invalid sums."""
    metrics = {
        "male_percent": 60.0,
        "female_percent": 30.0,  # Sum = 90.0 (not close to 100)
        "total_percent": 100.0,
    }

    issues = _check_sum_to_one(metrics)

    assert len(issues) > 0
    assert "sum_to_one" in issues[0].code


def test_check_sum_to_one_handles_missing_fields():
    """Test sum-to-one check handles missing gender fields gracefully."""
    # Missing male_percent
    metrics = {
        "female_percent": 48.2,
        "total_percent": 100.0,
    }

    issues = _check_sum_to_one(metrics)

    # Should not raise error, just no check
    assert len(issues) == 0


def test_no_double_scaling_bug():
    """Test that 11% from World Bank doesn't become 1100%."""
    # This is the critical bug fix: World Bank returns 11.0 for 11%
    # We must NOT multiply by 100 again

    value = 11.0
    indicator = "SL.UEM.TOTL.ZS"  # World Bank unemployment

    # Should stay 11.0
    normalized = normalize_percent_value(value, indicator_id=indicator)
    assert normalized == pytest.approx(11.0)

    # Validation should pass
    assert validate_percent_range(normalized)


def test_decimal_conversion_works():
    """Test that 0.11 decimal properly becomes 11%."""
    # Non-World-Bank source might return 0.11 as decimal

    value = 0.11
    indicator = None  # Not a known indicator

    # Should become 11.0
    normalized = normalize_percent_value(value, indicator_id=indicator)
    assert normalized == pytest.approx(11.0)

    # Validation should pass
    assert validate_percent_range(normalized)
