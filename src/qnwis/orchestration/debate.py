"""
Multi-agent debate orchestration helpers.

The orchestration workflow uses these utilities to run a bounded turn-based
debate and to detect when the conversation has converged.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from ..config.settings import DEBATE_CONFIGS

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
    """Construct a deterministic prompt for the given turn."""
    topic = state.get("question", "the policy question at hand")
    history_snippet = "\n".join(
        f"Turn {idx + 1}: {entry['content'][:400]}"
        for idx, entry in enumerate(debate_history[-4:])
    )
    return (
        "You are moderating a ministerial debate.\n"
        f"Question: {topic}\n"
        "Summarize the strongest remaining argument and cite concrete data.\n"
        f"Recent turns:\n{history_snippet}\n"
        f"Respond for turn {turn} with:\n"
        "1. Position\n2. Evidence (with citations)\n3. Counterpoint you are addressing\n"
    )


def detect_debate_convergence(debate_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply three convergence heuristics:
        1. High semantic similarity across last five turns
        2. No contradictions in the last three turns and at least eleven total turns
        3. Every participating agent has spoken at least twice once 15 turns are reached
    """
    if len(debate_history) < 5:
        return {"converged": False, "reason": "insufficient_turns"}

    recent_turns = debate_history[-5:]

    similarity_result = _semantic_similarity(recent_turns)
    if similarity_result is not None and similarity_result > 0.85:
        return {
            "converged": True,
            "reason": "high_repetition",
            "similarity_score": float(similarity_result),
        }

    recent_contradictions = count_new_contradictions(debate_history[-3:])
    if recent_contradictions == 0 and len(debate_history) > 10:
        return {"converged": True, "reason": "no_new_contradictions"}

    agent_counts: dict[str, int] = {}
    for turn in debate_history:
        agent = turn.get("agent")
        if agent:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

    if agent_counts and min(agent_counts.values()) >= 2 and len(debate_history) >= 15:
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

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts)
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

