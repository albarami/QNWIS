"""
Unit tests for orchestration verification harness.

Tests numeric invariant checking for agent outputs including
percent bounds, YoY growth limits, and sum-to-one constraints.
"""

import pytest

from src.qnwis.agents.base import AgentReport, Insight
from src.qnwis.orchestration.verification import (
    VerificationResult,
    verify_insight,
    verify_report,
)


def test_verification_passes_valid_percent():
    """Verify that valid percent values pass without issues."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"male_percent": 60.0, "female_percent": 40.0},
    )
    result = verify_insight(ins)
    assert isinstance(result, VerificationResult)
    assert len(result.issues) == 0


def test_verification_fails_negative_percent():
    """Verify that negative percent values generate warnings."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"male_percent": -5.0},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 1
    assert result.issues[0].level == "warn"
    assert result.issues[0].code == "percent_range"
    assert "male_percent=-5.0" in result.issues[0].detail


def test_verification_fails_excessive_percent():
    """Verify that percent values over 100 generate warnings."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"total_percent": 105.2},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 1
    assert result.issues[0].level == "warn"
    assert result.issues[0].code == "percent_range"
    assert "total_percent=105.2" in result.issues[0].detail


def test_verification_yoy_within_bounds():
    """Verify that reasonable YoY values pass."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"yoy_percent": 15.3},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 0


def test_verification_yoy_extreme_negative():
    """Verify that extreme negative YoY values generate warnings."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"yoy_percent": -150.0},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 1
    assert result.issues[0].level == "warn"
    assert result.issues[0].code == "yoy_outlier"


def test_verification_yoy_extreme_positive():
    """Verify that extreme positive YoY values generate warnings."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"yoy_percent": 250.0},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 1
    assert result.issues[0].level == "warn"
    assert result.issues[0].code == "yoy_outlier"


def test_verification_sum_to_one_valid():
    """Verify that gender percentages summing to total pass."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={
            "male_percent": 60.0,
            "female_percent": 40.0,
            "total_percent": 100.0,
        },
    )
    result = verify_insight(ins)
    # No sum_to_one issues
    sum_issues = [i for i in result.issues if i.code == "sum_to_one"]
    assert len(sum_issues) == 0


def test_verification_sum_to_one_within_tolerance():
    """Verify that gender percentages within tolerance pass."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={
            "male_percent": 60.2,
            "female_percent": 39.9,
            "total_percent": 100.0,
        },
    )
    result = verify_insight(ins)
    # Within SUM_TOL = 0.5
    sum_issues = [i for i in result.issues if i.code == "sum_to_one"]
    assert len(sum_issues) == 0


def test_verification_sum_to_one_fails():
    """Verify that gender percentages not summing to total fail."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={
            "male_percent": 60.0,
            "female_percent": 40.0,
            "total_percent": 102.0,
        },
    )
    result = verify_insight(ins)
    sum_issues = [i for i in result.issues if i.code == "sum_to_one"]
    assert len(sum_issues) == 1
    assert sum_issues[0].level == "warn"


def test_verification_missing_gender_fields():
    """Verify that missing gender fields don't cause errors."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"male_percent": 60.0},  # missing female and total
    )
    result = verify_insight(ins)
    # No sum_to_one check if fields missing
    sum_issues = [i for i in result.issues if i.code == "sum_to_one"]
    assert len(sum_issues) == 0


def test_verification_non_numeric_values():
    """Verify that non-numeric values are ignored."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={
            "male_percent": "60.0",  # string, not numeric
            "description": "test",
        },
    )
    result = verify_insight(ins)
    assert len(result.issues) == 0


def test_verification_multiple_issues():
    """Verify that multiple issues are all detected."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={
            "male_percent": -5.0,  # negative
            "female_percent": 110.0,  # over 100
            "yoy_percent": -150.0,  # extreme YoY
        },
    )
    result = verify_insight(ins)
    assert len(result.issues) == 3
    codes = {i.code for i in result.issues}
    assert codes == {"percent_range", "yoy_outlier"}


def test_verify_report_aggregates_insight_issues():
    """Verify that report verification aggregates all insight issues."""
    report = AgentReport(
        agent="TestAgent",
        findings=[
            Insight(
                title="Finding 1",
                summary="Test",
                metrics={"male_percent": -5.0},
            ),
            Insight(
                title="Finding 2",
                summary="Test",
                metrics={"yoy_percent": 300.0},
            ),
        ],
    )
    result = verify_report(report)
    assert len(result.issues) == 2


def test_verify_report_empty_findings():
    """Verify that reports with no findings don't cause errors."""
    report = AgentReport(agent="TestAgent", findings=[])
    result = verify_report(report)
    assert isinstance(result, VerificationResult)
    assert len(result.issues) == 0


def test_verification_edge_case_exactly_zero():
    """Verify that exactly 0% is valid."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"female_percent": 0.0},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 0


def test_verification_edge_case_exactly_100():
    """Verify that exactly 100% is valid."""
    ins = Insight(
        title="Test",
        summary="Test insight",
        metrics={"total_percent": 100.0},
    )
    result = verify_insight(ins)
    assert len(result.issues) == 0


def test_verification_edge_case_yoy_bounds():
    """Verify YoY boundary values."""
    # Exactly at lower bound
    ins1 = Insight(title="Test", summary="Test", metrics={"yoy_percent": -100.0})
    result1 = verify_insight(ins1)
    assert len(result1.issues) == 0

    # Exactly at upper bound
    ins2 = Insight(title="Test", summary="Test", metrics={"yoy_percent": 200.0})
    result2 = verify_insight(ins2)
    assert len(result2.issues) == 0

    # Just beyond lower bound
    ins3 = Insight(title="Test", summary="Test", metrics={"yoy_percent": -100.1})
    result3 = verify_insight(ins3)
    assert len(result3.issues) == 1

    # Just beyond upper bound
    ins4 = Insight(title="Test", summary="Test", metrics={"yoy_percent": 200.1})
    result4 = verify_insight(ins4)
    assert len(result4.issues) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
