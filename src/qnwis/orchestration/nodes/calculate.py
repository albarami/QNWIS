"""
Calculation Node.

Runs deterministic financial calculations on structured inputs.
NO LLM INVOLVEMENT - Pure Python math.

This node:
1. Takes structured inputs from structure_data_node
2. Runs FinancialEngine.calculate() for each option
3. Runs FinancialEngine.compare_options() when two options exist
4. Stores results in state["calculated_results"]
5. Adds warnings for low data confidence
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..state import IntelligenceState

logger = logging.getLogger(__name__)

# Data confidence thresholds
CONFIDENCE_THRESHOLD_LOW = 0.3
CONFIDENCE_THRESHOLD_MEDIUM = 0.5


async def calculate_node(state: IntelligenceState) -> IntelligenceState:
    """
    Run deterministic calculations on structured inputs.

    ALL CALCULATIONS ARE PYTHON MATH - NO LLM.

    This node:
    - Consumes structured inputs from structure_data_node
    - Runs FinancialEngine.calculate() for each option
    - Runs comparison if two options exist
    - Adds confidence warnings based on data quality

    Args:
        state: Current intelligence state with structured_inputs

    Returns:
        Updated state with calculated_results
    """
    from src.qnwis.engines.financial_engine import (
        CashFlowInput,
        FinancialEngine,
        FinancialModelInput,
    )
    from .structure_data import convert_structured_to_model_input

    logger.info("🔢 Running deterministic calculations...")

    structured_inputs = state.get("structured_inputs")
    if not structured_inputs:
        logger.warning("No structured inputs available for calculation")
        state["calculated_results"] = None
        state["calculation_warning"] = "No structured data available for calculation"
        state.setdefault("nodes_executed", []).append("calculate")
        return state

    engine = FinancialEngine()
    calculated_options: List[Any] = []

    # Get options from structured inputs
    options = structured_inputs.get("options", [])

    if not options:
        logger.warning("No options found in structured inputs")
        state["calculated_results"] = None
        state["calculation_warning"] = "No options to analyze"
        state.setdefault("nodes_executed", []).append("calculate")
        return state

    # Calculate for each option
    for i, option in enumerate(options):
        try:
            # Convert structured data to FinancialModelInput
            model_input_dict = convert_structured_to_model_input(structured_inputs, i)

            if not model_input_dict:
                logger.warning(f"Could not convert option {i} to model input")
                continue

            # Build CashFlowInput objects
            cash_flows = []
            for cf_dict in model_input_dict["cash_flows"]:
                cash_flows.append(
                    CashFlowInput(
                        year=cf_dict["year"],
                        investment=cf_dict.get("investment", 0),
                        revenue=cf_dict.get("revenue", 0),
                        operating_costs=cf_dict.get("operating_costs", 0),
                        source=cf_dict.get("source", ""),
                        assumptions=cf_dict.get("assumptions", ""),
                        confidence=cf_dict.get("confidence", 0.5),
                    )
                )

            # Create model input
            model_input = FinancialModelInput(
                option_name=model_input_dict["option_name"],
                option_description=model_input_dict.get("option_description", ""),
                cash_flows=cash_flows,
                discount_rate=model_input_dict["discount_rate"],
                discount_rate_source=model_input_dict.get(
                    "discount_rate_source", "Default"
                ),
                currency=model_input_dict.get("currency", "USD"),
                time_horizon_years=model_input_dict.get("time_horizon_years", 10),
            )

            # Run calculation
            output = engine.calculate(model_input)
            calculated_options.append(output)

            logger.info(
                f"  ✓ {option.get('name', f'Option {i+1}')}: "
                f"NPV={output.npv:,.0f}, IRR={output.irr*100:.1f}%, "
                f"Confidence={output.data_confidence*100:.0f}%"
            )

        except Exception as e:
            logger.error(
                f"  ✗ Failed to calculate {option.get('name', f'Option {i+1}')}: {e}"
            )

    # Compare options if we have two
    comparison = None
    if len(calculated_options) == 2:
        try:
            comparison = engine.compare_options(
                calculated_options[0], calculated_options[1]
            )
            logger.info(
                f"  → Winner: {comparison['winner']} "
                f"({comparison['confidence']:.0f}% confidence)"
            )
        except Exception as e:
            logger.error(f"  ✗ Failed to compare options: {e}")

    # Calculate overall data confidence
    if calculated_options:
        avg_confidence = sum(opt.data_confidence for opt in calculated_options) / len(
            calculated_options
        )
    else:
        avg_confidence = 0.0

    # ========================================================================
    # DATA CONFIDENCE THRESHOLD - Add warnings for low confidence data
    # ========================================================================
    calculation_warning: Optional[str] = None

    if avg_confidence < CONFIDENCE_THRESHOLD_LOW:
        logger.warning(
            f"⚠️ Data confidence too low for reliable calculations: {avg_confidence:.0%}"
        )
        calculation_warning = (
            "Results based on limited data – interpret with caution. "
            f"Data confidence: {avg_confidence:.0%}"
        )
    elif avg_confidence < CONFIDENCE_THRESHOLD_MEDIUM:
        logger.info(
            f"⚠️ Moderate data confidence: {avg_confidence:.0%} – some projections estimated"
        )
        calculation_warning = (
            "Moderate data confidence – some projections are estimated. "
            f"Data confidence: {avg_confidence:.0%}"
        )

    # Store results
    state["calculated_results"] = {
        "options": [opt.to_dict() for opt in calculated_options],
        "comparison": comparison,
        "data_confidence": avg_confidence,
        "calculation_method": "deterministic",
        "engine_version": "1.0",
    }

    if calculation_warning:
        state["calculation_warning"] = calculation_warning

    logger.info(
        f"✅ Calculations complete. {len(calculated_options)} options analyzed. "
        f"Data confidence: {avg_confidence:.0%}"
    )

    state.setdefault("nodes_executed", []).append("calculate")
    return state


def get_calculated_summary(state: IntelligenceState) -> str:
    """
    Get a formatted summary of calculated results for agent prompts.

    This helper formats the calculated results in a way that can be
    injected into LLM prompts for interpretation.

    Args:
        state: Intelligence state with calculated_results

    Returns:
        Formatted string summary of calculations
    """
    calculated = state.get("calculated_results")
    if not calculated:
        return "No calculations available."

    lines = []
    lines.append("=" * 60)
    lines.append("CALCULATED FINANCIAL RESULTS (DETERMINISTIC)")
    lines.append("=" * 60)
    lines.append("")

    # Add warning if present
    warning = state.get("calculation_warning")
    if warning:
        lines.append(f"⚠️ WARNING: {warning}")
        lines.append("")

    # Options summary
    for option in calculated.get("options", []):
        metrics = option.get("metrics", {})
        lines.append(f"### {option['option_name']}")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| NPV | {metrics.get('npv_formatted', 'N/A')} |")
        lines.append(f"| IRR | {metrics.get('irr_formatted', 'N/A')} |")
        lines.append(f"| Payback | {metrics.get('payback_years', 'N/A')} years |")
        lines.append(f"| ROI | {metrics.get('roi_formatted', 'N/A')} |")
        lines.append(
            f"| Data Confidence | {option.get('metadata', {}).get('data_confidence', 'N/A')}% |"
        )
        lines.append("")

        # Sensitivity analysis
        sensitivity = option.get("sensitivity", [])
        if sensitivity:
            lines.append("**Sensitivity Analysis:**")
            lines.append("")
            lines.append("| Scenario | NPV Change | Still Viable? |")
            lines.append("|----------|------------|---------------|")
            for scenario in sensitivity[:4]:  # Show top 4
                viable = "✓ Yes" if scenario.get("still_viable") else "✗ No"
                lines.append(
                    f"| {scenario['scenario']} | {scenario['npv_change_pct']}% | {viable} |"
                )
            lines.append("")

    # Comparison result
    comparison = calculated.get("comparison")
    if comparison:
        lines.append("### COMPARISON RESULT")
        lines.append("")
        lines.append(f"**Winner:** {comparison['winner']}")
        lines.append(f"**Confidence:** {comparison['confidence']:.0f}%")
        lines.append(f"**Margin:** {comparison['margin']:.1f} points")
        lines.append("")
        lines.append("**Score Breakdown:**")
        for metric, scores in comparison.get("breakdown", {}).items():
            lines.append(f"- {metric}: {scores}")
        lines.append("")
        lines.append(f"**Recommendation:** {comparison.get('recommendation', 'N/A')}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("INTERPRET THESE RESULTS - DO NOT GENERATE NEW NUMBERS")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_comparison_table(calculated_results: Dict[str, Any]) -> str:
    """
    Format a comparison table for ministerial briefing.

    Args:
        calculated_results: Results from calculate_node

    Returns:
        Markdown table comparing options
    """
    options = calculated_results.get("options", [])
    if len(options) < 2:
        return "Insufficient options for comparison."

    opt_a = options[0]
    opt_b = options[1]

    metrics_a = opt_a.get("metrics", {})
    metrics_b = opt_b.get("metrics", {})

    table = []
    table.append(f"| Metric | {opt_a['option_name']} | {opt_b['option_name']} | Difference |")
    table.append("|--------|----------------------|----------------------|------------|")

    # NPV
    npv_a = metrics_a.get("npv", 0)
    npv_b = metrics_b.get("npv", 0)
    npv_diff = npv_a - npv_b
    table.append(
        f"| NPV | {metrics_a.get('npv_formatted', 'N/A')} | "
        f"{metrics_b.get('npv_formatted', 'N/A')} | "
        f"{'+' if npv_diff > 0 else ''}{npv_diff:,.0f} |"
    )

    # IRR
    irr_a = metrics_a.get("irr_pct", 0)
    irr_b = metrics_b.get("irr_pct", 0)
    irr_diff = irr_a - irr_b
    table.append(
        f"| IRR | {metrics_a.get('irr_formatted', 'N/A')} | "
        f"{metrics_b.get('irr_formatted', 'N/A')} | "
        f"{'+' if irr_diff > 0 else ''}{irr_diff:.1f}% |"
    )

    # Payback
    payback_a = metrics_a.get("payback_years", "N/A")
    payback_b = metrics_b.get("payback_years", "N/A")
    if isinstance(payback_a, (int, float)) and isinstance(payback_b, (int, float)):
        payback_diff = payback_a - payback_b
        payback_diff_str = f"{'+' if payback_diff > 0 else ''}{payback_diff:.1f} years"
    else:
        payback_diff_str = "N/A"
    table.append(
        f"| Payback | {payback_a} years | {payback_b} years | {payback_diff_str} |"
    )

    # ROI
    roi_a = metrics_a.get("roi_pct", 0)
    roi_b = metrics_b.get("roi_pct", 0)
    roi_diff = roi_a - roi_b
    table.append(
        f"| ROI | {metrics_a.get('roi_formatted', 'N/A')} | "
        f"{metrics_b.get('roi_formatted', 'N/A')} | "
        f"{'+' if roi_diff > 0 else ''}{roi_diff:.1f}% |"
    )

    return "\n".join(table)


def format_sensitivity_matrix(calculated_results: Dict[str, Any]) -> str:
    """
    Format a sensitivity analysis matrix for ministerial briefing.

    Args:
        calculated_results: Results from calculate_node

    Returns:
        Markdown table showing sensitivity scenarios
    """
    options = calculated_results.get("options", [])
    if not options:
        return "No sensitivity analysis available."

    # Get scenarios from first option (they're the same for all)
    scenarios = options[0].get("sensitivity", [])
    if not scenarios:
        return "No sensitivity analysis available."

    # Build header
    header = ["| Scenario |"]
    divider = ["|----------|"]
    for opt in options:
        header.append(f" {opt['option_name']} NPV |")
        divider.append("------------|")

    if len(options) >= 2:
        header.append(" Winner |")
        divider.append("--------|")

    table = ["".join(header), "".join(divider)]

    # Add scenario rows
    for i, scenario in enumerate(scenarios):
        row = [f"| {scenario['scenario']} |"]

        npvs = []
        for opt in options:
            opt_scenario = opt.get("sensitivity", [])[i] if i < len(opt.get("sensitivity", [])) else {}
            npv = opt_scenario.get("npv", 0)
            npvs.append(npv)
            row.append(f" {npv:,.0f} |")

        if len(npvs) >= 2:
            winner = options[0]["option_name"] if npvs[0] > npvs[1] else options[1]["option_name"]
            row.append(f" {winner} |")

        table.append("".join(row))

    return "\n".join(table)

