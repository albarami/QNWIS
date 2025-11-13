"""
Nationalization agent prompt template.

Analyzes Qatarization metrics and GCC benchmarking.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


NATIONALIZATION_SYSTEM = """You are a nationalization policy expert specializing in Qatar's Qatarization initiatives.

EXPERTISE AREAS:
- Qatarization rates and trends
- GCC regional benchmarking
- Workforce composition analysis
- Nationalization policy effectiveness
- Competitive positioning vs. GCC peers

ANALYTICAL FRAMEWORK:
1. Assess current Qatarization levels
2. Compare against GCC benchmarks
3. Identify gaps and opportunities
4. Evaluate policy effectiveness
5. Recommend strategic interventions

CRITICAL REQUIREMENTS:
- Use ONLY numbers from the provided data
- Cite all data sources
- Provide regional context
- Be ministerial-quality
- Focus on actionable insights

{citation_rules}"""


NATIONALIZATION_USER = """TASK: Analyze Qatar's nationalization metrics and GCC competitive positioning.

USER QUESTION:
{question}

DATA PROVIDED (WITH SOURCE ATTRIBUTION):
{data_summary}

DETAILED DATA:
{data_tables}

CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Review Qatarization data and GCC benchmarks
2. Identify Qatar's competitive position
3. Calculate key metrics (rates, rankings, gaps)
4. Assess trends and patterns
5. Provide policy recommendations

⚠️ MANDATORY CITATION REQUIREMENT ⚠️
EVERY numeric claim in your analysis MUST include inline citation in the exact format:
[Per extraction: '{{exact_value}}' from {{source}} {{period}}]

Example:
"Qatar's Qatarization rate is [Per extraction: '23.5%' from Ministry Report 2024]"

If a metric is NOT in the provided data, write:
"NOT IN DATA - cannot provide {{metric_name}} figure"

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary with [Per extraction: ...] citations",
  "metrics": {{
    "qatar_unemployment_percent": value,
    "qatar_rank_gcc": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph with [Per extraction: ...] citations for EVERY number",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers MUST have [Per extraction: ...] citations. No exceptions."""


def build_nationalization_prompt(
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build nationalization prompt with data.

    Args:
        question: User's question
        data: Dictionary of QueryResult objects
        context: Additional context

    Returns:
        (system_prompt, user_prompt) tuple
    """
    from src.qnwis.agents.prompts.labour_economist import (
        _format_data_summary_with_sources,
        _format_data_tables,
        _format_context
    )

    data_summary = _format_data_summary_with_sources(data)
    data_tables = _format_data_tables(data)
    context_str = _format_context(context)

    # Inject citation rules into system prompt
    system_prompt = NATIONALIZATION_SYSTEM.format(
        citation_rules=ZERO_FABRICATION_CITATION_RULES
    )

    user_prompt = NATIONALIZATION_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )

    return system_prompt, user_prompt
