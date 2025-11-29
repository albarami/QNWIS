"""
Unit tests for FinancialEngine.

Tests cover:
- NPV calculation correctness
- IRR calculation correctness
- Payback period calculation
- Sensitivity analysis scenarios
- Option comparison with weighted scoring
- Data confidence thresholds
- Input validation
"""

from __future__ import annotations

import math
from typing import List

import pytest

from src.qnwis.engines.financial_engine import (
    CashFlowInput,
    FinancialEngine,
    FinancialModelInput,
    FinancialModelOutput,
    SensitivityScenario,
    calculate_simple_irr,
    calculate_simple_npv,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def engine() -> FinancialEngine:
    """Create a FinancialEngine instance."""
    return FinancialEngine()


@pytest.fixture
def simple_cash_flows() -> List[CashFlowInput]:
    """Simple test case: -100 investment, +50 per year for 3 years."""
    return [
        CashFlowInput(year=0, investment=100, revenue=0, operating_costs=0, source="test"),
        CashFlowInput(year=1, investment=0, revenue=50, operating_costs=0, source="test"),
        CashFlowInput(year=2, investment=0, revenue=50, operating_costs=0, source="test"),
        CashFlowInput(year=3, investment=0, revenue=50, operating_costs=0, source="test"),
    ]


@pytest.fixture
def option_a_input() -> FinancialModelInput:
    """Option A: Higher investment, higher returns."""
    return FinancialModelInput(
        option_name="Option A",
        option_description="High investment, high return option",
        cash_flows=[
            CashFlowInput(year=0, investment=100, source="Budget document"),
            CashFlowInput(year=1, revenue=60, operating_costs=10, source="Projections"),
            CashFlowInput(year=2, revenue=70, operating_costs=12, source="Projections"),
            CashFlowInput(year=3, revenue=80, operating_costs=15, source="Projections"),
        ],
        discount_rate=0.10,
        discount_rate_source="Corporate cost of capital",
    )


@pytest.fixture
def option_b_input() -> FinancialModelInput:
    """Option B: Lower investment, lower returns."""
    return FinancialModelInput(
        option_name="Option B",
        option_description="Low investment, moderate return option",
        cash_flows=[
            CashFlowInput(year=0, investment=50, source="Budget document"),
            CashFlowInput(year=1, revenue=30, operating_costs=5, source="Projections"),
            CashFlowInput(year=2, revenue=35, operating_costs=6, source="Projections"),
            CashFlowInput(year=3, revenue=40, operating_costs=7, source="Projections"),
        ],
        discount_rate=0.10,
        discount_rate_source="Corporate cost of capital",
    )


# ============================================================================
# NPV TESTS
# ============================================================================


class TestNPVCalculation:
    """Tests for Net Present Value calculation."""

    def test_npv_simple_case(self, engine: FinancialEngine) -> None:
        """Test NPV with simple cash flows."""
        # -100 investment, +50 per year for 3 years at 10% discount rate
        # NPV = -100 + 50/1.1 + 50/1.21 + 50/1.331 ≈ 24.34
        cash_flows = [-100, 50, 50, 50]
        npv = engine._calculate_npv(cash_flows, 0.10)
        
        assert abs(npv - 24.34) < 1.0, f"Expected NPV ≈ 24.34, got {npv}"

    def test_npv_zero_discount_rate(self, engine: FinancialEngine) -> None:
        """NPV with 0% discount should equal sum of cash flows."""
        cash_flows = [-100, 50, 50, 50]
        npv = engine._calculate_npv(cash_flows, 0.001)  # Near-zero
        
        # Sum = -100 + 50 + 50 + 50 = 50
        assert abs(npv - 50) < 2.0, f"Expected NPV ≈ 50, got {npv}"

    def test_npv_high_discount_rate(self, engine: FinancialEngine) -> None:
        """NPV should be lower with higher discount rates."""
        cash_flows = [-100, 50, 50, 50]
        
        npv_low = engine._calculate_npv(cash_flows, 0.05)
        npv_high = engine._calculate_npv(cash_flows, 0.20)
        
        assert npv_low > npv_high, "Higher discount rate should result in lower NPV"

    def test_npv_negative_project(self, engine: FinancialEngine) -> None:
        """Test NPV for a project that loses money."""
        cash_flows = [-100, 20, 20, 20]  # Only returns 60 total
        npv = engine._calculate_npv(cash_flows, 0.10)
        
        assert npv < 0, f"Expected negative NPV, got {npv}"


class TestSimpleNPVFunction:
    """Tests for the convenience NPV function."""

    def test_calculate_simple_npv(self) -> None:
        """Test the convenience function."""
        npv = calculate_simple_npv([-100, 50, 50, 50], 0.10)
        assert abs(npv - 24.34) < 1.0


# ============================================================================
# IRR TESTS
# ============================================================================


class TestIRRCalculation:
    """Tests for Internal Rate of Return calculation."""

    def test_irr_simple_case(self, engine: FinancialEngine) -> None:
        """Test IRR with a known result."""
        # -100 investment, returns 150 after 1 year = 50% return
        cash_flows = [-100, 150]
        irr = engine._calculate_irr(cash_flows)
        
        assert abs(irr - 0.50) < 0.01, f"Expected IRR ≈ 50%, got {irr * 100}%"

    def test_irr_multi_year(self, engine: FinancialEngine) -> None:
        """Test IRR with multiple years."""
        # -100 now, +50 for 3 years: IRR ≈ 23.4%
        cash_flows = [-100, 50, 50, 50]
        irr = engine._calculate_irr(cash_flows)
        
        assert 0.20 < irr < 0.30, f"Expected IRR ≈ 23%, got {irr * 100}%"

    def test_irr_negative_project(self, engine: FinancialEngine) -> None:
        """Test IRR for a project that loses money."""
        cash_flows = [-100, 20, 20, 20]  # Negative NPV at reasonable rates
        irr = engine._calculate_irr(cash_flows)
        
        # IRR should be negative or very low
        assert irr < 0.10, f"Expected low/negative IRR, got {irr * 100}%"


class TestSimpleIRRFunction:
    """Tests for the convenience IRR function."""

    def test_calculate_simple_irr(self) -> None:
        """Test the convenience function."""
        irr = calculate_simple_irr([-100, 150])
        assert abs(irr - 0.50) < 0.01


# ============================================================================
# PAYBACK TESTS
# ============================================================================


class TestPaybackCalculation:
    """Tests for payback period calculation."""

    def test_payback_simple(self, engine: FinancialEngine, simple_cash_flows: List[CashFlowInput]) -> None:
        """Test payback with simple cash flows."""
        payback = engine._calculate_payback(simple_cash_flows)
        
        # -100 investment, +50 per year: payback in 2 years
        assert abs(payback - 2.0) < 0.1, f"Expected payback ≈ 2 years, got {payback}"

    def test_payback_fractional(self, engine: FinancialEngine) -> None:
        """Test payback with fractional year result."""
        cash_flows = [
            CashFlowInput(year=0, investment=100, source="test"),
            CashFlowInput(year=1, revenue=40, source="test"),
            CashFlowInput(year=2, revenue=40, source="test"),
            CashFlowInput(year=3, revenue=40, source="test"),
        ]
        
        payback = engine._calculate_payback(cash_flows)
        
        # -100 + 40 + 40 = -20 after year 2, need 20 more from year 3's 40
        # Payback = 2 + (20/40) = 2.5 years
        assert abs(payback - 2.5) < 0.1, f"Expected payback ≈ 2.5 years, got {payback}"

    def test_payback_never(self, engine: FinancialEngine) -> None:
        """Test project that never pays back."""
        cash_flows = [
            CashFlowInput(year=0, investment=100, source="test"),
            CashFlowInput(year=1, revenue=10, source="test"),
            CashFlowInput(year=2, revenue=10, source="test"),
        ]
        
        payback = engine._calculate_payback(cash_flows)
        
        assert payback == float("inf"), f"Expected infinite payback, got {payback}"


# ============================================================================
# FULL CALCULATION TESTS
# ============================================================================


class TestFullCalculation:
    """Tests for the complete calculate() method."""

    def test_calculate_valid_input(self, engine: FinancialEngine, option_a_input: FinancialModelInput) -> None:
        """Test calculation with valid inputs."""
        result = engine.calculate(option_a_input)
        
        assert result.input_validation_passed
        assert result.option_name == "Option A"
        assert result.npv != 0
        assert result.irr != 0
        assert result.total_investment > 0
        assert result.total_revenue > 0
        assert len(result.sensitivity_scenarios) == 6  # 6 standard scenarios

    def test_calculate_invalid_input_no_source(self, engine: FinancialEngine) -> None:
        """Test calculation with missing source/assumption."""
        invalid_input = FinancialModelInput(
            option_name="Invalid",
            option_description="Test",
            cash_flows=[
                CashFlowInput(year=0, investment=100),  # No source!
            ],
            discount_rate=0.10,
            discount_rate_source="Test",
        )
        
        result = engine.calculate(invalid_input)
        
        assert not result.input_validation_passed
        assert len(result.validation_warnings) > 0

    def test_calculate_sensitivity_analysis(self, engine: FinancialEngine, option_a_input: FinancialModelInput) -> None:
        """Test that sensitivity analysis runs correctly."""
        result = engine.calculate(option_a_input)
        
        # Should have 6 scenarios
        assert len(result.sensitivity_scenarios) == 6
        
        # Check scenario names
        scenario_names = [s.scenario_name for s in result.sensitivity_scenarios]
        assert "Revenue -20%" in scenario_names
        assert "Costs +30%" in scenario_names
        assert "Best Case" in scenario_names
        assert "Worst Case" in scenario_names
        
        # Best case should have higher NPV than worst case
        best_case = next(s for s in result.sensitivity_scenarios if s.scenario_name == "Best Case")
        worst_case = next(s for s in result.sensitivity_scenarios if s.scenario_name == "Worst Case")
        assert best_case.npv > worst_case.npv

    def test_calculate_data_confidence(self, engine: FinancialEngine) -> None:
        """Test that data confidence is calculated correctly."""
        low_confidence_input = FinancialModelInput(
            option_name="Low Confidence",
            option_description="Test",
            cash_flows=[
                CashFlowInput(year=0, investment=100, source="test", confidence=0.3),
                CashFlowInput(year=1, revenue=50, source="test", confidence=0.3),
            ],
            discount_rate=0.10,
            discount_rate_source="Test",
        )
        
        result = engine.calculate(low_confidence_input)
        
        assert result.data_confidence == 0.3

    def test_calculate_output_serialization(self, engine: FinancialEngine, option_a_input: FinancialModelInput) -> None:
        """Test that output can be serialized to dict."""
        result = engine.calculate(option_a_input)
        output_dict = result.to_dict()
        
        assert "option_name" in output_dict
        assert "metrics" in output_dict
        assert "npv" in output_dict["metrics"]
        assert "irr_pct" in output_dict["metrics"]
        assert "sensitivity" in output_dict
        assert len(output_dict["sensitivity"]) == 6


# ============================================================================
# COMPARISON TESTS
# ============================================================================


class TestOptionComparison:
    """Tests for comparing two options."""

    def test_compare_options_winner(
        self,
        engine: FinancialEngine,
        option_a_input: FinancialModelInput,
        option_b_input: FinancialModelInput,
    ) -> None:
        """Test that comparison correctly identifies winner."""
        result_a = engine.calculate(option_a_input)
        result_b = engine.calculate(option_b_input)
        
        comparison = engine.compare_options(result_a, result_b)
        
        assert "winner" in comparison
        assert "loser" in comparison
        assert "confidence" in comparison
        assert comparison["winner"] in ["Option A", "Option B"]
        assert comparison["loser"] in ["Option A", "Option B"]
        assert comparison["winner"] != comparison["loser"]

    def test_compare_options_scores(
        self,
        engine: FinancialEngine,
        option_a_input: FinancialModelInput,
        option_b_input: FinancialModelInput,
    ) -> None:
        """Test that comparison includes scores."""
        result_a = engine.calculate(option_a_input)
        result_b = engine.calculate(option_b_input)
        
        comparison = engine.compare_options(result_a, result_b)
        
        assert "scores" in comparison
        assert "Option A" in comparison["scores"]
        assert "Option B" in comparison["scores"]
        assert comparison["scores"]["Option A"] + comparison["scores"]["Option B"] > 0

    def test_compare_options_breakdown(
        self,
        engine: FinancialEngine,
        option_a_input: FinancialModelInput,
        option_b_input: FinancialModelInput,
    ) -> None:
        """Test that comparison includes metric breakdown."""
        result_a = engine.calculate(option_a_input)
        result_b = engine.calculate(option_b_input)
        
        comparison = engine.compare_options(result_a, result_b)
        
        assert "breakdown" in comparison
        assert "npv" in comparison["breakdown"]
        assert "irr" in comparison["breakdown"]
        assert "payback" in comparison["breakdown"]

    def test_compare_options_custom_weights(
        self,
        engine: FinancialEngine,
        option_a_input: FinancialModelInput,
        option_b_input: FinancialModelInput,
    ) -> None:
        """Test comparison with custom weights."""
        result_a = engine.calculate(option_a_input)
        result_b = engine.calculate(option_b_input)
        
        # Weight only NPV
        custom_weights = {
            "npv": 1.0,
            "irr": 0.0,
            "payback": 0.0,
            "risk_resilience": 0.0,
            "data_confidence": 0.0,
        }
        
        comparison = engine.compare_options(result_a, result_b, weights=custom_weights)
        
        assert comparison["weights_used"] == custom_weights

    def test_compare_options_recommendation(
        self,
        engine: FinancialEngine,
        option_a_input: FinancialModelInput,
        option_b_input: FinancialModelInput,
    ) -> None:
        """Test that comparison includes a recommendation."""
        result_a = engine.calculate(option_a_input)
        result_b = engine.calculate(option_b_input)
        
        comparison = engine.compare_options(result_a, result_b)
        
        assert "recommendation" in comparison
        assert comparison["winner"] in comparison["recommendation"]


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================


class TestInputValidation:
    """Tests for input validation."""

    def test_cash_flow_validation_negative_revenue(self) -> None:
        """Test that negative revenue is flagged."""
        cf = CashFlowInput(year=0, revenue=-100, source="test")
        errors = cf.validate()
        
        assert len(errors) > 0
        assert any("Revenue cannot be negative" in e for e in errors)

    def test_cash_flow_validation_negative_costs(self) -> None:
        """Test that negative costs are flagged."""
        cf = CashFlowInput(year=0, operating_costs=-50, source="test")
        errors = cf.validate()
        
        assert len(errors) > 0
        assert any("Operating costs cannot be negative" in e for e in errors)

    def test_cash_flow_validation_no_source(self) -> None:
        """Test that missing source is flagged."""
        cf = CashFlowInput(year=0, investment=100)
        errors = cf.validate()
        
        assert len(errors) > 0
        assert any("Must have either source or assumptions" in e for e in errors)

    def test_cash_flow_validation_with_assumption(self) -> None:
        """Test that assumption is accepted instead of source."""
        cf = CashFlowInput(year=0, investment=100, assumptions="Estimated based on similar projects")
        errors = cf.validate()
        
        # Should have no source/assumption error
        assert not any("Must have either source or assumptions" in e for e in errors)

    def test_model_input_validation_high_discount_rate(self) -> None:
        """Test that high discount rate is flagged."""
        model = FinancialModelInput(
            option_name="Test",
            option_description="Test",
            cash_flows=[CashFlowInput(year=0, investment=100, source="test")],
            discount_rate=0.60,  # 60% - unrealistic
            discount_rate_source="test",
        )
        
        is_valid, errors = model.validate()
        
        assert not is_valid
        assert any("unrealistically high" in e for e in errors)

    def test_model_input_validation_no_discount_source(self) -> None:
        """Test that missing discount rate source is flagged."""
        model = FinancialModelInput(
            option_name="Test",
            option_description="Test",
            cash_flows=[CashFlowInput(year=0, investment=100, source="test")],
            discount_rate=0.10,
            discount_rate_source="",
        )
        
        is_valid, errors = model.validate()
        
        assert not is_valid
        assert any("Discount rate must have a source" in e for e in errors)


# ============================================================================
# DATA CONFIDENCE TESTS
# ============================================================================


class TestDataConfidence:
    """Tests for data confidence handling."""

    def test_high_confidence_data(self, engine: FinancialEngine) -> None:
        """Test with high confidence data."""
        high_conf_input = FinancialModelInput(
            option_name="High Confidence",
            option_description="Test",
            cash_flows=[
                CashFlowInput(year=0, investment=100, source="Audited", confidence=0.95),
                CashFlowInput(year=1, revenue=60, source="Contract", confidence=0.90),
            ],
            discount_rate=0.10,
            discount_rate_source="Central Bank",
        )
        
        result = engine.calculate(high_conf_input)
        
        assert result.data_confidence >= 0.9

    def test_low_confidence_data(self, engine: FinancialEngine) -> None:
        """Test with low confidence data."""
        low_conf_input = FinancialModelInput(
            option_name="Low Confidence",
            option_description="Test",
            cash_flows=[
                CashFlowInput(year=0, investment=100, source="Estimate", confidence=0.25),
                CashFlowInput(year=1, revenue=60, source="Assumption", confidence=0.25),
            ],
            discount_rate=0.10,
            discount_rate_source="Estimate",
        )
        
        result = engine.calculate(low_conf_input)
        
        assert result.data_confidence <= 0.30


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_year_cash_flow(self, engine: FinancialEngine) -> None:
        """Test with single year (immediate return)."""
        input_data = FinancialModelInput(
            option_name="Instant Return",
            option_description="Immediate payoff",
            cash_flows=[
                CashFlowInput(year=0, investment=100, revenue=150, source="test"),
            ],
            discount_rate=0.10,
            discount_rate_source="test",
        )
        
        result = engine.calculate(input_data)
        
        assert result.input_validation_passed
        assert result.npv == 50  # 150 - 100

    def test_very_long_horizon(self, engine: FinancialEngine) -> None:
        """Test with 30-year horizon."""
        cash_flows = [CashFlowInput(year=0, investment=1000, source="test")]
        for year in range(1, 31):
            cash_flows.append(CashFlowInput(year=year, revenue=100, source="test"))
        
        input_data = FinancialModelInput(
            option_name="Long Term",
            option_description="30 year project",
            cash_flows=cash_flows,
            discount_rate=0.08,
            discount_rate_source="test",
            time_horizon_years=30,
        )
        
        result = engine.calculate(input_data)
        
        assert result.input_validation_passed
        assert len(result.yearly_cash_flows) == 31

    def test_zero_investment(self, engine: FinancialEngine) -> None:
        """Test with zero investment (pure revenue)."""
        input_data = FinancialModelInput(
            option_name="No Investment",
            option_description="Pure revenue stream",
            cash_flows=[
                CashFlowInput(year=0, revenue=50, source="test"),
                CashFlowInput(year=1, revenue=50, source="test"),
            ],
            discount_rate=0.10,
            discount_rate_source="test",
        )
        
        result = engine.calculate(input_data)
        
        assert result.input_validation_passed
        assert result.total_investment == 0
        assert result.npv > 0

    def test_currency_formatting(self, engine: FinancialEngine) -> None:
        """Test currency formatting at different scales."""
        input_data = FinancialModelInput(
            option_name="Large Scale",
            option_description="Billions in value",
            cash_flows=[
                CashFlowInput(year=0, investment=5e9, source="test"),  # $5B
                CashFlowInput(year=1, revenue=2e9, source="test"),     # $2B
            ],
            discount_rate=0.08,
            discount_rate_source="test",
            currency="USD",
        )
        
        result = engine.calculate(input_data)
        
        # Check that formatting works for billions
        assert "B" in result.format_currency(result.npv) or "M" in result.format_currency(result.npv)

