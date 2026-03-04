"""
Supplementary service runners for the Legendary Synthesis pipeline.

Encapsulates calls to optional external services: case studies, financial
modeling, stakeholder analysis, risk register, and implementation planning.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from ...case_studies import extract_case_studies, format_case_studies_for_synthesis

logger = logging.getLogger(__name__)

# Optional service imports (fail gracefully)
try:
    from src.nsic.engine_b.services.financial_modeling import (
        FinancialModelingService,
        format_comparison_matrix_for_brief,
        generate_year_by_year_projection,
    )
    FINANCIAL_MODELING_AVAILABLE = True
except ImportError:
    FINANCIAL_MODELING_AVAILABLE = False

try:
    from ...implementation_planner import (
        ImplementationPlanner,
        format_implementation_plan_for_brief,
    )
    IMPLEMENTATION_PLANNER_AVAILABLE = True
except ImportError:
    IMPLEMENTATION_PLANNER_AVAILABLE = False

try:
    from ...stakeholder_analyzer import (
        StakeholderAnalyzer,
        format_stakeholder_analysis_for_brief,
    )
    STAKEHOLDER_ANALYZER_AVAILABLE = True
except ImportError:
    STAKEHOLDER_ANALYZER_AVAILABLE = False

try:
    from ...risk_register import (
        RiskRegisterGenerator,
        format_risk_register_for_brief,
    )
    RISK_REGISTER_AVAILABLE = True
except ImportError:
    RISK_REGISTER_AVAILABLE = False


async def fetch_case_studies(state: Dict[str, Any], query: str) -> str:
    """Fetch case studies from cache or external sources."""
    logger.info("=" * 60)
    logger.info("📚 CASE STUDY EXTRACTION...")
    logger.info("=" * 60)

    cached = state.get("case_studies_cache")
    if cached:
        logger.info(f"  ✅ Using {len(cached)} CACHED case studies from debate phase")
        return format_case_studies_for_synthesis(cached)

    try:
        studies = await extract_case_studies(query, max_cases=4)
        logger.info(f"  📊 Case studies returned: {len(studies) if studies else 0}")
        if studies:
            text = format_case_studies_for_synthesis(studies)
            logger.info(f"  ✅ Fetched {len(studies)} case studies from real sources")
            for i, cs in enumerate(studies[:3]):
                logger.info(f"    Case {i+1}: {cs.get('title', 'Untitled')[:50]}... ({cs.get('source_type', 'unknown')})")
            return text
        logger.warning("  ⚠️ No case studies found for this query")
        return "No directly relevant case studies found. The synthesis should note limited international benchmarking data."
    except Exception as e:
        logger.error(f"  ❌ Case study extraction FAILED: {e}", exc_info=True)
        return f"Case study extraction failed: {e}. Proceed with analysis based on available data."


def run_financial_modeling(
    query: str,
    scenario_summaries: List[Dict[str, Any]],
    facts: List[Dict[str, Any]],
) -> str:
    """Run financial modeling (NPV/IRR analysis) if available."""
    logger.info("💰 Running financial modeling (NPV/IRR analysis)...")
    if not FINANCIAL_MODELING_AVAILABLE:
        return "Financial modeling service not available. Use qualitative debate analysis for option comparison."
    try:
        service = FinancialModelingService(discount_rate=0.08)

        options = [
            {"name": s.get("name", "Option"), "type": s.get("type", "base")}
            for s in scenario_summaries[:4]
        ]
        if not options:
            options = [
                {"name": "Option A", "type": "base"},
                {"name": "Option B", "type": "alternative"},
            ]

        inv_match = re.search(r'\$?([\d.]+)\s*(billion|B)', query, re.IGNORECASE)
        total_inv = float(inv_match.group(1)) * 1e9 if inv_match else 50e9

        facts_dict: Dict[str, Any] = {}
        for f in facts:
            if isinstance(f, dict):
                key = f.get("metric", f.get("indicator", ""))
                value = f.get("value", "")
                if key:
                    facts_dict[key] = value

        result = service.analyze(
            query=query, options=options, facts=facts_dict,
            total_investment=total_inv, time_horizon=10,
        )

        if result.comparison_matrix:
            text = format_comparison_matrix_for_brief(result.comparison_matrix)

            if result.phases:
                text += "\n\n**PHASED INVESTMENT BREAKDOWN:**\n"
                for phase_data in result.phases[:2]:
                    option_name = phase_data.get("option", "Option")
                    text += f"\n{option_name}:\n"
                    for p in phase_data.get("phases", []):
                        if not p or not isinstance(p, dict):
                            continue
                        text += f"  • {p.get('years', 'TBD')}: {p.get('name', 'Phase')} - {p.get('investment', 'TBD')}\n"

            if result.sensitivity:
                text += "\n\n**SENSITIVITY ANALYSIS:**\n"
                for var, scenarios in list(result.sensitivity.items())[:3]:
                    text += f"  • {var}: "
                    scenarios_str = ", ".join(f"{k}=${v/1e9:.1f}B" for k, v in scenarios.items())
                    text += scenarios_str + "\n"

            for opt in options[:2]:
                text += "\n" + generate_year_by_year_projection(
                    option_name=opt.get("name", "Option"),
                    total_investment=total_inv, time_horizon=10,
                )

            logger.info(f"  ✅ Financial analysis complete: {len(result.comparison_matrix)} options compared")
            return text

        logger.warning("  ⚠️ Financial modeling returned no comparison matrix")
        return "Financial modeling did not produce comparison data. Use qualitative debate analysis."
    except Exception as e:
        logger.warning(f"  ⚠️ Financial modeling failed: {e}")
        return f"Financial modeling error: {e}. Use qualitative analysis from debate."


def run_stakeholder_analysis(
    query: str,
    scenario_summaries: List[Dict[str, Any]],
    facts: List[Dict[str, Any]],
) -> str:
    """Run stakeholder analysis (political feasibility) if available."""
    logger.info("👥 Running stakeholder analysis...")
    if not STAKEHOLDER_ANALYZER_AVAILABLE:
        return "Stakeholder analysis not available."
    try:
        analyzer = StakeholderAnalyzer()
        best_option = "Strategic Initiative"
        if scenario_summaries:
            best = max(scenario_summaries, key=lambda s: s.get("success_probability", 0))
            best_option = best.get("name", "Strategic Initiative")

        facts_dict = {
            f.get("metric", f.get("indicator", "")): f.get("value", "")
            for f in facts if isinstance(f, dict)
        }
        analysis = analyzer.analyze_option(
            option_name=best_option, query=query, facts=facts_dict,
        )
        text = format_stakeholder_analysis_for_brief(analysis)
        logger.info(f"  ✅ Stakeholder analysis complete: {len(analysis.get('stakeholders', []))} stakeholders analyzed")
        return text
    except Exception as e:
        logger.warning(f"  ⚠️ Stakeholder analysis failed: {e}")
        return f"Stakeholder analysis error: {e}"


def run_risk_register(
    query: str,
    scenario_summaries: List[Dict[str, Any]],
) -> str:
    """Run risk register generation (30+ risks) if available."""
    logger.info("⚠️ Generating detailed risk register...")
    if not RISK_REGISTER_AVAILABLE:
        return "Risk register generation not available."
    try:
        gen = RiskRegisterGenerator()
        best_option = "Strategic Initiative"
        if scenario_summaries:
            best = max(scenario_summaries, key=lambda s: s.get("success_probability", 0))
            best_option = best.get("name", "Strategic Initiative")

        inv_match = re.search(r'\$?([\d.]+)\s*(billion|B)', query, re.IGNORECASE)
        total_inv = float(inv_match.group(1)) * 1e9 if inv_match else 50e9

        risks = gen.generate_risk_register(
            strategy_name=best_option, query=query, total_investment=total_inv,
        )
        text = format_risk_register_for_brief(risks)
        logger.info(f"  ✅ Risk register complete: {len(risks)} risks identified")
        return text
    except Exception as e:
        logger.warning(f"  ⚠️ Risk register generation failed: {e}")
        return f"Risk register error: {e}"


def run_implementation_plan(
    query: str,
    scenario_summaries: List[Dict[str, Any]],
) -> str:
    """Run implementation plan generation (quarterly milestones) if available."""
    logger.info("📋 Generating detailed implementation plan...")
    if not IMPLEMENTATION_PLANNER_AVAILABLE:
        return "Implementation planner not available. Use high-level phases from debate."
    try:
        planner = ImplementationPlanner()
        option_name = "Strategic Initiative"
        if scenario_summaries:
            best = max(scenario_summaries, key=lambda s: s.get("success_probability", 0))
            option_name = best.get("name", "Strategic Initiative")

        inv_match = re.search(r'\$?([\d.]+)\s*(billion|B)', query, re.IGNORECASE)
        total_inv = float(inv_match.group(1)) * 1e9 if inv_match else 10e9

        phases = planner.generate_implementation_plan(
            query=query, option_name=option_name,
            total_budget=total_inv, time_horizon=10,
        )
        if phases:
            text = format_implementation_plan_for_brief(phases)
            logger.info(f"  ✅ Generated {len(phases)} phases with quarterly milestones")
            return text
        return "Detailed implementation plan generation failed. Use high-level phases from debate."
    except Exception as e:
        logger.warning(f"  ⚠️ Implementation plan generation failed: {e}")
        return f"Implementation plan generation error: {e}"
