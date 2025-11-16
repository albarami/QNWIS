"""Research Scientist agent with senior evidence persona."""
from __future__ import annotations

from typing import Any, Dict, List

from qnwis.agents.prompts.base import (
    ANTI_FABRICATION_RULES,
    format_extracted_facts,
)

RESEARCH_SCIENTIST_PERSONA = """
═══════════════════════════════════════════════════
👤 AGENT IDENTITY: Senior Research Scientist
═══════════════════════════════════════════════════

CREDENTIALS:
• PhD in Organizational Economics, MIT (2015)
• Post-doc, Oxford Centre for Technology & Global Affairs (2016-2018)
• Lead Researcher, Qatar Foundation Institute for Policy Research (2018-present)
• 34 peer-reviewed publications on workforce transitions in resource economies
• Co-author: "The Gulf Transition: Evidence from Failed and Successful Nationalization Policies" (Nature Human Behaviour, 2023)

EXPERTISE:
• Meta-analysis of nationalization policy outcomes across 47 countries (1990-2024)
• Systematic review of education-to-employment pipeline interventions
• Causal inference methods for policy evaluation (RCT design, diff-in-diff, synthetic controls)
• Academic literature synthesis and evidence grading (GRADE methodology)

ANALYTICAL FRAMEWORK:
1. Evidence Base Assessment: Grade quality of available research (high/moderate/low/very low)
2. Precedent Analysis: Document what worked/failed in similar contexts (Singapore, UAE, Saudi, Oman)
3. Theoretical Grounding: Map relevant economic/sociological theories
4. Knowledge Gaps: Expose unanswered questions and data voids
5. Research-Backed Recommendations: Only endorse actions with published support

CRITICAL STANCE:
"I ground recommendations in published evidence, not assumptions. If the literature is silent or contradictory, I say so explicitly rather than speculating."

═══════════════════════════════════════════════════
"""

STRUCTURED_OUTPUT_TEMPLATE = """
PROVIDE YOUR ANALYSIS IN THIS EXACT FORMAT:

## 🔬 RESEARCH SCIENTIST ANALYSIS
**Analyst:** Senior Research Scientist

### 1. EVIDENCE BASE QUALITY ASSESSMENT

**Available Research:**
[List relevant studies from Semantic Scholar extraction with quality grades]

**Evidence Quality (GRADE):**
- High quality: [What we know with confidence from RCTs/strong observational studies]
- Moderate quality: [What cohort studies suggest but with limitations]
- Low quality: [What weak observational data indicates]
- Very low quality / No evidence: [Critical gaps where we're guessing]

### 2. PRECEDENT ANALYSIS

**Successful Cases:**
**[Country / Program (Years)]:**
- Intervention: [Specific policy details]
- Outcome: [Measured results from peer-reviewed studies]
- Applicability to Qatar: [Why similar/different context]
- Citation: [Actual academic source]

**Failed Cases:**
**[Country / Program (Years)]:**
- Why it failed: [Root causes from academic analysis]
- Warning signs: [Early indicators that were missed]
- Relevance: [What Qatar should avoid]

### 3. THEORETICAL FRAMEWORKS

**Applicable Theories:**
- Human Capital Theory: [How it applies]
- Skill-Biased Technological Change: [Implications for automation risk]
- [Other relevant theories]

**Theory-Driven Predictions:**
[What these frameworks predict under different scenarios]

### 4. CRITICAL KNOWLEDGE GAPS

**What We DON'T Know (Research Gaps):**
1. [Specific empirical question with no good studies]
2. [Another critical gap]
3. [Another gap]

**Impact of Gaps:**
[How these unknowns affect recommendation confidence]

### 5. RESEARCH-BACKED RECOMMENDATIONS

**Strong Evidence Supports:**
✅ [Recommendation backed by multiple high-quality studies]
   • Evidence: [Citations]
   • Effect size: [Quantified impact]
   • Confidence: HIGH

**Moderate Evidence Suggests:**
⚠️ [Recommendation with limited evidence]
   • Evidence: [Citations + caveats]
   • Confidence: MODERATE

**No Evidence / Speculative:**
❌ [What remains conjecture]
   • Why speculative: [Explain the gap]
   • Confidence: LOW - EXPERT JUDGMENT ONLY

### 6. OVERALL CONFIDENCE ASSESSMENT
**Research-Backed Confidence: [X]%**

**Breakdown:**
- Evidence base quality: [X]%
- Precedent applicability: [X]%
- Theoretical consensus: [X]%

═══════════════════════════════════════════════════
"""


async def analyze(query: str, extracted_facts: List[Dict[str, Any]], llm_client) -> Dict[str, Any]:
    """Generate research-grade synthesis grounded in academic evidence."""

    facts_formatted = format_extracted_facts(extracted_facts)
    papers = [f for f in extracted_facts if "Semantic Scholar" in f.get("source", "")]
    papers_text = "\n".join([
        f"• {p.get('value', '')} (confidence: {p.get('confidence', 0.7):.0%})"
        for p in papers
        if p.get("value")
    ]) or "No academic papers in extraction"

    prompt = f"""
{RESEARCH_SCIENTIST_PERSONA}

{ANTI_FABRICATION_RULES}

{facts_formatted}

ACADEMIC PAPERS AVAILABLE:
{papers_text}

MINISTERIAL QUERY:
{query}

{STRUCTURED_OUTPUT_TEMPLATE}

NOW PROVIDE YOUR RESEARCH-GROUNDED ANALYSIS:
"""

    try:
        response = await llm_client.ainvoke(prompt)

        if (
            "Per extraction:" not in response
            and "NOT IN DATA" not in response
            and "No academic papers" not in response
        ):
            response = (
                "⚠️ ANALYSIS REJECTED - No citations found.\n\n" + response
            )

        # Extract metadata (using similar logic to other agents)
        from qnwis.agents.base import (
            extract_citations_from_narrative,
            extract_data_gaps,
            extract_assumptions,
            extract_usage_tokens,
            resolve_response_model
        )
        from datetime import datetime
        
        citations = extract_citations_from_narrative(response, extracted_facts)
        data_gaps = extract_data_gaps(response)
        assumptions = extract_assumptions(response)
        facts_used = sorted({citation["metric"] for citation in citations})
        confidence = extract_confidence_from_response(response)
        tokens_in, tokens_out = extract_usage_tokens(response)
        model_name = resolve_response_model(response, llm_client)
        
        return {
            "agent_name": "research_scientist",
            "narrative": response,
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

    except Exception as exc:  # pragma: no cover - defensive programming
        from datetime import datetime
        return {
            "agent_name": "research_scientist",
            "narrative": f"ERROR: {exc}",
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
    """Extract numerical confidence from structured output."""
    import re

    patterns = [
        r"Research-Backed Confidence:\s*(\d+)%",
        r"Overall Confidence:\s*(\d+)%",
        r"Confidence:\s*(\d+)%",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return min(float(match.group(1)) / 100.0, 1.0)

    if "⚠️ ANALYSIS REJECTED" in response:
        return 0.0

    has_citations = "Per extraction:" in response or "Citation" in response
    has_evidence_sections = "Evidence Quality" in response or "Strong Evidence" in response

    if has_citations and has_evidence_sections:
        return 0.75
    if has_citations:
        return 0.6
    return 0.4


class ResearchScientistAgent:  # pragma: no cover - legacy shim
    """Compatibility shim to prevent legacy imports from breaking."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "ResearchScientistAgent class has been replaced. "
            "Use qnwis.agents.research_scientist.analyze(...) instead."
        )
