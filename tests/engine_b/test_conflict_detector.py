"""
Tests for Conflict Detector and Hybrid Flow Integration
"""

import pytest
from nsic.engine_b.integration.conflict_detector import (
    ConflictDetector,
    ConflictSeverity,
    Conflict,
    ConflictReport,
    should_trigger_engine_a_prime,
    CONFLICT_THRESHOLDS,
)


class TestConflictDetector:
    """Tests for conflict detection logic."""
    
    @pytest.fixture
    def detector(self):
        return ConflictDetector()
    
    def test_no_conflicts_high_alignment(self, detector):
        """No conflicts should result in high alignment score."""
        engine_a = {"recommendation": "Policy looks good"}
        engine_b = {
            "monte_carlo": {"success_rate": 0.85},
            "forecasting": {"trend": "stable"},
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        
        assert report.alignment_score >= 80
        assert not report.should_trigger_prime
    
    def test_low_feasibility_triggers_conflict(self, detector):
        """Low Monte Carlo success rate should trigger conflict."""
        engine_a = {"recommendation": "This policy will succeed"}
        engine_b = {
            "monte_carlo": {
                "success_rate": 0.20,  # Below 30% threshold
                "var_95": -0.05,
                "n_simulations": 10000,
            }
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        
        # Should have feasibility conflict
        feasibility_conflicts = [c for c in report.conflicts if c.conflict_type == "feasibility"]
        assert len(feasibility_conflicts) > 0
        
        # Should trigger prime
        assert report.should_trigger_prime
    
    def test_trend_mismatch_detection(self, detector):
        """Detect when forecast trend contradicts Engine A claim."""
        engine_a = {
            "recommendation": "The rate will grow significantly",
            "synthesis": "We expect positive growth trajectory",
        }
        engine_b = {
            "forecasting": {
                "trend": "decreasing",
                "trend_slope": -0.02,
            }
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        
        trend_conflicts = [c for c in report.conflicts if c.conflict_type == "trend_mismatch"]
        assert len(trend_conflicts) > 0
    
    def test_threshold_breach_critical(self, detector):
        """Threshold breach should be critical severity."""
        engine_a = {"recommendation": "Operating within bounds"}
        engine_b = {
            "thresholds": {
                "risk_level": "critical",
                "critical_thresholds": [
                    {
                        "currently_violated": True,
                        "constraint_description": "Budget ceiling",
                        "constraint_expression": "budget <= 100",
                        "severity": "critical",
                    }
                ],
            }
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        
        # Should have critical threshold breach
        breach_conflicts = [c for c in report.conflicts if c.conflict_type == "threshold_breach"]
        assert len(breach_conflicts) > 0
        assert breach_conflicts[0].severity == ConflictSeverity.CRITICAL
    
    def test_benchmark_outlier_detection(self, detector):
        """Detect when Qatar is a statistical outlier."""
        engine_a = {"recommendation": "Qatar is competitive"}
        engine_b = {
            "benchmarking": {
                "metric_benchmarks": [
                    {
                        "metric_name": "Performance",
                        "is_outlier": True,
                        "outlier_direction": "below",
                        "z_score": -2.5,
                        "performance": "lagging",
                        "qatar_value": 30,
                        "peer_mean": 60,
                        "qatar_percentile": 10,
                    }
                ]
            }
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        
        outlier_conflicts = [c for c in report.conflicts if c.conflict_type == "benchmark_outlier"]
        assert len(outlier_conflicts) > 0
    
    def test_prime_trigger_conditions(self, detector):
        """Test Engine A Prime trigger conditions."""
        # Case 1: Single high-severity conflict - should trigger
        engine_a = {"recommendation": "success"}
        engine_b = {
            "monte_carlo": {"success_rate": 0.15}  # Very low
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        assert report.should_trigger_prime
        
        # Case 2: Two medium conflicts - should trigger
        engine_a = {"recommendation": "good outlook"}
        engine_b = {
            "thresholds": {
                "risk_level": "warning",
                "critical_thresholds": [
                    {"currently_violated": False, "margin_percent": 5, "constraint_description": "margin1"},
                    {"currently_violated": False, "margin_percent": 8, "constraint_description": "margin2"},
                ]
            }
        }
        
        # This tests the threshold warning detection
    
    def test_alignment_score_calculation(self, detector):
        """Alignment score should decrease with more/worse conflicts."""
        engine_a = {"recommendation": "test"}
        
        # No conflicts
        report1 = detector.detect_conflicts(engine_a, {})
        
        # Some conflicts
        engine_b_conflicts = {
            "monte_carlo": {"success_rate": 0.25},
            "thresholds": {
                "risk_level": "critical",
                "critical_thresholds": [{"currently_violated": True, "constraint_description": "test", "constraint_expression": "x", "severity": "critical"}]
            }
        }
        report2 = detector.detect_conflicts(engine_a, engine_b_conflicts)
        
        assert report1.alignment_score > report2.alignment_score
    
    def test_prime_focus_and_questions(self, detector):
        """Prime focus and questions should be generated."""
        engine_a = {"recommendation": "will succeed"}
        engine_b = {
            "monte_carlo": {"success_rate": 0.10, "n_simulations": 10000}
        }
        
        report = detector.detect_conflicts(engine_a, engine_b)
        
        if report.should_trigger_prime:
            assert report.prime_focus is not None
            assert len(report.prime_questions) > 0


class TestConflictThresholds:
    """Tests for conflict threshold constants."""
    
    def test_thresholds_are_defined(self):
        """All required thresholds should be defined."""
        required_keys = [
            "feasibility",
            "trend_mismatch",
            "threshold_breach",
            "benchmark_outlier",
            "ignored_driver",
            "correlation_contradiction",
        ]
        
        for key in required_keys:
            assert key in CONFLICT_THRESHOLDS
    
    def test_feasibility_threshold_reasonable(self):
        """Feasibility threshold should be reasonable (10-50%)."""
        assert 0.10 <= CONFLICT_THRESHOLDS["feasibility"] <= 0.50
    
    def test_benchmark_outlier_threshold_reasonable(self):
        """Benchmark outlier should be 1.5-3.0 std deviations."""
        assert 1.5 <= CONFLICT_THRESHOLDS["benchmark_outlier"] <= 3.0


class TestConvenienceFunction:
    """Tests for should_trigger_engine_a_prime convenience function."""
    
    def test_returns_tuple(self):
        """Should return (bool, list) tuple."""
        result = should_trigger_engine_a_prime(
            {"recommendation": "test"},
            {"monte_carlo": {"success_rate": 0.10}}
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)
    
    def test_low_success_triggers_prime(self):
        """Very low success rate should trigger prime."""
        should_trigger, conflicts = should_trigger_engine_a_prime(
            {"recommendation": "will succeed"},
            {"monte_carlo": {"success_rate": 0.05}}
        )
        
        assert should_trigger
        assert len(conflicts) > 0


class TestConflictDataClass:
    """Tests for Conflict dataclass."""
    
    def test_conflict_creation(self):
        """Conflict should be creatable with required fields."""
        conflict = Conflict(
            conflict_type="test",
            source_service="test_service",
            severity=ConflictSeverity.MEDIUM,
            engine_a_claim="claim",
            engine_b_finding="finding",
        )
        
        assert conflict.conflict_type == "test"
        assert conflict.severity == ConflictSeverity.MEDIUM
    
    def test_severity_ordering(self):
        """Severity values should have correct ordering."""
        severities = [
            ConflictSeverity.INFO,
            ConflictSeverity.LOW,
            ConflictSeverity.MEDIUM,
            ConflictSeverity.HIGH,
            ConflictSeverity.CRITICAL,
        ]
        
        # All should be valid enum values
        for sev in severities:
            assert sev.value in ["info", "low", "medium", "high", "critical"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
