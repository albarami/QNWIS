"""
Labour Economist agent with Dr. Fatima persona.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .base import (
    AgentReport,
    DataClient,
    Insight,
    coerce_llm_response_text,
    evidence_from,
    extract_assumptions,
    extract_citations_from_narrative,
    extract_data_gaps,
    extract_usage_tokens,
    resolve_response_model,
)
from qnwis.agents.prompts.base import ANTI_FABRICATION_RULES, format_extracted_facts

LABOUR_ECONOMIST_PERSONA = """
═══════════════════════════════════════════════════
👤 AGENT IDENTITY: Senior Labour Economist
═══════════════════════════════════════════════════

CREDENTIALS:
• PhD in Labor Economics, Oxford University (2012)
• Former Senior Economist, ILO Regional Office for Arab States (2013-2018)
• Lead Consultant, GCC Workforce Development Initiatives (2018-present)
• 23 peer-reviewed publications on Gulf labor market dynamics

EXPERTISE:
• Supply-demand modeling for constrained labor markets
• Educational pipeline capacity analysis
• Nationalization policy implementation (UAE, Saudi, Oman precedents)
• Gender participation gap analysis in STEM fields
• Regional talent mobility patterns

ANALYTICAL FRAMEWORK:
1. Supply Side: Calculate current and projected national graduate production
2. Demand Side: Calculate required workforce for target Qatarization levels
3. Gap Analysis: Quantify supply-demand mismatch with timeline constraints
4. Feasibility: Assign probability to each implementation scenario
5. Risk Assessment: Identify critical bottlenecks and failure modes

═══════════════════════════════════════════════════
"""


STRUCTURED_OUTPUT_TEMPLATE = """
PROVIDE YOUR ANALYSIS IN THIS EXACT FORMAT:

## 🧑‍💼 LABOUR ECONOMIST ANALYSIS
**Analyst:** Senior Labour Economist

### 1. SUPPLY-DEMAND CALCULATION

**Current National Production:**
[Cite extraction for annual graduate numbers]

**Required National Workforce:**
[Calculate from target % × current sector employment from extraction]

**Supply Gap:**
[Calculation showing shortfall]

### 2. SCENARIO FEASIBILITY ASSESSMENT

**SCENARIO A (Aggressive - 3 years):**
- Required annual output: [calculation]
- Current capacity: [cite extraction]
- Capacity multiplier needed: [X]x
- **Feasibility Probability: [X]%**
- **Reasoning:** [Explain using cited facts]

**SCENARIO B (Moderate - 5 years):**
- Required annual output: [calculation]
- **Feasibility Probability: [X]%**
- **Reasoning:** [Explain using cited facts]

**SCENARIO C (Conservative - 8 years):**
- Required annual output: [calculation]
- **Feasibility Probability: [X]%**
- **Reasoning:** [Explain using cited facts]

### 3. CRITICAL BOTTLENECKS
1. **[Bottleneck Name]:** [Describe with evidence]
2. **[Bottleneck Name]:** [Describe with evidence]

### 4. DATA LIMITATIONS
**Missing Data That Would Improve Analysis:**
- [Specific data point needed]
- [Specific data point needed]

### 5. CONFIDENCE ASSESSMENT
**Overall Confidence: [X]%**

**Breakdown:**
- Data coverage: [X]% (have X out of Y critical data points)
- Model robustness: [X]% (assumptions needed: [list])
- Implementation precedent: [X]% (similar policies: [examples])

**What Would Increase Confidence:**
[List specific data or analysis needed]

═══════════════════════════════════════════════════
"""


async def analyze(
    query: str,
    extracted_facts: List[Dict[str, Any]],
    llm_client: Any,
) -> dict[str, Any]:
    """Labour Economist analysis with mandatory citation enforcement."""

    facts_formatted = format_extracted_facts(extracted_facts)
    
    prompt = f"""
{LABOUR_ECONOMIST_PERSONA}

{ANTI_FABRICATION_RULES}

{facts_formatted}

MINISTERIAL QUERY:
{query}

{STRUCTURED_OUTPUT_TEMPLATE}

NOW PROVIDE YOUR ANALYSIS:
"""
    
    try:
        response = await llm_client.ainvoke(prompt)
        narrative = coerce_llm_response_text(response)

        if "Per extraction:" not in narrative and "NOT IN DATA" not in narrative:
            narrative = (
                "⚠️ ANALYSIS REJECTED - No citations found. "
                "Agent violated citation requirements.\n\n" + narrative
            )

        citations = extract_citations_from_narrative(narrative, extracted_facts)
        data_gaps = extract_data_gaps(narrative)
        assumptions = extract_assumptions(narrative)
        facts_used = sorted({citation["metric"] for citation in citations})
        confidence = extract_confidence_from_response(narrative)
        tokens_in, tokens_out = extract_usage_tokens(response)
        model_name = resolve_response_model(response, llm_client)

        return {
            "agent_name": "labour_economist",
            "narrative": narrative,
            "confidence": confidence,
            "citations": citations,
            "facts_used": facts_used,
            "assumptions": assumptions,
            "data_gaps": data_gaps,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model_name,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    except Exception as exc:  # pragma: no cover - defensive
        error_text = f"ERROR: {exc}"
        return {
            "agent_name": "labour_economist",
            "narrative": error_text,
            "confidence": 0.0,
            "citations": [],
            "facts_used": [],
            "assumptions": [],
            "data_gaps": ["Agent execution failed"],
            "timestamp": datetime.utcnow().isoformat(),
            "model": getattr(llm_client, "model", "unknown"),
            "tokens_in": 0,
            "tokens_out": 0,
        }


def extract_confidence_from_response(response: str) -> float:
    """Extract confidence percentage from structured output."""
    import re

    patterns = [
        r"Overall Confidence:\s*(\d+)%",
        r"Confidence:\s*(\d+)%",
        r"confidence[""\s:]+(\d+)%",
        r"Feasibility Probability:\s*(\d+)%",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            confidence_pct = float(match.group(1))
            return min(confidence_pct / 100.0, 1.0)

    if "⚠️ ANALYSIS REJECTED" in response or "NOT FOUND" in response:
        return 0.0

    if len(response) < 100:
        return 0.2

    has_citations = "Per extraction:" in response or "[Per extraction:" in response
    has_calculations = any(word in response for word in ["calculated as", "equals", "totals"])
    has_scenarios = "SCENARIO" in response.upper()

    if has_citations and has_calculations and has_scenarios:
        return 0.7
    if has_citations:
        return 0.6
    return 0.4


class LabourEconomistAgent:
    """
    Deterministic labour economist that tracks gender employment trends.

    The agent operates purely on the deterministic catalog (no LLM calls) so
    that the orchestration workflow and existing unit tests continue to work
    after the module-level `analyze` coroutine was introduced for LangGraph.
    """

    DEFAULT_QUERY_ID = "syn_employment_share_by_gender_latest"

    def __init__(self, client: DataClient, query_id: str | None = None) -> None:
        self.client = client
        self.query_id = query_id or self.DEFAULT_QUERY_ID

    def _numeric(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _year(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _sorted_rows(self, rows: List[Any]) -> List[Any]:
        enumerated = list(enumerate(rows))

        def sort_key(item: tuple[int, Any]) -> tuple[int, int]:
            idx, row = item
            yr = self._year(row.data.get("year"))
            if yr is None:
                return (1, idx)
            return (0, yr)

        enumerated.sort(key=sort_key)
        return [row for _, row in enumerated]

    def _build_metrics(self, rows: List[Any]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        if not rows:
            return metrics

        latest = rows[-1]
        previous = rows[-2] if len(rows) >= 2 else None

        for key in ("male_percent", "female_percent", "total_percent"):
            val = self._numeric(latest.data.get(key))
            if val is not None:
                metrics[key] = round(val, 2)

        latest_year = self._year(latest.data.get("year"))
        if latest_year is not None:
            metrics["latest_year"] = float(latest_year)

        if previous is not None:
            latest_female = self._numeric(latest.data.get("female_percent"))
            prev_female = self._numeric(previous.data.get("female_percent"))
            if latest_female is not None and prev_female is not None:
                metrics["yoy_percent"] = round(latest_female - prev_female, 2)

        return metrics

    def _summarize(self, rows: List[Any], metrics: dict[str, float]) -> str:
        if not rows:
            return "No employment share data is available for labour analysis."

        latest = rows[-1]
        latest_year = self._year(latest.data.get("year"))
        male = self._numeric(latest.data.get("male_percent"))
        female = self._numeric(latest.data.get("female_percent"))

        parts: list[str] = []
        period = f"{latest_year}" if latest_year is not None else "the latest reported period"

        if male is not None and female is not None:
            parts.append(
                f"Female participation is {female:.1f}% versus {male:.1f}% for males in {period}."
            )
        elif female is not None:
            parts.append(f"Female participation stands at {female:.1f}% in {period}.")
        elif male is not None:
            parts.append(f"Male participation stands at {male:.1f}% in {period}.")
        else:
            parts.append(f"Employment share data for {period} is missing numeric values.")

        yoy = metrics.get("yoy_percent")
        if yoy is not None and len(rows) >= 2:
            prev_year = self._year(rows[-2].data.get("year"))
            direction = "increased" if yoy >= 0 else "fell"
            change = abs(yoy)
            if prev_year is not None:
                parts.append(
                    f"Female share {direction} by {change:.1f} percentage points compared to {prev_year}."
                )
            else:
                parts.append(
                    f"Female share {direction} by {change:.1f} percentage points versus the prior observation."
                )

        return " ".join(parts)

    def run(self) -> AgentReport:
        result = self.client.run(self.query_id)
        rows = self._sorted_rows(list(result.rows))
        metrics = self._build_metrics(rows)
        summary = self._summarize(rows, metrics)
        warnings = list(result.warnings)

        finding = Insight(
            title="Gender employment share trend",
            summary=summary,
            metrics=metrics,
            evidence=[evidence_from(result)] if rows else [],
            warnings=warnings,
        )

        return AgentReport(
            agent="LabourEconomist",
            findings=[finding],
            warnings=warnings,
            metadata={
                "query_id": result.query_id,
                "row_count": len(rows),
            },
        )
