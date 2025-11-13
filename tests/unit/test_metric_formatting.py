"""
Unit tests for metric value formatting.

Ensures that percent values from World Bank (already in percent units)
are displayed correctly without double-multiplication.
"""

from src.qnwis.ui.components import format_metric_value


def test_format_percent_world_bank_unemployment():
    """
    World Bank unemployment values are already in percent units.
    
    Example: SL.UEM.TOTL.ZS returns 0.11 meaning 0.11%, NOT 11%.
    Should display as "0.11%" not "11.00%".
    """
    # Qatar unemployment from World Bank: 0.11 (meaning 0.11%)
    result = format_metric_value("qatar_unemployment_percent", 0.11)
    assert result == "0.11%"
    
    # Should NOT be "11.00%" (that would be double-multiplication)
    assert result != "11.00%"


def test_format_percent_various_values():
    """Test formatting of various percent values."""
    # Small percentages
    assert format_metric_value("unemployment_percent", 0.11) == "0.11%"
    assert format_metric_value("unemployment_percent", 0.50) == "0.50%"
    assert format_metric_value("unemployment_percent", 1.25) == "1.25%"
    
    # Larger percentages
    assert format_metric_value("employment_percent", 69.38) == "69.38%"
    assert format_metric_value("female_percent", 30.62) == "30.62%"
    assert format_metric_value("total_percent", 100.00) == "100.00%"


def test_format_percent_key_variations():
    """Percent formatting should work for various key names."""
    # Keys with "percent"
    assert format_metric_value("male_percent", 69.38) == "69.38%"
    assert format_metric_value("unemployment_percent", 0.11) == "0.11%"
    
    # Keys with "rate"
    assert format_metric_value("unemployment_rate", 0.11) == "0.11%"
    assert format_metric_value("attrition_rate", 3.5) == "3.50%"


def test_format_non_percent_values():
    """Non-percent values should format differently."""
    # Scores/confidence (no % symbol)
    assert format_metric_value("confidence_score", 0.85) == "0.85"
    assert format_metric_value("quality_score", 92.5) == "92.50"
    
    # General floats
    assert format_metric_value("value", 123.45) == "123.45"
    assert format_metric_value("metric", 0.5) == "0.50"
    
    # Integers
    assert format_metric_value("count", 42) == "42"
    assert format_metric_value("total", 1500) == "1,500"


def test_format_edge_cases():
    """Test edge cases in formatting."""
    # Zero
    assert format_metric_value("unemployment_percent", 0.0) == "0.00%"
    
    # Very small values
    assert format_metric_value("rate", 0.01) == "0.01%"
    
    # Negative values (shouldn't happen, but handle gracefully)
    assert format_metric_value("change_percent", -2.5) == "-2.50%"


def test_no_double_multiplication():
    """
    Critical test: Ensure we never double-multiply percent values.
    
    The old logic had:
        if abs(value) < 1:
            return f"{value:.2%}"  # This multiplies by 100!
    
    This caused 0.11 to display as "11.00%" (wrong).
    New logic just adds % symbol without multiplication.
    """
    # These should all just add % symbol, not multiply
    test_cases = [
        (0.11, "0.11%"),
        (0.50, "0.50%"),
        (1.00, "1.00%"),
        (11.00, "11.00%"),
        (69.38, "69.38%"),
    ]
    
    for value, expected in test_cases:
        result = format_metric_value("unemployment_percent", value)
        assert result == expected, f"Expected {expected}, got {result} for value {value}"
