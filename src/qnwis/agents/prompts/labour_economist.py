"""
Labour Economist agent prompt template.

Analyzes employment trends, gender distribution, and YoY growth.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


LABOUR_ECONOMIST_SYSTEM = """You are a senior labour economist with deep expertise in Qatar's workforce dynamics.

EXPERTISE AREAS:
- Employment trends and patterns
- Gender distribution analysis
- Year-over-year growth calculations
- Sector-specific labour market insights
- Policy implications and recommendations

ANALYTICAL FRAMEWORK:
1. Data Analysis: Examine provided data thoroughly
2. Pattern Recognition: Identify trends and anomalies
3. Contextualization: Provide Qatar-specific context
4. Implications: Draw policy-relevant conclusions
5. Recommendations: Suggest evidence-based actions

CRITICAL REQUIREMENTS:
- Use ONLY numbers from the provided data
- Cite data sources for every statistic
- Provide confidence levels for conclusions
- Acknowledge data limitations
- Be precise and ministerial-quality

{citation_rules}"""


LABOUR_ECONOMIST_USER = """TASK: Analyze Qatar's labour market data to answer the user's question.

USER QUESTION:
{question}

DATA PROVIDED (WITH SOURCE ATTRIBUTION):
{data_summary}

DETAILED DATA:
{data_tables}

CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Review all provided data carefully
2. Identify key metrics relevant to the question
3. Calculate derived metrics if needed (growth rates, percentages)
4. Identify patterns and trends
5. Provide interpretation and context
6. Suggest policy implications

⚠️ MANDATORY CITATION REQUIREMENT ⚠️
EVERY numeric claim in your analysis MUST include inline citation in the exact format:
[Per extraction: '{{exact_value}}' from {{source}} {{period}}]

Example:
"Qatar's unemployment rate is [Per extraction: '0.10%' from GCC-STAT Q1-2024]"

If a metric is NOT in the provided data, write:
"NOT IN DATA - cannot provide {{metric_name}} figure"

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary with [Per extraction: ...] citations",
  "metrics": {{
    "metric_name": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph with [Per extraction: ...] citations for EVERY number",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers MUST have [Per extraction: ...] citations. No exceptions."""


def build_labour_economist_prompt(
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build labour economist prompt with data.

    Args:
        question: User's question
        data: Dictionary of QueryResult objects
        context: Additional context

    Returns:
        (system_prompt, user_prompt) tuple
    """
    data_summary = _format_data_summary_with_sources(data)
    data_tables = _format_data_tables(data)
    context_str = _format_context(context)

    # Inject citation rules into system prompt
    system_prompt = LABOUR_ECONOMIST_SYSTEM.format(
        citation_rules=ZERO_FABRICATION_CITATION_RULES
    )

    user_prompt = LABOUR_ECONOMIST_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )

    return system_prompt, user_prompt


def _format_data_summary_with_sources(data: Dict) -> str:
    """
    Format data summary with explicit source attribution for citations.

    This helps the LLM understand what sources to cite.
    """
    if not data:
        return "No data available."

    lines = []
    for key, query_result in data.items():
        lines.append(f"- {key}: {len(query_result.rows)} rows")

        # Extract source and period for citation format
        source = "Unknown Source"
        period = "Unknown Period"

        if hasattr(query_result, 'provenance') and query_result.provenance:
            source = query_result.provenance.source
            lines.append(f"  Source: {source}")

        if hasattr(query_result, 'freshness') and query_result.freshness:
            period = str(query_result.freshness.asof_date)
            lines.append(f"  Period: {period}")

        # Add citation template
        lines.append(f"  Citation format: [Per extraction: '{{value}}' from {source} {period}]")
        lines.append("")

    return "\n".join(lines)


def _format_data_summary(data: Dict) -> str:
    """Format data summary for prompt (legacy)."""
    if not data:
        return "No data available."

    lines = []
    for key, query_result in data.items():
        lines.append(f"- {key}: {len(query_result.rows)} rows")
        if hasattr(query_result, 'provenance') and query_result.provenance:
            lines.append(f"  Source: {query_result.provenance.source}")
        if hasattr(query_result, 'freshness') and query_result.freshness:
            lines.append(f"  Freshness: {query_result.freshness.asof_date}")
    return "\n".join(lines)


def _format_data_tables(data: Dict) -> str:
    """Format data tables as markdown for prompt."""
    if not data:
        return "No data tables available."
    
    tables = []
    for key, query_result in data.items():
        tables.append(f"### {key}")
        
        # Format as markdown table
        if hasattr(query_result, 'to_markdown'):
            tables.append(query_result.to_markdown())
        else:
            # Fallback: format rows manually
            if query_result.rows:
                # Get headers from first row
                headers = list(query_result.rows[0].data.keys())
                tables.append("| " + " | ".join(headers) + " |")
                tables.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                # Add rows (limit to first 20)
                for row in query_result.rows[:20]:
                    values = [str(row.data.get(h, "")) for h in headers]
                    tables.append("| " + " | ".join(values) + " |")
                
                if len(query_result.rows) > 20:
                    tables.append(f"\n... ({len(query_result.rows) - 20} more rows)")
        
        tables.append("")
    
    return "\n".join(tables)


def _format_context(context: Dict) -> str:
    """Format context dictionary."""
    if not context:
        return "No additional context provided."
    
    lines = []
    for key, value in context.items():
        if isinstance(value, dict):
            lines.append(f"- {key}:")
            for k, v in value.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"- {key}: {value}")
    
    return "\n".join(lines)
