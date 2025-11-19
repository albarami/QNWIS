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
Return a valid JSON object with these fields:
- title: Brief, descriptive title
- summary: 2-3 sentence executive summary with citations
- metrics: Dictionary of numeric findings (validation checks passed, anomalies detected, etc.)
- analysis: Detailed analysis paragraph with citations for EVERY number
- recommendations: List of recommendations
- confidence: Float 0.0-1.0
- data_quality_notes: Any concerns about data quality
- citations: List of data sources

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
    from qnwis.agents.prompts.labour_economist import (
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

    # Append JSON schema example AFTER format
    json_example = '''

CRITICAL JSON FORMATTING RULES:
1. Use \\n (escaped newline) for line breaks in the analysis field
2. Escape all quotes inside strings with \\"
3. Do not include trailing commas
4. Ensure all braces and brackets are balanced
5. Return ONLY the JSON object - no markdown code blocks, no explanatory text

EXAMPLE JSON OUTPUT:
{
  "title": "Data Quality Assessment for Employment Data",
  "summary": "Validation reveals high data quality with 2 minor anomalies detected. Analysis based on Q1-2024 data with 85% confidence.",
  "metrics": {
    "validation_checks_passed": 10,
    "anomalies_detected": 2
  },
  "analysis": "### Data Consistency Validation\\n\\nPerformed 10 validation checks on employment data.\\n\\n### Anomalies Detected\\n\\nIdentified [Per extraction: '15.2%' from GCC-STAT Q2-2024] as outlier.",
  "recommendations": ["Investigate identified anomalies", "Enhance data quality monitoring"],
  "confidence": 0.85,
  "data_quality_notes": "High quality overall with minor outliers",
  "citations": ["gcc_unemployment", "employment_gender"]
}
'''
    user_prompt += json_example

    return system_prompt, user_prompt
