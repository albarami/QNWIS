"""
Regression tests for gender sum validator fixes.

Ensures that the sum-to-one check correctly validates male + female = total,
not male + female + total = 200.
"""

import pytest
from src.qnwis.verification.rules import check_sum_to_one


def test_gender_sum_validator_ok():
    """Valid case: male + female = total within tolerance."""
    issues = check_sum_to_one(69.38, 30.62, 100.00)
    assert len(issues) == 0


def test_gender_sum_validator_ok_with_small_rounding():
    """Small rounding errors within tolerance are acceptable."""
    issues = check_sum_to_one(69.4, 30.5, 100.0)
    assert len(issues) == 0  # 99.9 vs 100.0, delta=0.1 < 0.5


def test_gender_sum_validator_flags_large_gap():
    """Large gaps should be flagged."""
    issues = check_sum_to_one(69.0, 30.0, 100.0)
    assert len(issues) == 1
    assert issues[0].code == "sum_to_one"
    assert "delta" in issues[0].detail


def test_gender_sum_validator_handles_none():
    """None values are skipped (no validation)."""
    assert len(check_sum_to_one(None, 30.0, 100.0)) == 0
    assert len(check_sum_to_one(70.0, None, 100.0)) == 0
    assert len(check_sum_to_one(70.0, 30.0, None)) == 0


def test_gender_sum_validator_exact_match():
    """Exact matches pass."""
    issues = check_sum_to_one(50.0, 50.0, 100.0)
    assert len(issues) == 0


def test_gender_sum_validator_at_tolerance_boundary():
    """Values exactly at tolerance boundary should pass."""
    # 69.75 + 30.25 = 100.0, delta = 0.0
    issues = check_sum_to_one(69.75, 30.25, 100.0)
    assert len(issues) == 0
    
    # 69.3 + 30.2 = 99.5, delta = 0.5 (at boundary)
    issues = check_sum_to_one(69.3, 30.2, 100.0)
    assert len(issues) == 0  # Should pass at boundary


def test_gender_sum_validator_just_over_tolerance():
    """Values just over tolerance should fail."""
    # 69.0 + 30.0 = 99.0, delta = 1.0 > 0.5
    issues = check_sum_to_one(69.0, 30.0, 100.0)
    assert len(issues) == 1
