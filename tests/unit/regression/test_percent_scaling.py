"""
Regression tests for percent scaling fixes.

Ensures that percent values are not double-multiplied and follow
the QNWIS contract: upstream datasets store values already in percent units.
"""

import pytest
from src.qnwis.utils.percent import normalize_percent, format_percent


def test_percent_normalization_no_double_multiply():
    """0.11 means 0.11% in our data model, not 11%."""
    assert normalize_percent(0.11) == 0.11


def test_percent_normalization_corrects_mistaken_multiply():
    """If somewhere multiplied by 100 incorrectly, bring it back."""
    assert normalize_percent(11.0) == 0.11
    assert normalize_percent(569.0) == 5.69


def test_percent_normalization_regular_values_pass_through():
    """Regular percent values (0-10) pass through unchanged."""
    assert normalize_percent(5.66) == 5.66
    assert normalize_percent(0.0) == 0.0
    assert normalize_percent(10.0) == 10.0  # Boundary: exactly 10% passes through


def test_percent_normalization_handles_none():
    """None values pass through as None."""
    assert normalize_percent(None) is None


def test_percent_normalization_very_large_values():
    """Values >10000 are left unchanged (assumed to be counts, not percents)."""
    assert normalize_percent(15000) == 15000


def test_format_percent_basic():
    """Format percent values with proper symbol."""
    assert format_percent(0.11) == "0.11%"
    assert format_percent(5.66) == "5.66%"


def test_format_percent_corrects_scaling():
    """Format should normalize before displaying."""
    assert format_percent(11.0) == "0.11%"  # Corrected from mistaken multiply


def test_format_percent_handles_none():
    """None values display as N/A."""
    assert format_percent(None) == "N/A"


def test_format_percent_custom_decimals():
    """Support custom decimal places."""
    assert format_percent(5.666, decimals=1) == "5.7%"
    assert format_percent(5.666, decimals=3) == "5.666%"
