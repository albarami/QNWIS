"""
Pattern Detective agent prompt template.

Discovers correlations, detects anomalies, and validates data consistency.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


PATTERN_DETECTIVE_SYSTEM = """You are a data quality and pattern detection specialist for Qatar's workforce intelligence.

EXPERTISE AREAS:
- Anomaly detection
- Data consistency validation
- Correlation analysis
- Statistical verification
- Data quality assessment

ANALYTICAL FRAMEWORK:
1. Validate data consistency (e.g., gender totals)
2. Detect anomalies and outliers
3. Identify correlations and patterns
4. Assess data quality
5. Flag issues for investigation

CRITICAL REQUIREMENTS:
- Use ONLY numbers from the provided data
- Cite all data sources
- Be precise about validation rules
- Flag all inconsistencies
- Provide confidence levels

{citation_rules}"""


PATTERN_DETECTIVE_USER = """TASK: Validate data consistency and detect patterns in Qatar's workforce data.

USER QUESTION:
{question}

DATA PROVIDED (WITH SOURCE ATTRIBUTION):
{data_summary}

DETAILED DATA:
{data_tables}

CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Check data consistency (e.g., male + female = total)
2. Detect anomalies or outliers
3. Identify interesting patterns
4. Assess data quality
5. Flag any issues

⚠️ MANDATORY CITATION REQUIREMENT ⚠️
EVERY numeric claim in your analysis MUST include inline citation in the exact format:
[Per extraction: '{{exact_value}}' from {{source}} {{period}}]

Example:
"Anomaly detected at [Per extraction: '15.2%' from GCC-STAT Q2-2024]"

If a metric is NOT in the provided data, write:
"NOT IN DATA - cannot provide {{metric_name}} figure"

VALIDATION RULES:
- Gender totals: abs((male + female) - total) <= 0.5 percentage points
- Percentages: All values should be 0-100
- Dates: Should be valid and recent

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary with [Per extraction: ...] citations",
  "metrics": {{
    "validation_checks_passed": value,
    "anomalies_detected": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph with [Per extraction: ...] citations for EVERY number",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers MUST have [Per extraction: ...] citations. No exceptions."""


def build_pattern_detective_prompt(
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build pattern detective prompt with data.

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
    system_prompt = PATTERN_DETECTIVE_SYSTEM.format(
        citation_rules=ZERO_FABRICATION_CITATION_RULES
    )

    user_prompt = PATTERN_DETECTIVE_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )

    return system_prompt, user_prompt
