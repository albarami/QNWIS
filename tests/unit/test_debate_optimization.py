import pytest

from src.qnwis.orchestration.debate import count_new_contradictions, detect_debate_convergence


def test_debate_convergence_on_similarity(monkeypatch):
    history = [{"agent": "A", "content": f"Repeated point {i}"} for i in range(5)]

    # Monkeypatch semantic similarity to bypass model loading
    monkeypatch.setattr("src.qnwis.orchestration.debate._semantic_similarity", lambda turns: 0.9)

    result = detect_debate_convergence(history)
    assert result["converged"]
    assert result["reason"] == "high_repetition"


def test_contradiction_counter():
    turns = [
        {"message": "However, data disagrees"},
        {"message": "All good"},
        {"message": "On the other hand, we should wait"},
    ]
    assert count_new_contradictions(turns) == 2
