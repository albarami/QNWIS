"""
Comprehensive Tests for All Engine B Services
Tests: Unit, Integration, Data Gathering, Math Accuracy
"""

import pytest
import numpy as np
from scipy import stats

# Import all services
from nsic.engine_b.services.monte_carlo import MonteCarloService, MonteCarloInput
from nsic.engine_b.services.sensitivity import SensitivityService, SensitivityInput
from nsic.engine_b.services.optimization import (
    OptimizationService, OptimizationInput, 
    OptimizationVariable, OptimizationConstraint
)
from nsic.engine_b.services.forecasting import ForecastingService, ForecastingInput
from nsic.engine_b.services.thresholds import ThresholdService, ThresholdInput, ThresholdConstraint
from nsic.engine_b.services.benchmarking import (
    BenchmarkingService, BenchmarkingInput, 
    BenchmarkMetric, PeerData
)
from nsic.engine_b.services.correlation import CorrelationService, CorrelationInput


# ============================================================================
# SENSITIVITY SERVICE TESTS
# ============================================================================

class TestSensitivityService:
    """Tests for Sensitivity Analysis Service."""
    
    @pytest.fixture
    def service(self):
        return SensitivityService(gpu_id=2)
    
    def test_health_check(self, service):
        health = service.health_check()
        assert health["status"] == "healthy"
        assert health["service"] == "sensitivity"
    
    def test_basic_analysis(self, service):
        """Basic sensitivity analysis."""
        input_spec = SensitivityInput(
            base_values={"a": 10, "b": 20, "c": 5},
            formula="a + b * 2 + c",
            n_steps=10,
        )
        
        result = service.analyze(input_spec)
        
        assert result.base_result == 55  # 10 + 20*2 + 5
        assert len(result.parameter_impacts) == 3
        assert len(result.top_drivers) <= 3
    
    def test_tornado_data_structure(self, service):
        """Tornado chart data should have correct structure."""
        input_spec = SensitivityInput(
            base_values={"x": 10, "y": 5},
            formula="x * y",
            ranges={"x": {"low": 5, "high": 15}, "y": {"low": 2, "high": 8}},
        )
        
        result = service.analyze(input_spec)
        
        for tornado in result.tornado_data:
            assert "parameter" in tornado
            assert "swing" in tornado
            assert "elasticity" in tornado
    
    def test_elasticity_calculation(self, service):
        """Elasticity should be correctly calculated."""
        # Linear function: y = 2x, elasticity should be ~1
        input_spec = SensitivityInput(
            base_values={"x": 10},
            formula="2 * x",
            ranges={"x": {"low": 8, "high": 12}},
        )
        
        result = service.analyze(input_spec)
        impact = result.parameter_impacts[0]
        
        # For linear function y=2x, elasticity = (dy/y)/(dx/x) = 1
        assert abs(impact.elasticity - 1.0) < 0.1
    
    def test_one_at_a_time(self, service):
        """Quick OAT sensitivity."""
        swings = service.one_at_a_time(
            base_values={"a": 10, "b": 20},
            formula="a + b",
            variation_pct=0.10,
        )
        
        # 10% of 10 = ±1, swing = 2
        # 10% of 20 = ±2, swing = 4
        assert abs(swings["a"] - 2.0) < 0.01
        assert abs(swings["b"] - 4.0) < 0.01


# ============================================================================
# OPTIMIZATION SERVICE TESTS
# ============================================================================

class TestOptimizationService:
    """Tests for Optimization Solver Service."""
    
    @pytest.fixture
    def service(self):
        return OptimizationService(gpu_id=3)
    
    def test_health_check(self, service):
        health = service.health_check()
        assert health["status"] == "healthy"
    
    def test_unconstrained_optimization(self, service):
        """Simple unconstrained minimization."""
        input_spec = OptimizationInput(
            variables=[
                OptimizationVariable("x", lower_bound=-10, upper_bound=10, initial_value=5),
            ],
            objective="(x - 3) ** 2",  # Minimum at x=3
            sense="minimize",
        )
        
        result = service.solve(input_spec)
        
        assert result.converged
        assert abs(result.optimal_values["x"] - 3.0) < 0.1
    
    def test_constrained_optimization(self, service):
        """Optimization with constraints."""
        input_spec = OptimizationInput(
            variables=[
                OptimizationVariable("x", lower_bound=0, upper_bound=100, initial_value=50),
                OptimizationVariable("y", lower_bound=0, upper_bound=100, initial_value=50),
            ],
            objective="x + y",
            sense="maximize",
            constraints=[
                OptimizationConstraint("100 - x - y", "ineq", "Budget <= 100"),
            ],
        )
        
        result = service.solve(input_spec)
        
        # Maximum should use full budget
        assert result.optimal_values["x"] + result.optimal_values["y"] <= 100.1
    
    def test_budget_allocation_scenario(self, service):
        """Realistic budget allocation problem."""
        input_spec = OptimizationInput(
            variables=[
                OptimizationVariable("training", lower_bound=0, upper_bound=100, initial_value=30),
                OptimizationVariable("incentives", lower_bound=0, upper_bound=100, initial_value=30),
                OptimizationVariable("marketing", lower_bound=0, upper_bound=50, initial_value=20),
            ],
            objective="0.4 * training + 0.35 * incentives + 0.1 * marketing",
            sense="maximize",
            constraints=[
                OptimizationConstraint(
                    "150 - training - incentives - marketing",
                    "ineq",
                    "Total budget <= 150M"
                ),
            ],
        )
        
        result = service.solve(input_spec)
        
        assert result.feasible
        total = sum(result.optimal_values.values())
        assert total <= 150.1


# ============================================================================
# FORECASTING SERVICE TESTS
# ============================================================================

class TestForecastingService:
    """Tests for Time Series Forecasting Service."""
    
    @pytest.fixture
    def service(self):
        return ForecastingService(gpu_id=4)
    
    def test_health_check(self, service):
        health = service.health_check()
        assert health["status"] == "healthy"
    
    def test_linear_trend(self, service):
        """Forecast linear trend."""
        input_spec = ForecastingInput(
            historical_values=[10, 12, 14, 16, 18],  # Linear: y = 10 + 2*x
            forecast_horizon=3,
            method="linear",
        )
        
        result = service.forecast(input_spec)
        
        assert result.trend == "increasing"
        assert abs(result.trend_slope - 2.0) < 0.1
        
        # Forecasts should continue trend
        assert result.forecasts[0].point_forecast > 18
    
    def test_confidence_intervals(self, service):
        """Confidence intervals should contain point forecast."""
        input_spec = ForecastingInput(
            historical_values=[10, 11, 12, 13, 14],
            forecast_horizon=5,
            confidence_level=0.95,
        )
        
        result = service.forecast(input_spec)
        
        for fc in result.forecasts:
            assert fc.lower_bound <= fc.point_forecast <= fc.upper_bound
    
    def test_fit_metrics(self, service):
        """Fit metrics should be reasonable."""
        input_spec = ForecastingInput(
            historical_values=[10, 12, 11, 13, 12, 14],
            forecast_horizon=3,
        )
        
        result = service.forecast(input_spec)
        
        assert result.mape >= 0  # MAPE is non-negative
        assert result.rmse >= 0  # RMSE is non-negative
    
    def test_qatarization_projection(self, service):
        """Realistic Qatarization rate projection."""
        input_spec = ForecastingInput(
            historical_values=[0.35, 0.37, 0.39, 0.40, 0.42],  # 2019-2023
            time_labels=["2019", "2020", "2021", "2022", "2023"],
            forecast_horizon=5,  # To 2028
            confidence_level=0.95,
        )
        
        result = service.forecast(input_spec)
        
        assert result.trend == "increasing"
        
        # 5-year forecast should be reasonable
        final_forecast = result.forecasts[-1].point_forecast
        assert 0.40 <= final_forecast <= 0.70


# ============================================================================
# THRESHOLDS SERVICE TESTS
# ============================================================================

class TestThresholdService:
    """Tests for Threshold Detection Service."""
    
    @pytest.fixture
    def service(self):
        return ThresholdService(gpu_id=5)
    
    def test_health_check(self, service):
        health = service.health_check()
        assert health["status"] == "healthy"
    
    def test_threshold_detection(self, service):
        """Detect threshold crossing."""
        input_spec = ThresholdInput(
            sweep_variable="x",
            sweep_range=(0, 10),
            fixed_variables={"x": 3},
            constraints=[
                ThresholdConstraint(
                    expression="x - 5",
                    threshold_type="upper",
                    target=0,
                    description="x must be < 5",
                ),
            ],
        )
        
        result = service.analyze(input_spec)
        
        assert len(result.thresholds) == 1
        assert abs(result.thresholds[0].threshold_value - 5.0) < 0.1
    
    def test_safe_range_calculation(self, service):
        """Safe range should be within bounds."""
        input_spec = ThresholdInput(
            sweep_variable="rate",
            sweep_range=(0.3, 0.8),
            fixed_variables={"rate": 0.42},
            constraints=[
                ThresholdConstraint(
                    expression="rate - 0.35",
                    threshold_type="lower",
                    target=0,
                    description="Rate must be >= 35%",
                ),
                ThresholdConstraint(
                    expression="rate - 0.70",
                    threshold_type="upper",
                    target=0,
                    description="Rate must be < 70%",
                ),
            ],
        )
        
        result = service.analyze(input_spec)
        
        if result.safe_range:
            assert result.safe_range[0] >= 0.3
            assert result.safe_range[1] <= 0.8


# ============================================================================
# BENCHMARKING SERVICE TESTS
# ============================================================================

class TestBenchmarkingService:
    """Tests for Benchmarking Service."""
    
    @pytest.fixture
    def service(self):
        return BenchmarkingService(gpu_id=6)
    
    def test_health_check(self, service):
        health = service.health_check()
        assert health["status"] == "healthy"
    
    def test_basic_benchmarking(self, service):
        """Basic peer comparison."""
        input_spec = BenchmarkingInput(
            metrics=[
                BenchmarkMetric(
                    name="Test Metric",
                    qatar_value=50,
                    peers=[
                        PeerData("Peer A", 40),
                        PeerData("Peer B", 60),
                        PeerData("Peer C", 55),
                    ],
                    higher_is_better=True,
                ),
            ],
        )
        
        result = service.benchmark(input_spec)
        
        assert len(result.metric_benchmarks) == 1
        mb = result.metric_benchmarks[0]
        
        assert mb.qatar_value == 50
        assert mb.peer_mean == pytest.approx((40 + 60 + 55) / 3)
    
    def test_ranking(self, service):
        """Ranking should be correct."""
        input_spec = BenchmarkingInput(
            metrics=[
                BenchmarkMetric(
                    name="Score",
                    qatar_value=90,  # Best
                    peers=[
                        PeerData("A", 80),
                        PeerData("B", 70),
                        PeerData("C", 60),
                    ],
                    higher_is_better=True,
                ),
            ],
        )
        
        result = service.benchmark(input_spec)
        
        # Qatar should be rank 1 (best)
        assert result.metric_benchmarks[0].qatar_rank == 1
    
    def test_gcc_comparison(self, service):
        """Realistic GCC peer comparison."""
        input_spec = BenchmarkingInput(
            metrics=[
                BenchmarkMetric(
                    name="Nationalization Rate",
                    qatar_value=0.42,
                    peers=[
                        PeerData("UAE", 0.35, "MENA", "high"),
                        PeerData("Saudi Arabia", 0.45, "MENA", "high"),
                        PeerData("Kuwait", 0.38, "MENA", "high"),
                        PeerData("Bahrain", 0.40, "MENA", "high"),
                        PeerData("Oman", 0.48, "MENA", "high"),
                    ],
                    higher_is_better=True,
                    target=0.60,
                ),
            ],
        )
        
        result = service.benchmark(input_spec)
        
        mb = result.metric_benchmarks[0]
        assert mb.gap_to_target < 0  # Below target
        assert mb.best_peer.name == "Oman"


# ============================================================================
# CORRELATION SERVICE TESTS
# ============================================================================

class TestCorrelationService:
    """Tests for Correlation Analysis Service."""
    
    @pytest.fixture
    def service(self):
        return CorrelationService(gpu_id=7)
    
    def test_health_check(self, service):
        health = service.health_check()
        assert health["status"] == "healthy"
    
    def test_perfect_correlation(self, service):
        """Perfect positive correlation."""
        input_spec = CorrelationInput(
            data={
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],  # y = 2x
            },
            methods=["pearson"],
        )
        
        result = service.analyze(input_spec)
        
        # Find the x-y pair
        for pair in result.all_pairs:
            if pair.variable_1 != pair.variable_2:
                assert pair.pearson_r == pytest.approx(1.0, abs=0.01)
    
    def test_negative_correlation(self, service):
        """Negative correlation detection."""
        input_spec = CorrelationInput(
            data={
                "x": [1, 2, 3, 4, 5],
                "y": [10, 8, 6, 4, 2],  # Decreasing
            },
        )
        
        result = service.analyze(input_spec)
        
        for pair in result.all_pairs:
            if pair.variable_1 != pair.variable_2:
                assert pair.pearson_r < 0
                assert pair.relationship in ["strong_negative", "moderate_negative"]
    
    def test_driver_analysis(self, service):
        """Driver analysis for target variable."""
        input_spec = CorrelationInput(
            data={
                "target": [10, 15, 20, 25, 30],
                "driver1": [1, 2, 3, 4, 5],  # Strong correlation
                "driver2": [5, 4, 3, 2, 1],  # Strong negative
                "noise": [3, 1, 4, 1, 5],    # Random
            },
            target_variable="target",
        )
        
        result = service.analyze(input_spec)
        
        assert result.driver_analysis is not None
        assert "driver1" in result.driver_analysis.top_positive_drivers
        assert "driver2" in result.driver_analysis.top_negative_drivers
    
    def test_multicollinearity_warning(self, service):
        """Detect multicollinearity."""
        input_spec = CorrelationInput(
            data={
                "x": [1, 2, 3, 4, 5],
                "y": [1.1, 2.1, 3.1, 4.1, 5.1],  # Almost identical
                "target": [10, 20, 30, 40, 50],
            },
            target_variable="target",
        )
        
        result = service.analyze(input_spec)
        
        # Should warn about x and y being highly correlated
        assert len(result.multicollinearity_warnings) > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestServiceIntegration:
    """Integration tests across multiple services."""
    
    def test_all_services_initialize(self):
        """All services should initialize without error."""
        services = [
            MonteCarloService(gpu_ids=[0, 1]),
            SensitivityService(gpu_id=2),
            OptimizationService(gpu_id=3),
            ForecastingService(gpu_id=4),
            ThresholdService(gpu_id=5),
            BenchmarkingService(gpu_id=6),
            CorrelationService(gpu_id=7),
        ]
        
        for service in services:
            health = service.health_check()
            assert health["status"] == "healthy"
    
    def test_combined_policy_analysis(self):
        """Combined analysis for policy question."""
        # Monte Carlo for feasibility
        mc_service = MonteCarloService()
        mc_result = mc_service.simulate(MonteCarloInput(
            variables={
                "rate": {"mean": 0.42, "std": 0.02},
                "growth": {"mean": 0.03, "std": 0.01},
            },
            formula="rate + growth * 5",
            success_condition="result >= 0.55",
            n_simulations=5000,
            seed=42,
        ))
        
        # Forecasting for projection
        fc_service = ForecastingService()
        fc_result = fc_service.forecast(ForecastingInput(
            historical_values=[0.35, 0.37, 0.39, 0.40, 0.42],
            forecast_horizon=5,
        ))
        
        # Sensitivity for drivers
        sens_service = SensitivityService()
        sens_result = sens_service.analyze(SensitivityInput(
            base_values={"rate": 0.42, "growth": 0.03},
            formula="rate + growth * 5",
        ))
        
        # All results should be valid
        assert 0 <= mc_result.success_rate <= 1
        assert fc_result.trend in ["increasing", "decreasing", "stable", "volatile"]
        assert len(sens_result.top_drivers) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
