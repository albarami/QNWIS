"""
Tests for Monte Carlo Simulation Service
Tests: Unit, Data Gathering, Math Accuracy
"""

import pytest
import numpy as np
from nsic.engine_b.services.monte_carlo import (
    MonteCarloService,
    MonteCarloInput,
    MonteCarloResult,
)


class TestMonteCarloUnit:
    """Unit tests for Monte Carlo service."""
    
    @pytest.fixture
    def service(self):
        return MonteCarloService(gpu_ids=[0, 1])
    
    def test_health_check(self, service):
        """Service should report healthy status."""
        health = service.health_check()
        assert health["status"] == "healthy"
        assert health["service"] == "monte_carlo"
    
    def test_basic_simulation(self, service):
        """Basic simulation should return valid results."""
        input_spec = MonteCarloInput(
            variables={"x": {"mean": 10, "std": 2, "distribution": "normal"}},
            formula="x",
            success_condition="result > 8",
            n_simulations=1000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        assert isinstance(result, MonteCarloResult)
        assert 0 <= result.success_rate <= 1
        assert result.n_simulations == 1000
        assert result.execution_time_ms > 0
    
    def test_reproducibility_with_seed(self, service):
        """Same seed should produce same results."""
        input_spec = MonteCarloInput(
            variables={"x": {"mean": 10, "std": 2}},
            formula="x * 2",
            success_condition="result > 15",
            n_simulations=1000,
            seed=12345,
        )
        
        result1 = service.simulate(input_spec)
        result2 = service.simulate(input_spec)
        
        assert result1.success_rate == result2.success_rate
        assert result1.mean_result == result2.mean_result
    
    def test_multi_variable_simulation(self, service):
        """Simulation with multiple variables."""
        input_spec = MonteCarloInput(
            variables={
                "rate": {"mean": 0.42, "std": 0.02},
                "growth": {"mean": 0.03, "std": 0.01},
                "years": {"mean": 5, "std": 0},  # Fixed value
            },
            formula="rate + growth * years",
            success_condition="result >= 0.55",
            n_simulations=5000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        assert result.n_simulations == 5000
        assert "rate" in result.variable_contributions
        assert "growth" in result.variable_contributions
    
    def test_different_distributions(self, service):
        """Test different probability distributions."""
        distributions = [
            {"mean": 10, "std": 2, "distribution": "normal"},
            {"mean": 10, "std": 2, "distribution": "uniform"},
            {"mean": 10, "std": 2, "distribution": "lognormal"},
            {"low": 5, "mode": 10, "high": 15, "distribution": "triangular"},
        ]
        
        for dist in distributions:
            input_spec = MonteCarloInput(
                variables={"x": dist},
                formula="x",
                success_condition="result > 5",
                n_simulations=1000,
                seed=42,
            )
            
            result = service.simulate(input_spec)
            assert result.success_rate > 0
    
    def test_percentiles_ordered(self, service):
        """Percentiles should be in order."""
        input_spec = MonteCarloInput(
            variables={"x": {"mean": 50, "std": 10}},
            formula="x",
            success_condition="result > 0",
            n_simulations=10000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        assert result.percentiles["p5"] <= result.percentiles["p25"]
        assert result.percentiles["p25"] <= result.percentiles["p50"]
        assert result.percentiles["p50"] <= result.percentiles["p75"]
        assert result.percentiles["p75"] <= result.percentiles["p95"]


class TestMonteCarloMathAccuracy:
    """Math accuracy tests for Monte Carlo service."""
    
    @pytest.fixture
    def service(self):
        return MonteCarloService(gpu_ids=[0, 1])
    
    def test_normal_distribution_properties(self, service):
        """Normal distribution should produce expected statistics."""
        mean, std = 100, 15
        
        input_spec = MonteCarloInput(
            variables={"x": {"mean": mean, "std": std, "distribution": "normal"}},
            formula="x",
            success_condition="result > 0",
            n_simulations=50000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # Mean should be within 1% of target
        assert abs(result.mean_result - mean) / mean < 0.01
        
        # Std should be within 5% of target
        assert abs(result.std_result - std) / std < 0.05
    
    def test_success_rate_accuracy(self, service):
        """Success rate should match theoretical probability."""
        # P(X > 0) for N(0, 1) should be ~50%
        input_spec = MonteCarloInput(
            variables={"x": {"mean": 0, "std": 1}},
            formula="x",
            success_condition="result > 0",
            n_simulations=50000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # Should be ~50% with small margin
        assert 0.48 <= result.success_rate <= 0.52
    
    def test_var_calculation(self, service):
        """VaR should be at correct percentile."""
        input_spec = MonteCarloInput(
            variables={"x": {"mean": 100, "std": 10}},
            formula="x",
            success_condition="result > 0",
            n_simulations=50000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # 5th percentile of N(100, 10) ≈ 100 - 1.645*10 ≈ 83.55
        theoretical_var = 100 - 1.645 * 10
        assert abs(result.var_95 - theoretical_var) < 2
    
    def test_sensitivity_sums_to_one(self, service):
        """Variable contributions should sum to approximately 1."""
        input_spec = MonteCarloInput(
            variables={
                "a": {"mean": 10, "std": 2},
                "b": {"mean": 20, "std": 3},
                "c": {"mean": 5, "std": 1},
            },
            formula="a + b + c",
            success_condition="result > 0",
            n_simulations=10000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        total = sum(result.variable_contributions.values())
        assert 0.9 <= total <= 1.1  # Allow small numerical error


class TestMonteCarloDataGathering:
    """Data gathering tests - ensure service handles real-world data patterns."""
    
    @pytest.fixture
    def service(self):
        return MonteCarloService(gpu_ids=[0, 1])
    
    def test_qatarization_scenario(self, service):
        """Test with realistic Qatarization policy scenario."""
        input_spec = MonteCarloInput(
            variables={
                "current_rate": {"mean": 0.42, "std": 0.02, "distribution": "normal"},
                "annual_growth": {"mean": 0.03, "std": 0.01, "distribution": "normal"},
                "economic_factor": {"mean": 1.0, "std": 0.1, "distribution": "lognormal"},
            },
            formula="current_rate + annual_growth * 5 * economic_factor",
            success_condition="result >= 0.60",  # 60% target
            n_simulations=10000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # Should have reasonable success rate
        assert 0 <= result.success_rate <= 1
        
        # Mean should be in reasonable range
        assert 0.30 <= result.mean_result <= 0.80
        
        # Should identify key drivers
        assert len(result.variable_contributions) == 3
    
    def test_edge_case_zero_variance(self, service):
        """Handle zero variance (fixed) variables."""
        input_spec = MonteCarloInput(
            variables={
                "fixed": {"mean": 10, "std": 0},  # Fixed value
                "random": {"mean": 5, "std": 2},
            },
            formula="fixed + random",
            success_condition="result > 12",
            n_simulations=1000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # Should handle without error
        assert result.mean_result > 10  # At least the fixed value
    
    def test_edge_case_extreme_values(self, service):
        """Handle extreme parameter values."""
        input_spec = MonteCarloInput(
            variables={
                "large": {"mean": 1e6, "std": 1e5},
                "small": {"mean": 1e-6, "std": 1e-7},
            },
            formula="large * small",
            success_condition="result > 0",
            n_simulations=1000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # Should handle without overflow
        assert not np.isnan(result.mean_result)
        assert not np.isinf(result.mean_result)
    
    def test_historical_data_scenario(self, service):
        """Test with parameters derived from historical data."""
        # Simulated historical stats for unemployment rate
        input_spec = MonteCarloInput(
            variables={
                "unemployment": {"mean": 0.05, "std": 0.015, "distribution": "beta", "alpha": 2, "beta": 38},
                "gdp_growth": {"mean": 0.03, "std": 0.02, "distribution": "normal"},
            },
            formula="unemployment * (1 - gdp_growth * 5)",
            success_condition="result < 0.04",  # Target: below 4%
            n_simulations=10000,
            seed=42,
        )
        
        result = service.simulate(input_spec)
        
        # Should produce valid results
        assert 0 <= result.success_rate <= 1
        assert result.min_result >= 0  # Unemployment can't be negative


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
