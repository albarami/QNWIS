"""
Unit tests for gender sum validation logic.

Ensures that (male + female) == total is checked correctly,
not male + female + total == 200.
"""


def check_gender_sum(male_pct: float, female_pct: float, total_pct: float, tol: float = 0.5) -> dict:
    """
    Check that male + female approximately equals total.
    
    Args:
        male_pct: Male percentage
        female_pct: Female percentage
        total_pct: Total percentage (should be ~100 or sum of male+female)
        tol: Tolerance in percentage points
        
    Returns:
        Dictionary with sum_to_one_violation delta and ok flag
    """
    delta = abs((male_pct + female_pct) - total_pct)
    return {
        "sum_to_one_violation": round(delta, 3),
        "ok": delta <= tol
    }


def test_gender_sum_valid_case():
    """Valid case: male + female = total within tolerance."""
    result = check_gender_sum(69.38, 30.62, 100.0)
    assert result["ok"] is True
    assert result["sum_to_one_violation"] == 0.0


def test_gender_sum_with_small_rounding():
    """Small rounding errors should pass."""
    result = check_gender_sum(69.4, 30.5, 100.0)
    assert result["ok"] is True
    assert result["sum_to_one_violation"] <= 0.5


def test_gender_sum_flags_large_gap():
    """Large gaps should be flagged."""
    result = check_gender_sum(69.0, 30.0, 100.0)
    assert result["ok"] is False
    assert result["sum_to_one_violation"] == 1.0


def test_gender_sum_exact_match():
    """Exact matches should pass."""
    result = check_gender_sum(50.0, 50.0, 100.0)
    assert result["ok"] is True
    assert result["sum_to_one_violation"] == 0.0


def test_gender_sum_not_adding_all_three():
    """
    Critical test: Should NOT sum male + female + total.
    
    If we incorrectly summed all three:
    69.38 + 30.62 + 100.0 = 200.0 (WRONG)
    
    Correct logic:
    (69.38 + 30.62) - 100.0 = 0.0 (RIGHT)
    """
    result = check_gender_sum(69.38, 30.62, 100.0)
    
    # Should NOT report 200.0 violation
    assert result["sum_to_one_violation"] != 200.0
    
    # Should report ~0.0 (valid)
    assert result["sum_to_one_violation"] == 0.0
    assert result["ok"] is True


def test_gender_sum_at_tolerance_boundary():
    """Values at tolerance boundary should pass."""
    # 69.3 + 30.2 = 99.5, delta = 0.5 (at boundary)
    result = check_gender_sum(69.3, 30.2, 100.0, tol=0.5)
    assert result["ok"] is True


def test_gender_sum_just_over_tolerance():
    """Values just over tolerance should fail."""
    # 69.0 + 30.0 = 99.0, delta = 1.0 > 0.5
    result = check_gender_sum(69.0, 30.0, 100.0, tol=0.5)
    assert result["ok"] is False
    assert result["sum_to_one_violation"] == 1.0


def test_gender_sum_custom_tolerance():
    """Should respect custom tolerance values."""
    # With looser tolerance, should pass
    result = check_gender_sum(69.0, 30.0, 100.0, tol=1.5)
    assert result["ok"] is True
    
    # With tighter tolerance, should fail
    result = check_gender_sum(69.4, 30.5, 100.0, tol=0.05)
    assert result["ok"] is False
