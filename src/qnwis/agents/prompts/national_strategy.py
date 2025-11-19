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

If a metric is NOT in the provided data, write:
"NOT IN DATA - cannot provide metric_name figure"

OUTPUT FORMAT (JSON):
Return a valid JSON object with these fields:
- title: Brief, descriptive title
- summary: 2-3 sentence executive summary with citations
- metrics: Dictionary of numeric findings
- analysis: Detailed analysis paragraph with citations for EVERY number
- recommendations: List of recommendations
- confidence: Float 0.0-1.0
- data_quality_notes: Any concerns about data quality
- citations: List of data sources

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
    from qnwis.agents.prompts.labour_economist import (
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
  "title": "Vision 2030 Workforce Alignment Assessment",
  "summary": "Strategic analysis reveals strong progress toward Vision 2030 goals with 90% confidence. Key metrics show improving employment trends across sectors.",
  "metrics": {
    "employment_male_percent": 85.2,
    "employment_female_percent": 58.1,
    "gcc_unemployment_min": 1.2
  },
  "analysis": "### Vision 2030 Alignment\\n\\nEmployment data shows [Per extraction: '85.2%' from LMIS Q1-2024] male participation rate.\\n\\n### Strategic Recommendations\\n\\nContinue current trajectory with focused investments.",
  "recommendations": ["Accelerate female workforce participation initiatives", "Monitor GCC competitive positioning quarterly"],
  "confidence": 0.90,
  "data_quality_notes": "Comprehensive data coverage across key metrics",
  "citations": ["employment_gender", "gcc_unemployment"]
}
'''
    user_prompt += json_example

    return system_prompt, user_prompt
