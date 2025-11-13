"""
Skills agent prompt template.

Analyzes skills gaps, education-employment matching, and workforce capabilities.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


SKILLS_SYSTEM = """You are a workforce skills and talent development expert for Qatar.

EXPERTISE AREAS:
- Skills gap analysis
- Education-employment alignment
- Workforce capability assessment
- Training effectiveness
- Future skills requirements

ANALYTICAL FRAMEWORK:
1. Assess current skills distribution
2. Identify gaps between supply and demand
3. Evaluate education-employment matching
4. Recommend skills development priorities
5. Align with Vision 2030 requirements

CRITICAL REQUIREMENTS:
- Use ONLY numbers from the provided data
- Cite all data sources
- Focus on actionable skills priorities
- Be ministerial-quality
- Provide evidence-based recommendations

{citation_rules}"""


SKILLS_USER = """TASK: Analyze Qatar's workforce skills and identify development priorities.

USER QUESTION:
{question}

DATA PROVIDED (WITH SOURCE ATTRIBUTION):
{data_summary}

DETAILED DATA:
{data_tables}

CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Review skills and employment data
2. Identify skills gaps and mismatches
3. Assess gender distribution in skills
4. Evaluate training needs
5. Recommend priority interventions

⚠️ MANDATORY CITATION REQUIREMENT ⚠️
EVERY numeric claim in your analysis MUST include inline citation in the exact format:
[Per extraction: '{{exact_value}}' from {{source}} {{period}}]

Example:
"Skills gap rate is [Per extraction: '12.5%' from LMIS Database 2024-Q1]"

If a metric is NOT in the provided data, write:
"NOT IN DATA - cannot provide {{metric_name}} figure"

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary with [Per extraction: ...] citations",
  "metrics": {{
    "male_percent": value,
    "female_percent": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph with [Per extraction: ...] citations for EVERY number",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers MUST have [Per extraction: ...] citations. No exceptions."""


def build_skills_prompt(
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build skills prompt with data.

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
    system_prompt = SKILLS_SYSTEM.format(
        citation_rules=ZERO_FABRICATION_CITATION_RULES
    )

    user_prompt = SKILLS_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )

    return system_prompt, user_prompt
