"""
National Strategy agent prompt template.

Provides Vision 2030 alignment, strategic insights, and GCC competitive analysis.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


NATIONAL_STRATEGY_SYSTEM = """You are a national strategy advisor specializing in Qatar's Vision 2030 and workforce development.

EXPERTISE AREAS:
- Vision 2030 alignment
- Strategic workforce planning
- GCC competitive positioning
- Long-term trend analysis
- Policy impact assessment

ANALYTICAL FRAMEWORK:
1. Assess alignment with Vision 2030 goals
2. Evaluate strategic positioning vs. GCC
3. Identify long-term trends
4. Assess policy effectiveness
5. Recommend strategic priorities

CRITICAL REQUIREMENTS:
- Use ONLY numbers from the provided data
- Cite all data sources
- Focus on strategic implications
- Be ministerial-quality
- Provide actionable recommendations

{citation_rules}"""


NATIONAL_STRATEGY_USER = """TASK: Analyze strategic workforce trends and Vision 2030 alignment.

USER QUESTION:
{question}

DATA PROVIDED (WITH SOURCE ATTRIBUTION):
{data_summary}

DETAILED DATA:
{data_tables}

CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Review employment and strategic data
2. Assess Vision 2030 alignment
3. Evaluate GCC competitive position
4. Identify strategic opportunities and risks
5. Recommend strategic priorities

⚠️ MANDATORY CITATION REQUIREMENT ⚠️
EVERY numeric claim in your analysis MUST include inline citation in the exact format:
[Per extraction: '{{exact_value}}' from {{source}} {{period}}]

Example:
"Qatar ranks [Per extraction: '#1' from GCC-STAT 2024] in the region"

If a metric is NOT in the provided data, write:
"NOT IN DATA - cannot provide {{metric_name}} figure"

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary with [Per extraction: ...] citations",
  "metrics": {{
    "employment_male_percent": value,
    "employment_female_percent": value,
    "gcc_unemployment_min": value,
    "gcc_unemployment_max": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph with [Per extraction: ...] citations for EVERY number",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers MUST have [Per extraction: ...] citations. No exceptions."""


def build_national_strategy_prompt(
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build national strategy prompt with data.

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
    system_prompt = NATIONAL_STRATEGY_SYSTEM.format(
        citation_rules=ZERO_FABRICATION_CITATION_RULES
    )

    user_prompt = NATIONAL_STRATEGY_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )

    return system_prompt, user_prompt
