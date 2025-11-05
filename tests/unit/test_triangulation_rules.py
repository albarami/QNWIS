"""Unit tests for triangulation rules."""
from src.qnwis.verification.rules import (
    check_ewi_vs_yoy_sign,
    check_percent_bounds,
    check_qatarization_formula,
    check_sum_to_one,
    check_yoy_bounds,
)


def test_sum_to_one_flags_delta():
    """Test that sum_to_one detects when male+female != total."""
    issues = check_sum_to_one(55.0, 44.0, 100.0)
    assert any(i.code == "sum_to_one" for i in issues)


def test_sum_to_one_passes_within_tolerance():
    """Test that sum_to_one passes when within tolerance."""
    issues = check_sum_to_one(49.8, 50.0, 99.9)
    assert len(issues) == 0


def test_percent_bounds():
    """Test that percent_bounds detects values outside [0,100]."""
    issues = check_percent_bounds("male_percent", 120.0)
    assert any(i.code == "percent_bounds" for i in issues)


def test_percent_bounds_passes():
    """Test that percent_bounds passes for valid values."""
    issues = check_percent_bounds("male_percent", 50.0)
    assert len(issues) == 0


def test_percent_bounds_ignores_non_percent():
    """Test that percent_bounds ignores keys not ending in _percent."""
    issues = check_percent_bounds("male_count", 120.0)
    assert len(issues) == 0


def test_yoy_bounds():
    """Test that yoy_bounds detects outliers."""
    assert check_yoy_bounds(300.0)
    assert check_yoy_bounds(-150.0)


def test_yoy_bounds_passes():
    """Test that yoy_bounds passes for reasonable values."""
    assert not check_yoy_bounds(50.0)
    assert not check_yoy_bounds(-10.0)


def test_qatarization_formula():
    """Test that qatarization_formula detects mismatches."""
    issues = check_qatarization_formula(200, 800, 30.0)  # expected 20.0%
    assert any(i.code == "qatarization_mismatch" for i in issues)


def test_qatarization_formula_passes():
    """Test that qatarization_formula passes when correct."""
    issues = check_qatarization_formula(200, 800, 20.0)
    assert len(issues) == 0


def test_qatarization_formula_with_tolerance():
    """Test that qatarization_formula allows small deltas within tolerance."""
    issues = check_qatarization_formula(200, 800, 20.3)  # within SUM_TOL=0.5
    assert len(issues) == 0


def test_ewi_vs_yoy_sign():
    """Test that ewi_vs_yoy_sign detects incoherence."""
    issues = check_ewi_vs_yoy_sign(4.0, 2.0)
    assert any(i.code == "ewi_incoherence" for i in issues)


def test_ewi_vs_yoy_sign_passes():
    """Test that ewi_vs_yoy_sign passes when consistent."""
    issues = check_ewi_vs_yoy_sign(4.0, -2.0)
    assert len(issues) == 0


def test_ewi_vs_yoy_sign_low_ewi():
    """Test that ewi_vs_yoy_sign passes when EWI drop is low."""
    issues = check_ewi_vs_yoy_sign(2.0, 5.0)
    assert len(issues) == 0


def test_none_handling():
    """Test that rules handle None values gracefully."""
    assert not check_sum_to_one(None, 50.0, 100.0)
    assert not check_yoy_bounds(None)
    assert not check_qatarization_formula(None, 800, 20.0)
    assert not check_ewi_vs_yoy_sign(None, 2.0)
