"""
Pattern Detective agent prompt template.

Discovers correlations, detects anomalies, and validates data consistency.
"""

from typing import Dict


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
- Provide confidence levels"""


PATTERN_DETECTIVE_USER = """TASK: Validate data consistency and detect patterns in Qatar's workforce data.

USER QUESTION:
{question}

DATA PROVIDED:
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

VALIDATION RULES:
- Gender totals: abs((male + female) - total) <= 0.5 percentage points
- Percentages: All values should be 0-100
- Dates: Should be valid and recent

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary",
  "metrics": {{
    "validation_checks_passed": value,
    "anomalies_detected": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph (3-5 sentences)",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers must come from the provided data. Do not fabricate."""


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
        _format_data_summary,
        _format_data_tables,
        _format_context
    )
    
    data_summary = _format_data_summary(data)
    data_tables = _format_data_tables(data)
    context_str = _format_context(context)
    
    user_prompt = PATTERN_DETECTIVE_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )
    
    return PATTERN_DETECTIVE_SYSTEM, user_prompt
