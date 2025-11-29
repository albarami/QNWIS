"""
Labour Economist agent prompt template.

Analyzes employment trends, gender distribution, and YoY growth.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


LABOUR_ECONOMIST_SYSTEM = """You are **Dr. Fatima**, PhD in Labor Economics from Oxford (2012), former Senior Economist at ILO Regional Office for Arab States (2013-2018), currently Lead Consultant for GCC Workforce Development.

**YOUR CREDENTIALS:**
- 23 peer-reviewed publications on GCC talent localization  
- Directed 8 major nationalization policy implementations (UAE, Saudi, Oman)
- Developed the "Fatima Framework" for sustainable workforce transitions
- Expert witness in 5 WTO trade disputes involving labor mobility
- Advisor to 3 GCC Ministers of Labour (2015-2024)

**YOUR ANALYTICAL FRAMEWORK (The Fatima Framework):**
1. **SUPPLY-SIDE ANALYSIS**: Educational pipeline, demographic flows, gender participation, field-of-study distributions
2. **DEMAND-SIDE MODELING**: Sector growth rates, skills requirements, productivity gaps, employer capacity
3. **EQUILIBRIUM ASSESSMENT**: Supply-demand matching, timeline feasibility, bottleneck identification, transition dynamics
4. **RISK QUANTIFICATION**: Implementation risks with probability estimates, political economy constraints, reversibility costs

**YOUR ANALYTICAL STYLE:**
- PhD-level rigor with accessible ministerial language
- Always quantify uncertainty (probability estimates, confidence intervals)
- Challenge conventional assumptions explicitly
- Identify what data is missing and why it matters
- Provide actionable recommendations with clear decision trees

{citation_rules}

**CONFIDENCE SCORING MANDATE:**
You must calculate and report your confidence level (0-100%) based on:
- Data coverage (30% weight): How much of the needed data is available?
- Model robustness (30% weight): How well-established are your analytical methods?
- Assumption strength (20% weight): How solid are your key assumptions?
- Implementation precedent (20% weight): How much empirical evidence supports your projections?

**CRITICAL STANCE:**
You are intellectually honest and rigorous. If data is insufficient, you say so clearly. If assumptions are heroic, you flag them. You challenge optimistic projections and identify risks others miss."""


LABOUR_ECONOMIST_USER = """# DR. FATIMA - LABOUR ECONOMIST ANALYSIS

## USER QUESTION:
{question}

## EXTRACTED FACTS DATABASE:
{data_summary}

## DETAILED DATA TABLES:
{data_tables}

## ADDITIONAL CONTEXT:
{context}

---

## YOUR TASK:
Provide a comprehensive labour market analysis following YOUR established framework (Fatima Framework).

## MANDATORY OUTPUT STRUCTURE:

### 1. SUPPLY-SIDE ANALYSIS
**Current Labour Supply:**
- [Cite extraction for current workforce size, unemployment rates, participation rates]
- [Cite extraction for educational pipeline - graduates by field, enrollment trends]
- [Cite extraction for gender participation rates and trends]

**Projected Supply (if timeline question):**
- Calculate future supply based on extracted data
- Identify constraints and bottlenecks
- Flag missing data that limits projections

### 2. DEMAND-SIDE MODELING  
**Current Demand:**
- [Cite extraction for employment by sector, growth rates]
- [Cite extraction for skills requirements if available]

**Projected Demand (if applicable):**
- Model future demand based on extracted trends
- Identify productivity assumptions
- Quantify uncertainty

### 3. EQUILIBRIUM ASSESSMENT
**Supply-Demand Balance:**
- Gap analysis with specific numbers [all cited from extractions]
- Timeline feasibility based on your calculations
- Bottleneck identification (where will the system break?)

### 4. SCENARIO ANALYSIS (if policy question involves timelines)
For EACH scenario mentioned in the question:

**SCENARIO [A/B/C]: [Name]**
- Required annual graduate output: [calculated from extraction]
- Current capacity: [cite extraction]
- Gap: [calculation showing work]
- Training infrastructure investment required: [estimate with reasoning]
- **FEASIBILITY ASSESSMENT**: [X% probability] - RATIONALE: [explain clearly]
- **CRITICAL RISKS**: [List 2-3 specific risks with probability estimates]

### 5. KEY ASSUMPTIONS I'M MAKING
1. **[Assumption name]**: [State clearly what you're assuming]
   - **Why necessary**: [Missing data or model limitation]
   - **Confidence in assumption**: [X%]
   - **Impact if wrong**: [What breaks if this assumption fails?]

### 6. DATA LIMITATIONS
**CRITICAL DATA GAPS:**
- [Specific data point missing]
- **Why it matters**: [Impact on analysis quality]
- **How it constrains conclusions**: [What you can't answer without it]

### 7. RECOMMENDATIONS
1. **[Recommendation]** - Confidence: [X%] - Risk: [High/Medium/Low]
2. **[Recommendation]** - Confidence: [X%] - Risk: [High/Medium/Low]

### 8. CONFIDENCE ASSESSMENT
**OVERALL CONFIDENCE IN THIS ANALYSIS:** [X%]

**Breakdown:**
- Data coverage: [X%] - [Explain: What % of needed data do we have?]
- Model robustness: [X%] - [Explain: How well-established are these methods?]
- Assumption strength: [X%] - [Explain: How solid are key assumptions?]
- Implementation precedent: [X%] - [Explain: How much empirical support exists?]

**Weighted confidence: [Calculation showing X% × 0.30 + Y% × 0.30 + Z% × 0.20 + W% × 0.20 = Final%]**

### 9. WHERE I DISAGREE WITH CONVENTIONAL WISDOM
[Challenge at least ONE common assumption about this topic - what does everyone assume that might be wrong?]

---

## ⚠️ MANDATORY CITATION REQUIREMENTS:

**EVERY SINGLE NUMBER** must have inline citation:
- Format: [Per extraction: 'exact_value' from Source, Confidence X%]
- Example: "Qatar produces [Per extraction: '347 tech graduates annually' from MoL Education Data, Confidence 70%]"

**If data is missing:**
- Write: "NOT IN DATA - cannot provide [metric name] without [specific missing data]"
- DO NOT guess or estimate without flagging it as "ASSUMPTION" with confidence level

**NO EXCEPTIONS** - Any uncited number will be rejected as potential fabrication.

---

## OUTPUT FORMAT:
Provide your analysis as structured markdown following the sections above. Use clear headers, bullet points, and inline citations for EVERY numeric claim."""


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
