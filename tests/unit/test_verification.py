"""
Unit tests for verification helpers.

Tests the pure verification logic extracted for Phase 1 Fix 1.1.
"""

import pytest

from src.qnwis.orchestration.verification_helpers import verify_agent_reports


def test_verification_with_valid_citations():
    """Test that verification passes with properly cited numbers."""
    agent_reports = [
        {
            "agent_name": "labour_economist",
            "narrative": (
                "Qatar produces [Per extraction: 'qatar_graduates' 347 from MoL] "
                "annually. This is concerning."
            ),
            "confidence": 0.7,
            "citations": [
                {
                    "metric": "qatar_graduates",
                    "value": "347",
                    "source": "MoL",
                    "confidence": 0.8,
                }
            ],
            "facts_used": ["qatar_graduates"],
            "assumptions": [],
            "data_gaps": [],
            "timestamp": "2025-11-16T00:00:00",
            "model": "claude-sonnet-4-5",
            "tokens_in": 1000,
            "tokens_out": 500,
        }
    ]

    extracted_facts = [
        {
            "metric": "qatar_graduates",
            "value": 347,
            "source": "MoL LMIS (stub)",
            "confidence": 0.8,
        }
    ]

    result = verify_agent_reports(agent_reports, extracted_facts)

    # Verification should pass
    assert result["total_citations"] == 1
    assert result["citation_violations"] == []
    assert result["number_violations"] == []
    assert result["warning_count"] == 0
    assert result["error_count"] == 0


def test_verification_catches_uncited_numbers():
    """Test that verification catches numbers without citations."""
    agent_reports = [
        {
            "agent_name": "labour_economist",
            "narrative": "Qatar needs 1,277 graduates annually. This is concerning.",
            "confidence": 0.7,
            "citations": [],
            "facts_used": [],
            "assumptions": [],
            "data_gaps": [],
            "timestamp": "2025-11-16T00:00:00",
            "model": "claude-sonnet-4-5",
            "tokens_in": 1000,
            "tokens_out": 500,
        }
    ]

    extracted_facts = []

    result = verify_agent_reports(agent_reports, extracted_facts)

    # Should catch the uncited number
    assert result["warning_count"] > 0
    assert len(result["citation_violations"]) > 0
    
    # Verify the violation contains the number
    violations_str = str(result["citation_violations"])
    assert "1277" in violations_str or "1,277" in violations_str


def test_verification_catches_number_mismatch():
    """Test that verification catches fabricated numbers beyond 2% tolerance."""
    agent_reports = [
        {
            "agent_name": "financial_economist",
            "narrative": (
                "Qatar GDP is [Per extraction: 'qatar_gdp' 500 from World Bank] billion. "
                "This is significant."
            ),
            "confidence": 0.8,
            "citations": [
                {
                    "metric": "qatar_gdp",
                    "value": "500",  # Fabricated - actual is 200
                    "source": "World Bank",
                    "confidence": 0.9,
                }
            ],
            "facts_used": ["qatar_gdp"],
            "assumptions": [],
            "data_gaps": [],
            "timestamp": "2025-11-16T00:00:00",
            "model": "claude-sonnet-4-5",
            "tokens_in": 1000,
            "tokens_out": 500,
        }
    ]

    extracted_facts = [
        {
            "metric": "qatar_gdp",
            "value": 200,  # Actual value
            "source": "World Bank API",
            "confidence": 0.95,
        }
    ]

    result = verify_agent_reports(agent_reports, extracted_facts)

    # Should catch the fabricated number (500 vs 200 is > 2% tolerance)
    assert result["error_count"] > 0
    assert len(result["number_violations"]) > 0
    
    violation = result["number_violations"][0]
    assert violation["metric"] == "qatar_gdp"
    assert violation["cited"] == 500.0
    assert violation["actual"] == 200.0


def test_verification_allows_2_percent_tolerance():
    """Test that verification allows values within 2% tolerance."""
    agent_reports = [
        {
            "agent_name": "labour_economist",
            "narrative": (
                "Qatar unemployment is [Per extraction: 'qatar_unemployment' 0.102 from MoL] "
                "which is concerning."
            ),
            "confidence": 0.75,
            "citations": [
                {
                    "metric": "qatar_unemployment",
                    "value": "0.102",  # 0.1 with small variance
                    "source": "MoL",
                    "confidence": 0.8,
                }
            ],
            "facts_used": ["qatar_unemployment"],
            "assumptions": [],
            "data_gaps": [],
            "timestamp": "2025-11-16T00:00:00",
            "model": "claude-sonnet-4-5",
            "tokens_in": 1000,
            "tokens_out": 500,
        }
    ]

    extracted_facts = [
        {
            "metric": "qatar_unemployment",
            "value": 0.1,  # Actual value
            "source": "MoL LMIS",
            "confidence": 0.8,
        }
    ]

    result = verify_agent_reports(agent_reports, extracted_facts)

    # Should pass - 0.102 vs 0.1 is within 2% tolerance
    assert result["number_violations"] == []
    assert result["error_count"] == 0


def test_verification_with_empty_reports():
    """Test that verification handles empty reports gracefully."""
    result = verify_agent_reports([], [])

    assert result["total_citations"] == 0
    assert result["total_numbers"] == 0
    assert result["citation_violations"] == []
    assert result["number_violations"] == []
    assert result["warning_count"] == 0
    assert result["error_count"] == 0


def test_verification_with_multiple_agents():
    """Test verification across multiple agent reports."""
    agent_reports = [
        {
            "agent_name": "labour_economist",
            "narrative": "Qatar produces [Per extraction: 'graduates' 347 from MoL] graduates.",
            "confidence": 0.7,
            "citations": [
                {"metric": "graduates", "value": "347", "source": "MoL", "confidence": 0.8}
            ],
            "facts_used": ["graduates"],
            "assumptions": [],
            "data_gaps": [],
            "timestamp": "2025-11-16T00:00:00",
            "model": "claude-sonnet-4-5",
            "tokens_in": 1000,
            "tokens_out": 500,
        },
        {
            "agent_name": "financial_economist",
            "narrative": "We need 1500 more graduates yearly.",  # No citation
            "confidence": 0.6,
            "citations": [],
            "facts_used": [],
            "assumptions": [],
            "data_gaps": [],
            "timestamp": "2025-11-16T00:00:00",
            "model": "claude-sonnet-4-5",
            "tokens_in": 1000,
            "tokens_out": 500,
        },
    ]

    extracted_facts = [
        {"metric": "graduates", "value": 347, "source": "MoL", "confidence": 0.8}
    ]

    result = verify_agent_reports(agent_reports, extracted_facts)

    # Should have 1 good citation from labour economist
    assert result["total_citations"] == 1
    
    # Should catch uncited number from financial economist
    assert result["warning_count"] > 0
    assert any("financial_economist" in str(v) for v in result["citation_violations"])
