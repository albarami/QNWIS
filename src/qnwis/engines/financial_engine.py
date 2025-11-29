"""
Domain-Agnostic Financial Modeling Engine.

This engine performs financial calculations for ANY investment scenario.
ALL CALCULATIONS ARE DETERMINISTIC PYTHON MATH - NO LLM INVOLVEMENT.

Key Features:
- NPV (Net Present Value) calculation
- IRR (Internal Rate of Return) calculation
- Payback period calculation
- Sensitivity analysis (6 standard scenarios)
- Option comparison with weighted scoring

Works for any domain: infrastructure, healthcare, education, business, government.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import numpy_financial as npf
except ImportError:
    # Fallback implementations if numpy_financial not installed
    npf = None

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES - Structured inputs and outputs
# ============================================================================


@dataclass
class CashFlowInput:
    """
    Generic cash flow input - works for any domain.

    Examples:
    - Infrastructure: Year 0 investment, Years 1-10 revenues from operations
    - Healthcare: Year 0-2 equipment purchase, Years 1-10 patient revenues
    - Government: Year 0-5 program investment, Years 3-10 economic benefits
    """

    year: int
    investment: float = 0.0  # Negative = outflow (spending money)
    revenue: float = 0.0  # Positive = inflow (receiving money)
    operating_costs: float = 0.0  # Positive = outflow (ongoing expenses)
    source: str = ""  # Citation for these numbers
    assumptions: str = ""  # Explicit assumptions if estimated
    confidence: float = 1.0  # 0-1, how confident are we in this data?

    @property
    def net_cash_flow(self) -> float:
        """Calculate net cash flow for this year."""
        return self.revenue - self.operating_costs - abs(self.investment)

    def validate(self) -> List[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if self.revenue < 0:
            errors.append(
                f"Year {self.year}: Revenue cannot be negative ({self.revenue})"
            )
        if self.operating_costs < 0:
            errors.append(
                f"Year {self.year}: Operating costs cannot be negative ({self.operating_costs})"
            )
        if not self.source and not self.assumptions:
            errors.append(
                f"Year {self.year}: Must have either source or assumptions documented"
            )
        if self.confidence < 0 or self.confidence > 1:
            errors.append(
                f"Year {self.year}: Confidence must be between 0 and 1 ({self.confidence})"
            )
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "year": self.year,
            "investment": self.investment,
            "revenue": self.revenue,
            "operating_costs": self.operating_costs,
            "net_cash_flow": self.net_cash_flow,
            "source": self.source,
            "assumptions": self.assumptions,
            "confidence": self.confidence,
        }


@dataclass
class FinancialModelInput:
    """
    Complete input for financial modeling - domain agnostic.

    This structure works for any strategic decision:
    - Government: "Should we invest in Option A or Option B?"
    - Corporate: "Should we enter market X or market Y?"
    - Healthcare: "Should we expand ICU or oncology?"
    """

    option_name: str
    option_description: str
    cash_flows: List[CashFlowInput]
    discount_rate: float  # Cost of capital (e.g., 0.08 for 8%)
    discount_rate_source: str  # Why this rate?
    currency: str = "USD"
    currency_unit: str = "millions"  # "millions", "billions", "thousands"
    time_horizon_years: int = 10

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all inputs before calculation."""
        errors = []

        if not self.option_name:
            errors.append("Option name is required")

        if not self.cash_flows:
            errors.append("No cash flows provided")
            return False, errors

        for cf in self.cash_flows:
            errors.extend(cf.validate())

        if self.discount_rate <= 0:
            errors.append(f"Discount rate must be positive ({self.discount_rate})")
        elif self.discount_rate > 0.50:
            errors.append(
                f"Discount rate {self.discount_rate} (={self.discount_rate*100}%) "
                "seems unrealistically high"
            )

        if not self.discount_rate_source:
            errors.append("Discount rate must have a source/justification")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "option_name": self.option_name,
            "option_description": self.option_description,
            "cash_flows": [cf.to_dict() for cf in self.cash_flows],
            "discount_rate": self.discount_rate,
            "discount_rate_source": self.discount_rate_source,
            "currency": self.currency,
            "currency_unit": self.currency_unit,
            "time_horizon_years": self.time_horizon_years,
        }


@dataclass
class SensitivityScenario:
    """Result of a sensitivity analysis scenario."""

    scenario_name: str
    description: str
    npv: float
    irr: float
    npv_change_pct: float  # % change vs base case
    payback_years: float
    still_viable: bool  # Is NPV still positive?

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "scenario": self.scenario_name,
            "description": self.description,
            "npv": round(self.npv, 2),
            "irr_pct": round(self.irr * 100, 2),
            "npv_change_pct": round(self.npv_change_pct, 1),
            "payback_years": (
                round(self.payback_years, 1)
                if self.payback_years != float("inf")
                else "Never"
            ),
            "still_viable": self.still_viable,
        }


@dataclass
class FinancialModelOutput:
    """
    Complete output from financial modeling - all numbers CALCULATED.

    This output structure works for any domain.
    """

    option_name: str
    option_description: str

    # Core metrics (CALCULATED, not estimated)
    npv: float  # Net Present Value
    irr: float  # Internal Rate of Return (as decimal, e.g., 0.12 = 12%)
    payback_period_years: float  # Years until cumulative cash flow >= 0
    total_investment: float  # Sum of all investment outflows
    total_revenue: float  # Sum of all revenue
    total_costs: float  # Sum of all operating costs
    roi: float  # Return on Investment (as decimal)
    profitability_index: float  # (NPV + Investment) / Investment

    # Year-by-year breakdown
    yearly_cash_flows: List[Dict[str, Any]]
    cumulative_cash_flow: List[float]

    # Sensitivity analysis (all CALCULATED)
    sensitivity_scenarios: List[SensitivityScenario]

    # Metadata
    currency: str
    currency_unit: str
    discount_rate: float
    calculation_timestamp: str
    input_validation_passed: bool
    validation_warnings: List[str]
    data_confidence: float  # Average confidence of input data

    def format_currency(self, value: float) -> str:
        """Format a value with currency."""
        if abs(value) >= 1e9:
            return f"{self.currency} {value/1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"{self.currency} {value/1e6:.2f}M"
        elif abs(value) >= 1e3:
            return f"{self.currency} {value/1e3:.2f}K"
        else:
            return f"{self.currency} {value:.2f}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for state passing and display."""
        return {
            "option_name": self.option_name,
            "option_description": self.option_description,
            "metrics": {
                "npv": round(self.npv, 2),
                "npv_formatted": self.format_currency(self.npv),
                "irr_decimal": round(self.irr, 4),
                "irr_pct": round(self.irr * 100, 2),
                "irr_formatted": f"{self.irr * 100:.1f}%",
                "payback_years": (
                    round(self.payback_period_years, 1)
                    if self.payback_period_years != float("inf")
                    else "Never"
                ),
                "total_investment": round(self.total_investment, 2),
                "total_investment_formatted": self.format_currency(self.total_investment),
                "total_revenue": round(self.total_revenue, 2),
                "total_revenue_formatted": self.format_currency(self.total_revenue),
                "total_costs": round(self.total_costs, 2),
                "roi_decimal": round(self.roi, 4),
                "roi_pct": round(self.roi * 100, 2),
                "roi_formatted": f"{self.roi * 100:.1f}%",
                "profitability_index": round(self.profitability_index, 2),
            },
            "yearly_breakdown": self.yearly_cash_flows,
            "cumulative_cash_flow": [round(cf, 2) for cf in self.cumulative_cash_flow],
            "sensitivity": [s.to_dict() for s in self.sensitivity_scenarios],
            "metadata": {
                "currency": self.currency,
                "currency_unit": self.currency_unit,
                "discount_rate_pct": f"{self.discount_rate * 100:.1f}%",
                "calculated_at": self.calculation_timestamp,
                "validation_passed": self.input_validation_passed,
                "warnings": self.validation_warnings,
                "data_confidence": round(self.data_confidence * 100, 1),
            },
        }

    def get_summary(self) -> str:
        """Get a text summary of the results."""
        payback_str = (
            f"{self.payback_period_years:.1f} years"
            if self.payback_period_years != float("inf")
            else "Never"
        )
        return f"""
{self.option_name}:
  NPV: {self.format_currency(self.npv)}
  IRR: {self.irr * 100:.1f}%
  Payback: {payback_str}
  ROI: {self.roi * 100:.1f}%
  Total Investment: {self.format_currency(self.total_investment)}
  Data Confidence: {self.data_confidence * 100:.0f}%
"""


# ============================================================================
# FINANCIAL ENGINE - All calculations are deterministic Python math
# ============================================================================


class FinancialEngine:
    """
    Domain-Agnostic Financial Calculation Engine.

    This engine performs financial analysis for ANY investment decision.

    CRITICAL: ALL CALCULATIONS ARE DETERMINISTIC PYTHON MATH.
              NO LLM INVOLVEMENT IN NUMBER GENERATION.

    The engine does not generate numbers - it CALCULATES based on inputs.
    """

    def __init__(self) -> None:
        """Initialize the financial engine."""
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """Check that required libraries are available."""
        if npf is None:
            logger.warning(
                "numpy_financial not installed. Using fallback implementations."
            )

    # ========================================================================
    # MAIN CALCULATION METHOD
    # ========================================================================

    def calculate(self, model_input: FinancialModelInput) -> FinancialModelOutput:
        """
        Perform complete financial analysis on the input.

        ALL CALCULATIONS ARE DETERMINISTIC.

        Args:
            model_input: Structured financial inputs with cash flows

        Returns:
            FinancialModelOutput with all metrics calculated
        """
        logger.info(f"Calculating financial model for: {model_input.option_name}")

        # Validate inputs
        is_valid, validation_errors = model_input.validate()

        if not is_valid:
            logger.error(f"Validation failed: {validation_errors}")
            return self._create_error_output(model_input, validation_errors)

        # Sort cash flows by year
        cash_flows = sorted(model_input.cash_flows, key=lambda cf: cf.year)

        # Extract net cash flows for calculations
        net_cash_flows = [cf.net_cash_flow for cf in cash_flows]

        # ====================================================================
        # CORE CALCULATIONS (ALL DETERMINISTIC PYTHON MATH)
        # ====================================================================

        npv = self._calculate_npv(net_cash_flows, model_input.discount_rate)
        irr = self._calculate_irr(net_cash_flows)
        payback = self._calculate_payback(cash_flows)

        # Totals
        total_investment = sum(abs(cf.investment) for cf in cash_flows)
        total_revenue = sum(cf.revenue for cf in cash_flows)
        total_costs = sum(cf.operating_costs for cf in cash_flows)

        # ROI and Profitability Index
        net_profit = total_revenue - total_costs - total_investment
        roi = net_profit / total_investment if total_investment > 0 else 0.0
        profitability_index = (
            (npv + total_investment) / total_investment if total_investment > 0 else 0.0
        )

        # Data confidence (average of input confidences)
        data_confidence = (
            sum(cf.confidence for cf in cash_flows) / len(cash_flows)
            if cash_flows
            else 0.0
        )

        # Year-by-year breakdown
        yearly_breakdown, cumulative = self._build_yearly_breakdown(cash_flows)

        # ====================================================================
        # SENSITIVITY ANALYSIS (ALL DETERMINISTIC)
        # ====================================================================

        sensitivity = self._run_sensitivity_analysis(
            cash_flows, model_input.discount_rate, npv
        )

        logger.info(
            f"Calculation complete: NPV={npv:.2f}, IRR={irr*100:.1f}%, "
            f"Payback={payback:.1f}yrs"
        )

        return FinancialModelOutput(
            option_name=model_input.option_name,
            option_description=model_input.option_description,
            npv=npv,
            irr=irr,
            payback_period_years=payback,
            total_investment=total_investment,
            total_revenue=total_revenue,
            total_costs=total_costs,
            roi=roi,
            profitability_index=profitability_index,
            yearly_cash_flows=yearly_breakdown,
            cumulative_cash_flow=cumulative,
            sensitivity_scenarios=sensitivity,
            currency=model_input.currency,
            currency_unit=model_input.currency_unit,
            discount_rate=model_input.discount_rate,
            calculation_timestamp=datetime.now().isoformat(),
            input_validation_passed=True,
            validation_warnings=[],
            data_confidence=data_confidence,
        )

    # ========================================================================
    # CORE FINANCIAL CALCULATIONS
    # ========================================================================

    def _calculate_npv(self, cash_flows: List[float], discount_rate: float) -> float:
        """
        Calculate Net Present Value.

        Formula: NPV = Σ (CF_t / (1 + r)^t) for t = 0 to n

        This is DETERMINISTIC MATH.
        """
        if npf is not None:
            return float(npf.npv(discount_rate, cash_flows))
        else:
            # Fallback implementation
            npv_value = 0.0
            for t, cf in enumerate(cash_flows):
                npv_value += cf / ((1 + discount_rate) ** t)
            return npv_value

    def _calculate_irr(self, cash_flows: List[float]) -> float:
        """
        Calculate Internal Rate of Return.

        IRR is the discount rate that makes NPV = 0.
        Uses numerical solving via numpy_financial or Newton-Raphson fallback.

        This is DETERMINISTIC MATH.
        """
        if npf is not None:
            try:
                irr = npf.irr(cash_flows)
                if np.isnan(irr) or np.isinf(irr):
                    return 0.0
                return float(irr)
            except Exception as e:
                logger.warning(f"IRR calculation failed: {e}")
                return 0.0
        else:
            # Newton-Raphson fallback
            return self._irr_newton_raphson(cash_flows)

    def _irr_newton_raphson(
        self,
        cash_flows: List[float],
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> float:
        """
        Calculate IRR using Newton-Raphson method.

        Fallback when numpy_financial is not available.
        """
        # Initial guess
        rate = 0.1

        for _ in range(max_iterations):
            # Calculate NPV and its derivative at current rate
            npv_value = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))
            npv_derivative = sum(
                -t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows)
            )

            if abs(npv_derivative) < tolerance:
                break

            # Newton-Raphson update
            new_rate = rate - npv_value / npv_derivative

            if abs(new_rate - rate) < tolerance:
                return new_rate

            rate = new_rate

            # Keep rate in reasonable bounds
            rate = max(-0.99, min(rate, 10.0))

        return rate

    def _calculate_payback(self, cash_flows: List[CashFlowInput]) -> float:
        """
        Calculate payback period in years.

        Simple payback = first year where cumulative cash flow >= 0
        Uses linear interpolation for fractional years.

        This is DETERMINISTIC MATH.
        """
        cumulative = 0.0
        prev_cumulative = 0.0
        prev_year = 0

        sorted_flows = sorted(cash_flows, key=lambda x: x.year)

        for cf in sorted_flows:
            prev_cumulative = cumulative
            cumulative += cf.net_cash_flow

            if cumulative >= 0 and prev_cumulative < 0:
                # Linear interpolation for fractional year
                if cf.net_cash_flow != 0:
                    fraction = abs(prev_cumulative) / abs(cf.net_cash_flow)
                    return prev_year + fraction
                return float(cf.year)

            prev_year = cf.year

        # Check if we start positive
        if len(sorted_flows) > 0:
            first_cumulative = sorted_flows[0].net_cash_flow
            if first_cumulative >= 0:
                return float(sorted_flows[0].year)

        return float("inf")  # Never pays back

    # ========================================================================
    # SENSITIVITY ANALYSIS
    # ========================================================================

    def _run_sensitivity_analysis(
        self,
        base_cash_flows: List[CashFlowInput],
        discount_rate: float,
        base_npv: float,
    ) -> List[SensitivityScenario]:
        """
        Run standard sensitivity scenarios.

        These scenarios are domain-agnostic - they apply to any investment.
        ALL CALCULATIONS ARE DETERMINISTIC.
        """
        scenarios = []

        # Scenario 1: Revenue 20% lower
        scenarios.append(
            self._calculate_sensitivity_scenario(
                name="Revenue -20%",
                description="If revenue is 20% lower than projected",
                base_cash_flows=base_cash_flows,
                discount_rate=discount_rate,
                base_npv=base_npv,
                revenue_multiplier=0.80,
                cost_multiplier=1.0,
            )
        )

        # Scenario 2: Revenue 30% lower (stress test)
        scenarios.append(
            self._calculate_sensitivity_scenario(
                name="Revenue -30%",
                description="Stress test: Revenue 30% below projection",
                base_cash_flows=base_cash_flows,
                discount_rate=discount_rate,
                base_npv=base_npv,
                revenue_multiplier=0.70,
                cost_multiplier=1.0,
            )
        )

        # Scenario 3: Costs 30% higher
        scenarios.append(
            self._calculate_sensitivity_scenario(
                name="Costs +30%",
                description="If operating costs are 30% higher than projected",
                base_cash_flows=base_cash_flows,
                discount_rate=discount_rate,
                base_npv=base_npv,
                revenue_multiplier=1.0,
                cost_multiplier=1.30,
            )
        )

        # Scenario 4: Costs 50% higher (stress test)
        scenarios.append(
            self._calculate_sensitivity_scenario(
                name="Costs +50%",
                description="Stress test: Operating costs 50% above projection",
                base_cash_flows=base_cash_flows,
                discount_rate=discount_rate,
                base_npv=base_npv,
                revenue_multiplier=1.0,
                cost_multiplier=1.50,
            )
        )

        # Scenario 5: Best case (Revenue +20%, Costs -15%)
        scenarios.append(
            self._calculate_sensitivity_scenario(
                name="Best Case",
                description="Optimistic: Revenue +20%, Costs -15%",
                base_cash_flows=base_cash_flows,
                discount_rate=discount_rate,
                base_npv=base_npv,
                revenue_multiplier=1.20,
                cost_multiplier=0.85,
            )
        )

        # Scenario 6: Worst case (Revenue -35%, Costs +45%)
        scenarios.append(
            self._calculate_sensitivity_scenario(
                name="Worst Case",
                description="Pessimistic: Revenue -35%, Costs +45%",
                base_cash_flows=base_cash_flows,
                discount_rate=discount_rate,
                base_npv=base_npv,
                revenue_multiplier=0.65,
                cost_multiplier=1.45,
            )
        )

        return scenarios

    def _calculate_sensitivity_scenario(
        self,
        name: str,
        description: str,
        base_cash_flows: List[CashFlowInput],
        discount_rate: float,
        base_npv: float,
        revenue_multiplier: float,
        cost_multiplier: float,
    ) -> SensitivityScenario:
        """Calculate a single sensitivity scenario."""

        # Adjust cash flows
        adjusted_net_flows = []
        adjusted_cash_flows = []

        for cf in base_cash_flows:
            adjusted_revenue = cf.revenue * revenue_multiplier
            adjusted_costs = cf.operating_costs * cost_multiplier
            adjusted_net = adjusted_revenue - adjusted_costs - abs(cf.investment)
            adjusted_net_flows.append(adjusted_net)

            adjusted_cash_flows.append(
                CashFlowInput(
                    year=cf.year,
                    investment=cf.investment,
                    revenue=adjusted_revenue,
                    operating_costs=adjusted_costs,
                    source=cf.source,
                )
            )

        # Calculate metrics for this scenario
        npv = self._calculate_npv(adjusted_net_flows, discount_rate)
        irr = self._calculate_irr(adjusted_net_flows)
        payback = self._calculate_payback(adjusted_cash_flows)

        # Calculate change from base
        if base_npv != 0:
            npv_change_pct = ((npv - base_npv) / abs(base_npv)) * 100
        else:
            npv_change_pct = 0.0 if npv == 0 else float("inf")

        return SensitivityScenario(
            scenario_name=name,
            description=description,
            npv=npv,
            irr=irr,
            npv_change_pct=npv_change_pct,
            payback_years=payback,
            still_viable=npv > 0,
        )

    # ========================================================================
    # OPTION COMPARISON
    # ========================================================================

    def compare_options(
        self,
        option_a: FinancialModelOutput,
        option_b: FinancialModelOutput,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Compare two options using weighted scoring.

        Weights are explicit and configurable - NOT LLM-decided.
        ALL CALCULATIONS ARE DETERMINISTIC.

        Args:
            option_a: First option's financial results
            option_b: Second option's financial results
            weights: Optional custom weights

        Returns:
            Comparison results with winner and confidence
        """
        if weights is None:
            # Default weights - can be customized per domain
            weights = {
                "npv": 0.35,  # Financial return
                "irr": 0.20,  # Return rate
                "payback": 0.15,  # Time to recover
                "risk_resilience": 0.20,  # Sensitivity to shocks
                "data_confidence": 0.10,  # How reliable is our data?
            }

        # Score each metric
        scores: Dict[str, Tuple[float, float]] = {}

        # NPV (higher is better)
        scores["npv"] = self._score_metric(
            option_a.npv, option_b.npv, higher_is_better=True
        )

        # IRR (higher is better)
        scores["irr"] = self._score_metric(
            option_a.irr, option_b.irr, higher_is_better=True
        )

        # Payback (lower is better)
        payback_a = (
            option_a.payback_period_years
            if option_a.payback_period_years != float("inf")
            else 100
        )
        payback_b = (
            option_b.payback_period_years
            if option_b.payback_period_years != float("inf")
            else 100
        )
        scores["payback"] = self._score_metric(
            payback_a, payback_b, higher_is_better=False
        )

        # Risk resilience (calculated from sensitivity analysis)
        risk_a = self._calculate_risk_resilience(option_a)
        risk_b = self._calculate_risk_resilience(option_b)
        scores["risk_resilience"] = self._score_metric(
            risk_a, risk_b, higher_is_better=True
        )

        # Data confidence
        scores["data_confidence"] = self._score_metric(
            option_a.data_confidence, option_b.data_confidence, higher_is_better=True
        )

        # Calculate weighted totals
        total_a = sum(scores[metric][0] * weights.get(metric, 0) for metric in scores)
        total_b = sum(scores[metric][1] * weights.get(metric, 0) for metric in scores)

        # Normalize to 100
        total_a = total_a * 100
        total_b = total_b * 100

        # Determine winner
        winner = option_a.option_name if total_a > total_b else option_b.option_name
        loser = option_b.option_name if total_a > total_b else option_a.option_name
        margin = abs(total_a - total_b)
        confidence = min(95, 50 + margin)  # Cap at 95%

        # Build comparison table
        comparison_table = {}
        for metric in scores:
            comparison_table[metric] = {
                option_a.option_name: round(scores[metric][0] * 100, 1),
                option_b.option_name: round(scores[metric][1] * 100, 1),
                "weight": f"{weights.get(metric, 0) * 100:.0f}%",
            }

        return {
            "winner": winner,
            "loser": loser,
            "confidence": round(confidence, 1),
            "margin": round(margin, 1),
            "scores": {
                option_a.option_name: round(total_a, 1),
                option_b.option_name: round(total_b, 1),
            },
            "breakdown": comparison_table,
            "raw_metrics": {
                option_a.option_name: {
                    "npv": option_a.npv,
                    "irr": option_a.irr,
                    "payback": option_a.payback_period_years,
                    "risk_resilience": risk_a,
                    "data_confidence": option_a.data_confidence,
                },
                option_b.option_name: {
                    "npv": option_b.npv,
                    "irr": option_b.irr,
                    "payback": option_b.payback_period_years,
                    "risk_resilience": risk_b,
                    "data_confidence": option_b.data_confidence,
                },
            },
            "weights_used": weights,
            "recommendation": (
                f"Based on weighted financial analysis, {winner} is the stronger "
                f"option with {confidence:.0f}% confidence. The key differentiator "
                f"is the {self._find_key_differentiator(scores, weights)}."
            ),
        }

    def _score_metric(
        self, a_val: float, b_val: float, higher_is_better: bool = True
    ) -> Tuple[float, float]:
        """
        Score two values on 0-1 scale.

        Returns (a_score, b_score) where scores sum to 1.
        """
        if a_val == b_val:
            return 0.5, 0.5

        if higher_is_better:
            # Handle negative values
            if a_val < 0 and b_val < 0:
                # Both negative: less negative is better
                total = abs(a_val) + abs(b_val)
                return abs(b_val) / total, abs(a_val) / total
            elif a_val < 0:
                return 0.1, 0.9  # a is negative, b is better
            elif b_val < 0:
                return 0.9, 0.1  # b is negative, a is better
            else:
                total = a_val + b_val
                if total == 0:
                    return 0.5, 0.5
                return a_val / total, b_val / total
        else:
            # Lower is better (like payback)
            if a_val <= 0:
                return 0.9, 0.1
            if b_val <= 0:
                return 0.1, 0.9
            total = a_val + b_val
            return b_val / total, a_val / total

    def _calculate_risk_resilience(self, output: FinancialModelOutput) -> float:
        """
        Calculate risk resilience score (0-100).

        Based on how well NPV holds up in adverse scenarios.
        """
        if not output.sensitivity_scenarios or output.npv <= 0:
            return 0.0

        # Look at worst scenarios
        adverse_scenarios = [
            s
            for s in output.sensitivity_scenarios
            if s.scenario_name in ["Revenue -30%", "Costs +50%", "Worst Case"]
        ]

        if not adverse_scenarios:
            return 50.0  # No adverse scenarios to test

        # Score based on:
        # 1. How many adverse scenarios are still viable (NPV > 0)?
        # 2. How much does NPV drop on average?

        viable_count = sum(1 for s in adverse_scenarios if s.still_viable)
        viable_pct = viable_count / len(adverse_scenarios)

        avg_npv_drop = sum(abs(s.npv_change_pct) for s in adverse_scenarios) / len(
            adverse_scenarios
        )
        drop_score = max(0, 100 - avg_npv_drop) / 100  # Lower drop = higher score

        # Combined score
        resilience = (viable_pct * 0.6 + drop_score * 0.4) * 100
        return resilience

    def _find_key_differentiator(
        self, scores: Dict[str, Tuple[float, float]], weights: Dict[str, float]
    ) -> str:
        """Find the metric that most differentiates the two options."""
        max_diff = 0.0
        key_metric = "npv"

        for metric, (a, b) in scores.items():
            weighted_diff = abs(a - b) * weights.get(metric, 0)
            if weighted_diff > max_diff:
                max_diff = weighted_diff
                key_metric = metric

        return key_metric.replace("_", " ")

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _build_yearly_breakdown(
        self, cash_flows: List[CashFlowInput]
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Build year-by-year breakdown table."""
        yearly_breakdown = []
        cumulative: List[float] = []
        running_total = 0.0

        for cf in sorted(cash_flows, key=lambda x: x.year):
            running_total += cf.net_cash_flow
            yearly_breakdown.append(
                {
                    "year": cf.year,
                    "investment": round(cf.investment, 2),
                    "revenue": round(cf.revenue, 2),
                    "operating_costs": round(cf.operating_costs, 2),
                    "net_cash_flow": round(cf.net_cash_flow, 2),
                    "cumulative": round(running_total, 2),
                    "source": cf.source,
                    "confidence": cf.confidence,
                }
            )
            cumulative.append(running_total)

        return yearly_breakdown, cumulative

    def _create_error_output(
        self, model_input: FinancialModelInput, errors: List[str]
    ) -> FinancialModelOutput:
        """Create an output object for failed validation."""
        return FinancialModelOutput(
            option_name=model_input.option_name,
            option_description=model_input.option_description,
            npv=0.0,
            irr=0.0,
            payback_period_years=float("inf"),
            total_investment=0.0,
            total_revenue=0.0,
            total_costs=0.0,
            roi=0.0,
            profitability_index=0.0,
            yearly_cash_flows=[],
            cumulative_cash_flow=[],
            sensitivity_scenarios=[],
            currency=model_input.currency,
            currency_unit=model_input.currency_unit,
            discount_rate=model_input.discount_rate,
            calculation_timestamp=datetime.now().isoformat(),
            input_validation_passed=False,
            validation_warnings=errors,
            data_confidence=0.0,
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def calculate_simple_npv(cash_flows: List[float], discount_rate: float) -> float:
    """
    Simple NPV calculation for quick checks.

    Args:
        cash_flows: List of cash flows [CF0, CF1, CF2, ...]
        discount_rate: Discount rate as decimal (e.g., 0.08 for 8%)

    Returns:
        Net Present Value
    """
    engine = FinancialEngine()
    return engine._calculate_npv(cash_flows, discount_rate)


def calculate_simple_irr(cash_flows: List[float]) -> float:
    """
    Simple IRR calculation for quick checks.

    Args:
        cash_flows: List of cash flows [CF0, CF1, CF2, ...]

    Returns:
        Internal Rate of Return as decimal
    """
    engine = FinancialEngine()
    return engine._calculate_irr(cash_flows)

