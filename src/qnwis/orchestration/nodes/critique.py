"""
Critique Node - Devil's Advocate Analysis.

Uses LLM to stress-test agent conclusions, identify weaknesses,
and provide constructive criticism for ministerial decision-making.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from ..state import IntelligenceState
from ...llm.client import LLMClient

logger = logging.getLogger(__name__)


async def _generate_llm_critique(
    agent_reports: List[Dict[str, Any]],
    debate_results: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Generate devil's advocate critique using LLM.
    
    Args:
        agent_reports: List of agent analysis reports
        debate_results: Results from agent debate
        query: Original ministerial query
        
    Returns:
        Structured critique results with critiques, red_flags, assessment
    """
    # Initialize LLM client using environment configuration
    provider = os.getenv("QNWIS_LLM_PROVIDER", "azure")
    model = os.getenv("QNWIS_LANGGRAPH_LLM_MODEL", "gpt-4o")
    
    llm_client = LLMClient(provider=provider, model=model)
    
    # Build conclusions from agent reports
    conclusions = []
    for report in agent_reports:
        if isinstance(report, dict):
            agent_name = report.get("agent", report.get("agent_name", "Unknown"))
            # Handle both dict and object formats
            rep = report.get("report", report)
            if isinstance(rep, dict):
                narrative = rep.get("narrative", "")
                confidence = rep.get("confidence", 0.5)
            else:
                narrative = getattr(rep, "narrative", str(rep))
                confidence = getattr(rep, "confidence", 0.5)
        else:
            # AgentReport object
            agent_name = getattr(report, "agent", "Unknown")
            narrative = getattr(report, "narrative", "")
            confidence = getattr(report, "confidence", 0.5)
        
        if narrative:
            conclusions.append(f"Agent: {agent_name}\nConfidence: {confidence:.2f}\nConclusion: {narrative[:500]}\n")
    
    if not conclusions:
        logger.warning("No agent conclusions found - attempting to extract from conversation history")
        # Try to extract from conversation history as fallback
        # This is critical for parallel mode where agent_reports may be in different format
        conversation = debate_results.get("conversation_history", [])
        for turn in conversation[-10:]:  # Last 10 turns often contain synthesis/conclusions
            if isinstance(turn, dict):
                msg = turn.get("message", "")
                agent = turn.get("agent", "Expert")
                if msg and len(msg) > 100:  # Only substantive messages
                    conclusions.append(f"Agent: {agent}\nConclusion: {msg[:500]}\n")
    
    if not conclusions:
        logger.warning("Still no conclusions - using scenario syntheses if available")
        return {
            "critiques": [{
                "agent_name": "System",
                "weakness_found": "Agent reports were not available in expected format",
                "counter_argument": "Verify data aggregation from parallel scenarios",
                "severity": "medium",
                "robustness_score": 0.5
            }],
            "red_flags": ["Agent conclusions not properly aggregated from parallel scenarios"],
            "overall_assessment": "Critique limited - agent data not in expected format. Review scenario syntheses directly.",
            "strengthened_by_critique": False,
            "confidence_adjustments": {},
            "status": "partial"
        }
    
    conclusions_text = "\n---\n".join(conclusions)
    
    # Add debate context - check BOTH locations for conversation history
    debate_context = ""
    conversation = debate_results.get("conversation_history", [])
    
    # Extract risk mentions from debate for devil's advocate
    risk_mentions = []
    for turn in conversation:
        if isinstance(turn, dict):
            msg = turn.get("message", "").lower()
            if any(w in msg for w in ["risk", "threat", "danger", "catastrophic", "failure", "tail risk"]):
                risk_mentions.append(f"Turn {turn.get('turn', '?')}: {turn.get('agent', 'Expert')}: {turn.get('message', '')[:200]}")
    
    contradictions = debate_results.get("contradictions_found", 0)
    total_turns = debate_results.get("total_turns", len(conversation))
    debate_context = f"""
DEBATE RESULTS:
- Total debate turns: {total_turns}
- Contradictions found: {contradictions}
- Consensus reached: {debate_results.get('consensus_reached', False)}
- Risk mentions in debate: {len(risk_mentions)}
{chr(10).join(risk_mentions[:5]) if risk_mentions else '(No specific risks flagged in debate)'}
"""
    
    # Build critique prompt
    critique_prompt = f"""You are a critical thinking expert acting as a devil's advocate for Qatar's Ministry of Labour.

ORIGINAL QUERY:
{query}

AGENT CONCLUSIONS:
{conclusions_text}

{debate_context}

YOUR TASK:
1. Identify potential weaknesses in the reasoning
2. Challenge assumptions that may not be warranted
3. Look for:
   - Over-generalization from limited data
   - Missing alternative explanations
   - Unwarranted confidence
   - Gaps in the logic
   - Hidden biases
   - Cherry-picked evidence
4. Propose counter-arguments or alternative interpretations
5. Rate the robustness of each conclusion (0.0-1.0)

Be constructively critical. The goal is to strengthen conclusions by finding and addressing weaknesses, not to tear them down arbitrarily.

OUTPUT FORMAT (JSON):
{{
  "critiques": [
    {{
      "agent_name": "agent name",
      "weakness_found": "description of weakness",
      "counter_argument": "alternative perspective",
      "severity": "high" | "medium" | "low",
      "robustness_score": 0.0-1.0
    }}
  ],
  "overall_assessment": "summary of overall robustness",
  "confidence_adjustments": {{
    "agent_name": adjustment_factor_0_to_1
  }},
  "red_flags": ["flag 1", "flag 2", ...],
  "strengthened_by_critique": true | false
}}

Provide at least 2-3 critiques per agent. Be thorough."""

    try:
        response = await llm_client.generate(
            prompt=critique_prompt,
            temperature=0.3,
            max_tokens=3000
        )
        
        # Parse JSON response
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        if not response_clean:
            raise ValueError("Empty response from LLM")
        
        critique = json.loads(response_clean)
        
        # Ensure all required fields exist
        critique.setdefault("critiques", [])
        critique.setdefault("red_flags", [])
        critique.setdefault("overall_assessment", "Critique completed")
        critique.setdefault("strengthened_by_critique", len(critique.get("critiques", [])) > 0)
        critique.setdefault("confidence_adjustments", {})
        critique["status"] = "complete"
        
        logger.info(
            f"LLM critique complete: {len(critique.get('critiques', []))} critiques, "
            f"{len(critique.get('red_flags', []))} red flags"
        )
        
        return critique
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse critique JSON: {e}")
        logger.error(f"Raw response: {response[:500] if response else 'None'}")
        return {
            "critiques": [{
                "agent_name": "System",
                "weakness_found": "Critique parsing failed",
                "counter_argument": "Review raw agent outputs for quality",
                "severity": "medium",
                "robustness_score": 0.5
            }],
            "red_flags": ["Critique LLM response was not valid JSON"],
            "overall_assessment": f"Critique parsing error: {str(e)}",
            "strengthened_by_critique": False,
            "confidence_adjustments": {},
            "status": "error"
        }
    except Exception as e:
        logger.error(f"LLM critique failed: {e}", exc_info=True)
        return {
            "critiques": [],
            "red_flags": [f"Critique generation failed: {str(e)}"],
            "overall_assessment": f"Critique error: {str(e)}",
            "strengthened_by_critique": False,
            "confidence_adjustments": {},
            "status": "error"
        }


def _collect_data_gaps(agent_reports: List[Dict[str, object]]) -> List[str]:
    """Aggregate all data gaps surfaced by agents."""
    gaps: List[str] = []
    for bundle in agent_reports:
        if isinstance(bundle, dict):
            report = bundle.get("report", bundle)
        else:
            report = bundle
            
        if isinstance(report, dict):
            for gap in report.get("data_gaps", []) or []:
                gaps.append(str(gap))
        elif hasattr(report, "data_gaps"):
            for gap in getattr(report, "data_gaps", []) or []:
                gaps.append(str(gap))
    return gaps


def _collect_high_risk_assumptions(agent_reports: List[Dict[str, object]]) -> List[str]:
    """Aggregate assumptions that might invalidate the recommendation."""
    assumptions: List[str] = []
    for bundle in agent_reports:
        if isinstance(bundle, dict):
            report = bundle.get("report", bundle)
        else:
            report = bundle
            
        if isinstance(report, dict):
            for assumption in report.get("assumptions", []) or []:
                assumptions.append(str(assumption))
        elif hasattr(report, "assumptions"):
            for assumption in getattr(report, "assumptions", []) or []:
                assumptions.append(str(assumption))
    return assumptions


async def critique_node_async(state: IntelligenceState) -> IntelligenceState:
    """
    Async critique node that uses LLM for devil's advocate analysis.
    
    This is the proper implementation that generates real critiques.
    """
    start_time = datetime.now(timezone.utc)
    
    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])
    
    # Emit running event
    emit_fn = state.get("emit_event_fn")
    if emit_fn:
        await emit_fn("critique", "running", {})
    
    agent_reports = state.get("agent_reports", [])
    debate_results = state.get("debate_results") or {}
    query = state.get("query", "")
    
    # CRITICAL: In parallel mode, conversation_history is in state directly
    # Merge it into debate_results so _generate_llm_critique can access it
    if not debate_results.get("conversation_history") and state.get("conversation_history"):
        debate_results = dict(debate_results)  # Copy to avoid mutating original
        debate_results["conversation_history"] = state.get("conversation_history", [])
        debate_results["total_turns"] = len(debate_results["conversation_history"])
        logger.info(f"Using aggregated conversation_history with {len(debate_results['conversation_history'])} turns")
    
    # Also check aggregate_debate_stats
    aggregate_stats = state.get("aggregate_debate_stats", {})
    if aggregate_stats:
        debate_results["total_turns"] = aggregate_stats.get("total_turns", debate_results.get("total_turns", 0))
        debate_results["total_challenges"] = aggregate_stats.get("total_challenges", 0)
        debate_results["total_consensus"] = aggregate_stats.get("total_consensus", 0)
    
    logger.info(f"Starting devil's advocate critique of {len(agent_reports)} reports, {debate_results.get('total_turns', 0)} debate turns")
    
    # Generate LLM critique
    critique_results = await _generate_llm_critique(agent_reports, debate_results, query)
    
    latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    critique_results["latency_ms"] = latency_ms
    
    # Store structured results
    state["critique_results"] = critique_results
    
    # Also create string report for backward compatibility
    critique_lines = ["Devil's advocate review:"]
    
    for critique in critique_results.get("critiques", []):
        agent = critique.get("agent_name", "Unknown")
        weakness = critique.get("weakness_found", "")
        severity = critique.get("severity", "medium")
        critique_lines.append(f"- [{severity.upper()}] {agent}: {weakness}")
    
    for flag in critique_results.get("red_flags", []):
        critique_lines.append(f"- 🚩 RED FLAG: {flag}")
    
    critique_lines.append(f"\nOverall: {critique_results.get('overall_assessment', 'Review complete')}")
    
    state["critique_report"] = "\n".join(critique_lines)
    
    # Emit complete event
    if emit_fn:
        await emit_fn(
            "critique",
            "complete",
            {
                "critiques": critique_results.get("critiques", []),
                "red_flags": critique_results.get("red_flags", []),
                "overall_assessment": critique_results.get("overall_assessment", ""),
                "strengthened_by_critique": critique_results.get("strengthened_by_critique", False),
                "num_critiques": len(critique_results.get("critiques", [])),
            },
            latency_ms
        )
    
    reasoning_chain.append(
        f"Devil's advocate critique: {len(critique_results.get('critiques', []))} critiques, "
        f"{len(critique_results.get('red_flags', []))} red flags"
    )
    nodes_executed.append("critique")
    
    # Add warnings if significant issues found
    if critique_results.get("red_flags"):
        warnings.append(f"Critique flagged {len(critique_results['red_flags'])} red flags")
    
    logger.info(f"Critique complete in {latency_ms:.0f}ms")
    
    return state


def critique_node(state: IntelligenceState) -> IntelligenceState:
    """
    Synchronous wrapper for async critique node.
    
    Uses asyncio to run the async LLM critique.
    """
    import asyncio
    
    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - create a task
        # This shouldn't happen in normal LangGraph execution
        logger.warning("critique_node called from async context - this may cause issues")
        # Fall back to simple critique
        return _simple_critique(state)
    except RuntimeError:
        # No event loop - we can run asyncio
        pass
    
    # Run the async critique
    try:
        return asyncio.run(critique_node_async(state))
    except Exception as e:
        logger.error(f"Async critique failed, falling back: {e}")
        return _simple_critique(state)


def _simple_critique(state: IntelligenceState) -> IntelligenceState:
    """
    Simple deterministic critique when LLM is unavailable.
    Still produces structured output for frontend.
    """
    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])
    
    agent_reports = state.get("agent_reports", [])
    data_gaps = _collect_data_gaps(agent_reports)
    assumptions = _collect_high_risk_assumptions(agent_reports)
    
    debate_results = state.get("debate_results") or {}
    contradiction_count = debate_results.get("contradictions_found", 0)
    data_quality = state.get("data_quality_score") or 0.0
    
    # Build structured critiques
    critiques = []
    red_flags = []
    
    if contradiction_count:
        red_flags.append(f"{contradiction_count} contradiction(s) remain unresolved")
        critiques.append({
            "agent_name": "Debate",
            "weakness_found": f"{contradiction_count} contradictions were not fully resolved",
            "counter_argument": "Human review recommended to adjudicate conflicting positions",
            "severity": "high" if contradiction_count > 2 else "medium",
            "robustness_score": max(0.3, 1.0 - (contradiction_count * 0.15))
        })
    
    if data_quality < 0.7:
        red_flags.append(f"Data quality score ({data_quality:.0%}) below threshold")
        critiques.append({
            "agent_name": "DataQuality",
            "weakness_found": f"Data quality score is {data_quality:.0%}, below 70% threshold",
            "counter_argument": "Refresh cache or fetch additional authoritative sources",
            "severity": "high" if data_quality < 0.5 else "medium",
            "robustness_score": data_quality
        })
    
    if data_gaps:
        critiques.append({
            "agent_name": "Coverage",
            "weakness_found": f"Agents reported {len(data_gaps)} data gaps",
            "counter_argument": f"Top gap: {data_gaps[0] if data_gaps else 'Unknown'}",
            "severity": "medium",
            "robustness_score": max(0.5, 1.0 - (len(data_gaps) * 0.1))
        })
    
    if assumptions:
        critiques.append({
            "agent_name": "Assumptions",
            "weakness_found": f"{len(assumptions)} key assumptions require validation",
            "counter_argument": f"Assumptions: {', '.join(assumptions[:3])}",
            "severity": "medium",
            "robustness_score": 0.6
        })
    
    # If nothing to critique, note that analysis appears sound
    if not critiques:
        critiques.append({
            "agent_name": "Review",
            "weakness_found": "No significant weaknesses detected in initial review",
            "counter_argument": "Evidence base appears sufficient for the analysis",
            "severity": "low",
            "robustness_score": 0.85
        })
    
    overall = "Analysis shows some areas requiring attention." if red_flags else "Analysis appears robust."
    
    critique_results = {
        "critiques": critiques,
        "red_flags": red_flags,
        "overall_assessment": overall,
        "strengthened_by_critique": len(red_flags) == 0,
        "confidence_adjustments": {},
        "status": "complete",
        "latency_ms": 0
    }
    
    state["critique_results"] = critique_results
    
    # String report for compatibility
    critique_lines = ["Devil's advocate review:"]
    for c in critiques:
        critique_lines.append(f"- [{c['severity'].upper()}] {c['agent_name']}: {c['weakness_found']}")
    for flag in red_flags:
        critique_lines.append(f"- 🚩 {flag}")
    
    state["critique_report"] = "\n".join(critique_lines)
    
    reasoning_chain.append(f"Critique: {len(critiques)} items, {len(red_flags)} red flags")
    nodes_executed.append("critique")
    
    if red_flags:
        warnings.append("Critique flagged outstanding concerns")
    
    return state
