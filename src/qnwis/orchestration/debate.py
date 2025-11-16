"""
Multi-agent debate orchestration helpers.
"""

from __future__ import annotations

from typing import Dict, Any


LLMWorkflowState = Dict[str, Any]


async def multi_agent_debate(state: LLMWorkflowState, llm_client) -> str:
    """
    Three-phase debate: Positions → Cross-Examination → Synthesis.
    """
    # Phase 1 handled upstream (agent analyses already in state)

    labour_challenges_financial = await llm_client.ainvoke(
        f"""
You are Dr. Fatima Al-Mansoori (Labour Economist).

The Financial Economist (Dr. Al-Khater) just provided this GDP impact analysis:
{state.get('financial_analysis', '')[:1000]}

YOUR TASK: Identify ONE questionable assumption or gap in their economic modeling.

RESPOND:
**MY CHALLENGE:**
[Your specific concern]

**WHY IT MATTERS:**
[Impact on recommendation]

**SUPPORTING EVIDENCE:**
[Cite extraction or explain logic]
"""
    )

    financial_challenges_market = await llm_client.ainvoke(
        f"""
You are Dr. Mohammed Al-Khater (Financial Economist).

The Market Economist (Dr. Al-Said) provided this competitive analysis:
{state.get('market_analysis', '')[:1000]}

YOUR TASK: Challenge their regional competition assumptions.

RESPOND IN SAME FORMAT AS ABOVE.
"""
    )

    synthesis_prompt = f"""
You are the DEBATE MODERATOR synthesizing a 4-agent expert council.

AGENT POSITIONS:

**LABOUR ECONOMIST (Dr. Al-Mansoori):**
{state.get('labour_analysis', '')}

**FINANCIAL ECONOMIST (Dr. Al-Khater):**
{state.get('financial_analysis', '')}

**MARKET ECONOMIST (Dr. Al-Said):**
{state.get('market_analysis', '')}

**OPERATIONS EXPERT (Eng. Al-Dosari):**
{state.get('operations_analysis', '')}

CROSS-EXAMINATION:
{labour_challenges_financial}
{financial_challenges_market}

SYNTHESIZE INTO:

## 💬 MULTI-AGENT DEBATE SYNTHESIS

### Consensus Points
✅ [What all 4 agents agree on - cite their analyses]

### Key Contradictions
**CONTRADICTION 1:** [Topic]
- Agent X position: [summary with confidence]
- Agent Y position: [contradicting view with confidence]
- Evidence favors: [which view is better supported by extracted facts]

### Emergent Insights
💡 [Insights visible only through debate, not individual analyses]

### Confidence-Weighted Recommendation
[Synthesize recommendation weighted by agent confidence scores]
"""

    debate_output = await llm_client.ainvoke(synthesis_prompt)
    return debate_output
