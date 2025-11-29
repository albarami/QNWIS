"""
McKinsey-Grade Ministerial Briefing Template.

Produces structured, evidence-based executive briefings with:
- Executive summary comparing options
- 10-year cash flow tables
- Sensitivity analysis matrices
- Risk assessments
- Data quality warnings
- Implementation recommendations

ALL NUMBERS come from CALCULATED RESULTS - no LLM-generated figures.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MinisterialBriefingTemplate:
    """
    Template for generating McKinsey-grade ministerial briefings.

    All numbers are pulled from calculated_results - LLMs only provide
    interpretation and strategic framing.
    """

    def __init__(
        self,
        query: str,
        calculated_results: Dict[str, Any],
        debate_insights: Optional[str] = None,
        calculation_warning: Optional[str] = None,
        data_sources: Optional[List[str]] = None,
    ):
        """
        Initialize the briefing template.

        Args:
            query: Original question being analyzed
            calculated_results: Results from calculate_node (REQUIRED)
            debate_insights: Summary of multi-agent debate (optional)
            calculation_warning: Data confidence warning (optional)
            data_sources: List of data sources used (optional)
        """
        self.query = query
        self.calculated_results = calculated_results
        self.debate_insights = debate_insights
        self.calculation_warning = calculation_warning
        self.data_sources = data_sources or []
        self.generated_at = datetime.now().isoformat()

    def render(self) -> str:
        """
        Render the complete ministerial briefing.

        Returns:
            Formatted markdown briefing
        """
        sections = []

        # Header
        sections.append(self._render_header())

        # Warning banner (if present)
        if self.calculation_warning:
            sections.append(self._render_warning_banner())

        # Executive Summary
        sections.append(self._render_executive_summary())

        # Financial Comparison Table
        sections.append(self._render_financial_comparison())

        # Cash Flow Tables
        sections.append(self._render_cash_flow_tables())

        # Sensitivity Analysis Matrix
        sections.append(self._render_sensitivity_matrix())

        # Risk Assessment
        sections.append(self._render_risk_assessment())

        # Debate Insights (if available)
        if self.debate_insights:
            sections.append(self._render_debate_insights())

        # Implementation Roadmap
        sections.append(self._render_implementation_roadmap())

        # Data Sources & Assumptions
        sections.append(self._render_appendix())

        return "\n\n".join(sections)

    def _render_header(self) -> str:
        """Render the briefing header."""
        return f"""# MINISTERIAL BRIEFING
## Strategic Investment Analysis

**Query:** {self.query}

**Generated:** {self.generated_at}

**Classification:** INTERNAL - MINISTERIAL

---"""

    def _render_warning_banner(self) -> str:
        """Render data quality warning if present."""
        return f"""## ⚠️ DATA CONFIDENCE ADVISORY

{self.calculation_warning}

*Recommendations below should be validated with additional data before implementation.*

---"""

    def _render_executive_summary(self) -> str:
        """Render the executive summary section."""
        options = self.calculated_results.get("options", [])
        comparison = self.calculated_results.get("comparison")

        if not options:
            return "## EXECUTIVE SUMMARY\n\n*No options available for analysis.*"

        lines = ["## EXECUTIVE SUMMARY"]
        lines.append("")

        # Winner announcement (if comparison exists)
        if comparison:
            winner = comparison.get("winner", "N/A")
            confidence = comparison.get("confidence", 0)
            margin = comparison.get("margin", 0)
            lines.append(f"### RECOMMENDATION: {winner}")
            lines.append("")
            lines.append(f"**Decision Confidence:** {confidence:.0f}%")
            lines.append(f"**Margin of Victory:** {margin:.1f} points")
            lines.append("")
            lines.append(f"**Rationale:** {comparison.get('recommendation', 'See detailed analysis below.')}")
            lines.append("")

        # Key metrics for each option
        lines.append("### KEY METRICS AT A GLANCE")
        lines.append("")

        for option in options:
            metrics = option.get("metrics", {})
            name = option.get("option_name", "Option")
            lines.append(f"**{name}:**")
            lines.append(f"- NPV: {metrics.get('npv_formatted', 'N/A')}")
            lines.append(f"- IRR: {metrics.get('irr_formatted', 'N/A')}")
            lines.append(f"- Payback: {metrics.get('payback_years', 'N/A')} years")
            lines.append(f"- Total Investment: {metrics.get('total_investment_formatted', 'N/A')}")
            lines.append("")

        return "\n".join(lines)

    def _render_financial_comparison(self) -> str:
        """Render side-by-side financial comparison table."""
        options = self.calculated_results.get("options", [])

        if len(options) < 2:
            return "## FINANCIAL COMPARISON\n\n*Single option analysis - no comparison available.*"

        opt_a = options[0]
        opt_b = options[1]
        metrics_a = opt_a.get("metrics", {})
        metrics_b = opt_b.get("metrics", {})

        lines = ["## FINANCIAL COMPARISON"]
        lines.append("")
        lines.append(f"| Metric | {opt_a.get('option_name')} | {opt_b.get('option_name')} | Winner |")
        lines.append("|--------|----------------------|----------------------|--------|")

        # NPV
        npv_a = metrics_a.get("npv", 0)
        npv_b = metrics_b.get("npv", 0)
        npv_winner = opt_a.get("option_name") if npv_a > npv_b else opt_b.get("option_name")
        lines.append(
            f"| **Net Present Value** | {metrics_a.get('npv_formatted', 'N/A')} | "
            f"{metrics_b.get('npv_formatted', 'N/A')} | {npv_winner} |"
        )

        # IRR
        irr_a = metrics_a.get("irr_pct", 0)
        irr_b = metrics_b.get("irr_pct", 0)
        irr_winner = opt_a.get("option_name") if irr_a > irr_b else opt_b.get("option_name")
        lines.append(
            f"| **Internal Rate of Return** | {metrics_a.get('irr_formatted', 'N/A')} | "
            f"{metrics_b.get('irr_formatted', 'N/A')} | {irr_winner} |"
        )

        # Payback
        payback_a = metrics_a.get("payback_years", float("inf"))
        payback_b = metrics_b.get("payback_years", float("inf"))
        if isinstance(payback_a, str):
            payback_a = float("inf")
        if isinstance(payback_b, str):
            payback_b = float("inf")
        payback_winner = (
            opt_a.get("option_name") if payback_a < payback_b else opt_b.get("option_name")
        )
        lines.append(
            f"| **Payback Period** | {metrics_a.get('payback_years', 'N/A')} yrs | "
            f"{metrics_b.get('payback_years', 'N/A')} yrs | {payback_winner} |"
        )

        # ROI
        roi_a = metrics_a.get("roi_pct", 0)
        roi_b = metrics_b.get("roi_pct", 0)
        roi_winner = opt_a.get("option_name") if roi_a > roi_b else opt_b.get("option_name")
        lines.append(
            f"| **Return on Investment** | {metrics_a.get('roi_formatted', 'N/A')} | "
            f"{metrics_b.get('roi_formatted', 'N/A')} | {roi_winner} |"
        )

        # Total Investment
        inv_a = metrics_a.get("total_investment", 0)
        inv_b = metrics_b.get("total_investment", 0)
        inv_better = opt_a.get("option_name") if inv_a < inv_b else opt_b.get("option_name")
        lines.append(
            f"| **Total Investment** | {metrics_a.get('total_investment_formatted', 'N/A')} | "
            f"{metrics_b.get('total_investment_formatted', 'N/A')} | {inv_better} (lower) |"
        )

        # Data Confidence
        conf_a = opt_a.get("metadata", {}).get("data_confidence", 0)
        conf_b = opt_b.get("metadata", {}).get("data_confidence", 0)
        conf_better = opt_a.get("option_name") if conf_a > conf_b else opt_b.get("option_name")
        lines.append(
            f"| **Data Confidence** | {conf_a:.0f}% | {conf_b:.0f}% | {conf_better} |"
        )

        return "\n".join(lines)

    def _render_cash_flow_tables(self) -> str:
        """Render 10-year cash flow tables for each option."""
        options = self.calculated_results.get("options", [])

        if not options:
            return "## CASH FLOW PROJECTIONS\n\n*No cash flow data available.*"

        lines = ["## CASH FLOW PROJECTIONS"]
        lines.append("")

        for option in options:
            name = option.get("option_name", "Option")
            yearly = option.get("yearly_breakdown", [])

            if not yearly:
                lines.append(f"### {name}")
                lines.append("*No yearly breakdown available.*")
                lines.append("")
                continue

            lines.append(f"### {name}")
            lines.append("")
            lines.append(
                "| Year | Investment | Revenue | Op. Costs | Net Cash Flow | Cumulative |"
            )
            lines.append(
                "|------|------------|---------|-----------|---------------|------------|"
            )

            for year_data in yearly[:11]:  # Cap at 10 years + year 0
                year = year_data.get("year", "")
                investment = year_data.get("investment", 0)
                revenue = year_data.get("revenue", 0)
                costs = year_data.get("operating_costs", 0)
                net = year_data.get("net_cash_flow", 0)
                cumulative = year_data.get("cumulative", 0)

                lines.append(
                    f"| {year} | {investment:,.0f} | {revenue:,.0f} | {costs:,.0f} | "
                    f"{net:,.0f} | {cumulative:,.0f} |"
                )

            lines.append("")

        return "\n".join(lines)

    def _render_sensitivity_matrix(self) -> str:
        """Render sensitivity analysis matrix."""
        options = self.calculated_results.get("options", [])

        if not options:
            return "## SENSITIVITY ANALYSIS\n\n*No sensitivity data available.*"

        # Get scenarios from first option (they're the same for all)
        scenarios = options[0].get("sensitivity", [])
        if not scenarios:
            return "## SENSITIVITY ANALYSIS\n\n*No sensitivity scenarios calculated.*"

        lines = ["## SENSITIVITY ANALYSIS"]
        lines.append("")
        lines.append("*How does NPV change under different scenarios?*")
        lines.append("")

        # Build header
        header = ["| Scenario |"]
        divider = ["|----------|"]
        for opt in options:
            header.append(f" {opt.get('option_name')} |")
            divider.append("------------|")

        if len(options) >= 2:
            header.append(" Winner |")
            divider.append("--------|")

        lines.append("".join(header))
        lines.append("".join(divider))

        # Add scenario rows
        for i, scenario in enumerate(scenarios):
            row = [f"| **{scenario.get('scenario', 'Scenario')}** |"]

            npvs = []
            viables = []
            for opt in options:
                opt_scenarios = opt.get("sensitivity", [])
                if i < len(opt_scenarios):
                    s = opt_scenarios[i]
                    npv = s.get("npv", 0)
                    npvs.append(npv)
                    change = s.get("npv_change_pct", 0)
                    viable = "✓" if s.get("still_viable") else "✗"
                    viables.append(s.get("still_viable", False))
                    row.append(f" {npv:,.0f} ({change:+.0f}%) {viable} |")
                else:
                    npvs.append(0)
                    viables.append(False)
                    row.append(" N/A |")

            if len(npvs) >= 2:
                # Determine winner for this scenario
                if viables[0] and not viables[1]:
                    winner = options[0].get("option_name")
                elif viables[1] and not viables[0]:
                    winner = options[1].get("option_name")
                elif npvs[0] > npvs[1]:
                    winner = options[0].get("option_name")
                else:
                    winner = options[1].get("option_name")
                row.append(f" {winner} |")

            lines.append("".join(row))

        lines.append("")
        lines.append("*✓ = NPV still positive (viable), ✗ = NPV negative (not viable)*")

        return "\n".join(lines)

    def _render_risk_assessment(self) -> str:
        """Render risk assessment based on sensitivity analysis."""
        options = self.calculated_results.get("options", [])
        comparison = self.calculated_results.get("comparison") or {}

        lines = ["## RISK ASSESSMENT"]
        lines.append("")

        # Risk resilience from comparison
        raw_metrics = comparison.get("raw_metrics", {})
        if raw_metrics:
            lines.append("### Risk Resilience Scores")
            lines.append("")
            for opt_name, metrics in raw_metrics.items():
                resilience = metrics.get("risk_resilience", 0)
                lines.append(f"- **{opt_name}:** {resilience:.0f}/100")
            lines.append("")

        # Identify which scenarios break each option
        lines.append("### Scenario Vulnerability Analysis")
        lines.append("")

        for option in options:
            name = option.get("option_name", "Option")
            scenarios = option.get("sensitivity", [])
            breaking_scenarios = [
                s.get("scenario")
                for s in scenarios
                if not s.get("still_viable", True)
            ]

            if breaking_scenarios:
                lines.append(f"**{name}** becomes non-viable under:")
                for scenario in breaking_scenarios:
                    lines.append(f"- {scenario}")
            else:
                lines.append(f"**{name}** remains viable under all tested scenarios ✓")
            lines.append("")

        return "\n".join(lines)

    def _render_debate_insights(self) -> str:
        """Render insights from multi-agent debate."""
        return f"""## STRATEGIC DEBATE INSIGHTS

*Summary from multi-agent deliberation:*

{self.debate_insights}"""

    def _render_implementation_roadmap(self) -> str:
        """Render implementation recommendations."""
        comparison = self.calculated_results.get("comparison") or {}
        winner = comparison.get("winner", "N/A")

        return f"""## IMPLEMENTATION ROADMAP

### Recommended Path: {winner}

**Phase 1: Due Diligence (Months 1-3)**
- Validate all input assumptions with primary sources
- Commission independent financial audit
- Conduct stakeholder consultations

**Phase 2: Detailed Planning (Months 4-6)**
- Develop detailed project plan
- Establish governance structure
- Define success metrics and KPIs

**Phase 3: Pilot Implementation (Months 7-12)**
- Begin with controlled pilot
- Monitor against projections
- Adjust based on early results

**Phase 4: Full Rollout (Year 2+)**
- Scale based on pilot success
- Regular reviews against sensitivity scenarios
- Quarterly reporting to stakeholders"""

    def _render_appendix(self) -> str:
        """Render data sources and assumptions appendix."""
        lines = ["## APPENDIX: DATA SOURCES & ASSUMPTIONS"]
        lines.append("")
        lines.append("### Data Sources")
        lines.append("")

        if self.data_sources:
            for source in self.data_sources:
                lines.append(f"- {source}")
        else:
            lines.append("- See individual cash flow citations")
        lines.append("")

        # Extract assumptions from options
        lines.append("### Key Assumptions")
        lines.append("")

        options = self.calculated_results.get("options", [])
        for option in options:
            name = option.get("option_name", "Option")
            metadata = option.get("metadata", {})
            discount_rate = metadata.get("discount_rate_pct", "N/A")
            lines.append(f"**{name}:**")
            lines.append(f"- Discount Rate: {discount_rate}")
            lines.append(f"- Data Confidence: {metadata.get('data_confidence', 'N/A')}%")
            lines.append("")

        lines.append("### Methodology")
        lines.append("")
        lines.append(
            "All financial calculations performed using deterministic Python engines. "
            "No LLM-generated numbers. NPV calculated using standard discounted cash flow. "
            "IRR calculated using Newton-Raphson method. Sensitivity analysis covers 6 "
            "standard scenarios: Revenue ±20-30%, Costs +30-50%, Best/Worst case."
        )

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Report generated: {self.generated_at}*")
        lines.append("*Classification: INTERNAL - MINISTERIAL*")

        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def render_executive_summary(calculated_results: Dict[str, Any]) -> str:
    """
    Render just the executive summary section.

    Args:
        calculated_results: Results from calculate_node

    Returns:
        Formatted executive summary
    """
    template = MinisterialBriefingTemplate(
        query="",
        calculated_results=calculated_results,
    )
    return template._render_executive_summary()


def render_financial_comparison(calculated_results: Dict[str, Any]) -> str:
    """
    Render just the financial comparison table.

    Args:
        calculated_results: Results from calculate_node

    Returns:
        Formatted comparison table
    """
    template = MinisterialBriefingTemplate(
        query="",
        calculated_results=calculated_results,
    )
    return template._render_financial_comparison()


def render_sensitivity_matrix(calculated_results: Dict[str, Any]) -> str:
    """
    Render just the sensitivity analysis matrix.

    Args:
        calculated_results: Results from calculate_node

    Returns:
        Formatted sensitivity matrix
    """
    template = MinisterialBriefingTemplate(
        query="",
        calculated_results=calculated_results,
    )
    return template._render_sensitivity_matrix()


def render_risk_assessment(calculated_results: Dict[str, Any]) -> str:
    """
    Render just the risk assessment section.

    Args:
        calculated_results: Results from calculate_node

    Returns:
        Formatted risk assessment
    """
    template = MinisterialBriefingTemplate(
        query="",
        calculated_results=calculated_results,
    )
    return template._render_risk_assessment()

