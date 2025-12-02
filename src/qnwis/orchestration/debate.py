"""
Multi-agent debate orchestration helpers.

The orchestration workflow uses these utilities to run a bounded turn-based
debate and to detect when the conversation has converged.

ENHANCED: Now includes cross-scenario quantitative context from Engine B
so agents reference actual computed numbers in their arguments.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from ..config.settings import DEBATE_CONFIGS
from .cross_scenario import (
    generate_cross_scenario_table,
    extract_robustness_summary,
    build_quantitative_context_for_agents,
)

logger = logging.getLogger(__name__)


async def multi_agent_debate(
    state: Dict[str, Any],
    llm_client: Any,
    *,
    complexity: str | None = None,
) -> Dict[str, Any]:
    """
    Conduct a structured debate and return its transcript and summary.

    The debate stops when either:
        - The maximum configured turns is reached
        - `detect_debate_convergence` signals convergence
    """
    config = DEBATE_CONFIGS.get(
        (complexity or state.get("classification", {}).get("complexity", "medium")).lower(),
        DEBATE_CONFIGS["medium"],
    )
    max_turns = config["max_turns"]
    check_interval = max(config.get("convergence_check_interval", 5), 1)

    debate_history: list[dict[str, Any]] = []
    convergence_result: dict[str, Any] = {"converged": False}

    for turn in range(1, max_turns + 1):
        prompt = _build_debate_prompt(state, debate_history, turn)
        try:
            response = await llm_client.ainvoke(prompt)
        except Exception as exc:  # pragma: no cover - defensive guard for llm errors
            logger.exception("Debate LLM call failed on turn %d", turn)
            debate_history.append({"agent": "moderator", "content": f"LLM error: {exc}"})
            break

        debate_history.append(
            {
                "agent": f"debater_{(turn % 4) + 1}",
                "content": response if isinstance(response, str) else str(response),
            }
        )

        if turn >= 10 and turn % check_interval == 0:
            convergence_result = detect_debate_convergence(debate_history)
            if convergence_result.get("converged"):
                break

    summary = "\n".join(entry["content"] for entry in debate_history[-2:]) if debate_history else ""
    return {
        "history": debate_history,
        "convergence": convergence_result,
        "total_turns": len(debate_history),
        "summary": summary,
    }


def _build_debate_prompt(
    state: Dict[str, Any],
    debate_history: List[Dict[str, Any]],
    turn: int,
) -> str:
    """
    Construct a deterministic prompt for the given turn.
    
    ENHANCED: Includes cross-scenario quantitative context from Engine B
    so agents must reference actual computed numbers.
    """
    topic = state.get("question", state.get("query", "the policy question at hand"))
    history_snippet = "\n".join(
        f"Turn {idx + 1}: {entry['content'][:400]}"
        for idx, entry in enumerate(debate_history[-4:])
    )
    
    # Get quantitative context from Engine B results
    quantitative_context = ""
    engine_b_results = state.get("engine_b_results", {})
    engine_b_aggregate = state.get("engine_b_aggregate", {})
    cross_scenario_table = state.get("cross_scenario_table", "")
    
    if cross_scenario_table:
        quantitative_context = f"""
## QUANTITATIVE CONTEXT (from Engine B)
{cross_scenario_table}

**You MUST reference these numbers in your arguments.**
"""
    elif engine_b_results or engine_b_aggregate:
        # Build context from aggregate results
        quantitative_context = build_quantitative_context_for_debate(engine_b_results or engine_b_aggregate)
    
    return (
        "You are participating in a ministerial debate.\n\n"
        f"**Question:** {topic}\n\n"
        f"{quantitative_context}\n"
        "Summarize the strongest remaining argument and cite concrete data.\n\n"
        f"**Recent turns:**\n{history_snippet}\n\n"
        f"**Respond for turn {turn} with:**\n"
        "1. Position (with specific numbers from the data above)\n"
        "2. Evidence (with citations to computed results)\n"
        "3. Counterpoint you are addressing\n"
    )


def build_quantitative_context_for_debate(engine_b_results: Dict[str, Any]) -> str:
    """
    Build quantitative context string for debate prompts.
    
    Args:
        engine_b_results: Engine B results (either per-scenario or aggregate)
    
    Returns:
        Formatted context string with cross-scenario data
    """
    if not engine_b_results:
        return ""
    
    try:
        # Try to build cross-scenario table
        cross_table = generate_cross_scenario_table(engine_b_results)
        robustness = extract_robustness_summary(engine_b_results)
        
        context = f"""
## QUANTITATIVE CONTEXT (Engine B Computed Results)

{cross_table}

### Key Metrics:
- **Robustness:** {robustness.get('robustness_ratio', 'N/A')} scenarios pass
- **Top Policy Levers:** {', '.join(robustness.get('top_drivers', ['Not computed']))}

**Your arguments MUST reference these computed numbers, not estimates.**
"""
        return context
    except Exception as e:
        logger.warning(f"Could not build quantitative context: {e}")
        return ""


def detect_debate_convergence(debate_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply conservative convergence heuristics for ministerial-grade debates.
    
    CRITICAL: These heuristics should be VERY conservative to ensure
    full debate depth is achieved. Only return "converged" when we're
    truly seeing repetition, not just polite agreement.
    
    Heuristics:
        1. Very high semantic similarity (>0.92) across last 8 turns
        2. No contradictions in last 5 turns AND past 80% of expected depth
        3. Every agent has spoken 5+ times AND past 75% of expected depth
    """
    # Need substantial history before checking convergence
    if len(debate_history) < 20:
        return {"converged": False, "reason": "insufficient_turns"}

    recent_turns = debate_history[-8:]

    # Heuristic 1: VERY high semantic similarity (agents repeating verbatim)
    similarity_result = _semantic_similarity(recent_turns)
    if similarity_result is not None and similarity_result > 0.92:  # Increased from 0.85
        return {
            "converged": True,
            "reason": "high_repetition",
            "similarity_score": float(similarity_result),
        }

    # Heuristic 2: No new contradictions - but only after substantial debate
    # DISABLED for legendary debates - we want full depth
    # recent_contradictions = count_new_contradictions(debate_history[-5:])
    # if recent_contradictions == 0 and len(debate_history) > 100:  # Increased from 10
    #     return {"converged": True, "reason": "no_new_contradictions"}

    # Heuristic 3: All agents have spoken extensively
    agent_counts: dict[str, int] = {}
    for turn in debate_history:
        agent = turn.get("agent")
        if agent:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

    # Only converge if all agents have spoken 5+ times AND we have 75+ turns
    if agent_counts and min(agent_counts.values()) >= 5 and len(debate_history) >= 75:
        return {
            "converged": True,
            "reason": "sufficient_coverage",
            "agent_participation": agent_counts,
        }

    return {"converged": False, "reason": "ongoing"}


def _semantic_similarity(recent_turns: List[Dict[str, Any]]) -> float | None:
    """Calculate cosine similarity between consecutive turns if the model is available."""
    texts = [turn.get("content") or turn.get("message") for turn in recent_turns]
    texts = [text for text in texts if text]
    if len(texts) < 2:
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:  # pragma: no cover - optional dependency
        logger.warning("sentence-transformers not available; skipping semantic similarity.")
        return None

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts)
    except Exception as e:
        logger.warning(f"Failed to load SentenceTransformer model: {e}")
        return None
    similarities = []
    for idx in range(len(embeddings) - 1):
        a = embeddings[idx]
        b = embeddings[idx + 1]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            continue
        similarities.append(float(np.dot(a, b) / denom))

    if not similarities:
        return None
    return float(np.mean(similarities))


def count_new_contradictions(recent_turns: List[Dict[str, Any]]) -> int:
    """Simple keyword-based contradiction detection."""
    keywords = [
        "however",
        "but",
        "disagree",
        "challenge",
        "incorrect",
        "contrary to",
        "on the other hand",
        "alternatively",
    ]
    count = 0
    for turn in recent_turns:
        content = (turn.get("content") or turn.get("message") or "").lower()
        if any(keyword in content for keyword in keywords):
            count += 1
    return count

