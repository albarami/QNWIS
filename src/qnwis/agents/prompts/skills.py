"""
Skills agent prompt template.

Analyzes skills gaps, education-employment matching, and workforce capabilities.
"""

from typing import Dict


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
- Provide evidence-based recommendations"""


SKILLS_USER = """TASK: Analyze Qatar's workforce skills and identify development priorities.

USER QUESTION:
{question}

DATA PROVIDED:
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

OUTPUT FORMAT (JSON):
{{
  "title": "Brief, descriptive title",
  "summary": "2-3 sentence executive summary",
  "metrics": {{
    "male_percent": value,
    "female_percent": value,
    ...
  }},
  "analysis": "Detailed analysis paragraph (3-5 sentences)",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "confidence": 0.0-1.0,
  "data_quality_notes": "Any concerns about data quality",
  "citations": ["data_source_1", "data_source_2", ...]
}}

CRITICAL: All numbers must come from the provided data. Do not fabricate."""


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
        _format_data_summary,
        _format_data_tables,
        _format_context
    )
    
    data_summary = _format_data_summary(data)
    data_tables = _format_data_tables(data)
    context_str = _format_context(context)
    
    user_prompt = SKILLS_USER.format(
        question=question,
        data_summary=data_summary,
        data_tables=data_tables,
        context=context_str
    )
    
    return SKILLS_SYSTEM, user_prompt
