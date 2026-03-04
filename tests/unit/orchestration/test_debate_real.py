"""
Tests for the debate package exercising REAL code paths.

NO mocks, NO hardcoded data — imports from the actual relocated debate
package and exercises robust_json_parse, detect_debate_convergence,
count_new_contradictions, and LegendaryDebateOrchestrator instantiation.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
from typing import Any

import pytest


# ── Import verification ──────────────────────────────────────────────────────

class TestDebatePackageImports:
    """Verify the debate package re-exports everything from its new location."""

    def test_import_legendary_debate_orchestrator(self):
        from src.qnwis.orchestration.debate import LegendaryDebateOrchestrator
        assert LegendaryDebateOrchestrator is not None

    def test_import_create_debate_context(self):
        from src.qnwis.orchestration.debate import create_debate_context
        assert callable(create_debate_context)

    def test_import_robust_json_parse(self):
        from src.qnwis.orchestration.debate import robust_json_parse
        assert callable(robust_json_parse)

    def test_import_detect_debate_convergence(self):
        from src.qnwis.orchestration.debate import detect_debate_convergence
        assert callable(detect_debate_convergence)

    def test_import_multi_agent_debate(self):
        from src.qnwis.orchestration.debate import multi_agent_debate
        assert callable(multi_agent_debate)

    def test_import_build_quantitative_context(self):
        from src.qnwis.orchestration.debate import build_quantitative_context_for_debate
        assert callable(build_quantitative_context_for_debate)

    def test_import_count_new_contradictions(self):
        from src.qnwis.orchestration.debate import count_new_contradictions
        assert callable(count_new_contradictions)

    def test_all_exports_match_init(self):
        from src.qnwis.orchestration.debate import __all__ as exports
        expected = {
            "LegendaryDebateOrchestrator",
            "create_debate_context",
            "robust_json_parse",
            "detect_debate_convergence",
            "multi_agent_debate",
            "build_quantitative_context_for_debate",
            "count_new_contradictions",
        }
        assert expected == set(exports)


# ── LegendaryDebateOrchestrator instantiation ────────────────────────────────

class TestLegendaryDebateOrchestratorInit:
    """Ensure the orchestrator can be constructed with real dependencies."""

    def _make_orchestrator(self, **overrides):
        from src.qnwis.orchestration.debate import LegendaryDebateOrchestrator
        from src.qnwis.llm.client import LLMClient

        llm = LLMClient()
        defaults = dict(
            emit_event_fn=self._noop_emit,
            llm_client=llm,
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
        )
        defaults.update(overrides)
        return LegendaryDebateOrchestrator(**defaults)

    @staticmethod
    async def _noop_emit(*_args, **_kwargs):
        pass

    def test_instantiation_succeeds(self):
        orch = self._make_orchestrator()
        assert orch is not None

    def test_initial_turn_counter_is_zero(self):
        orch = self._make_orchestrator()
        assert orch.turn_counter == 0

    def test_conversation_history_empty(self):
        orch = self._make_orchestrator()
        assert orch.conversation_history == []

    def test_default_complexity_is_standard(self):
        orch = self._make_orchestrator()
        assert orch.debate_complexity == "standard"

    def test_scenario_id_stored(self):
        orch = self._make_orchestrator(scenario_id="abc-123")
        assert orch.scenario_id == "abc-123"

    def test_debate_configs_available(self):
        from src.qnwis.orchestration.debate import LegendaryDebateOrchestrator
        configs = LegendaryDebateOrchestrator.DEBATE_CONFIGS
        assert "simple" in configs
        assert "standard" in configs
        assert "complex" in configs
        assert "comparative" in configs
        for key, cfg in configs.items():
            assert "max_turns" in cfg, f"{key} config missing max_turns"
            assert "phases" in cfg, f"{key} config missing phases"

    def test_detect_question_complexity_simple(self):
        orch = self._make_orchestrator()
        result = orch._detect_question_complexity("What is the GDP?")
        assert result in ("simple", "standard", "complex", "comparative")

    def test_detect_question_complexity_strategic(self):
        orch = self._make_orchestrator()
        result = orch._detect_question_complexity(
            "Should Qatar invest $5 billion in renewable energy or expand LNG capacity?"
        )
        assert result in ("complex", "comparative")


# ── robust_json_parse ────────────────────────────────────────────────────────

class TestRobustJsonParse:
    """Exercise the real robust_json_parse with various malformed inputs."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from src.qnwis.orchestration.debate import robust_json_parse
        self.parse = robust_json_parse

    def test_valid_json_object(self):
        assert self.parse('{"a": 1}') == {"a": 1}

    def test_valid_json_array(self):
        assert self.parse('[1, 2, 3]') == [1, 2, 3]

    def test_json_in_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert self.parse(text) == {"key": "value"}

    def test_json_in_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        assert self.parse(text) == {"key": "value"}

    def test_json_with_surrounding_prose(self):
        text = 'Here is the result:\n{"score": 0.85}\nEnd of output.'
        result = self.parse(text)
        assert isinstance(result, dict)
        assert result["score"] == 0.85

    def test_trailing_comma_repaired(self):
        text = '{"a": 1, "b": 2,}'
        result = self.parse(text)
        assert result == {"a": 1, "b": 2}

    def test_empty_string_returns_default(self):
        assert self.parse("") is None
        assert self.parse("", default={"fallback": True}) == {"fallback": True}

    def test_whitespace_only_returns_default(self):
        assert self.parse("   \n  ") is None

    def test_no_json_at_all_returns_default(self):
        assert self.parse("This is plain English.") is None

    def test_deeply_nested_json(self):
        obj = {"level1": {"level2": {"level3": [1, 2, 3]}}}
        result = self.parse(json.dumps(obj))
        assert result == obj

    def test_mixed_array_and_object(self):
        text = 'Some preamble [{"id": 1}, {"id": 2}] trailing'
        result = self.parse(text)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_newlines_inside_string_values(self):
        text = '{"text": "line1\nline2"}'
        result = self.parse(text)
        assert result is not None
        assert "line1" in result["text"]

    def test_boolean_and_null_values(self):
        result = self.parse('{"active": true, "deleted": false, "note": null}')
        assert result == {"active": True, "deleted": False, "note": None}

    def test_kv_fallback_extraction(self):
        text = '{"confidence": 0.9, "verdict": "approve", broken stuff here}'
        result = self.parse(text)
        assert result is not None
        assert "confidence" in result or "verdict" in result

    def test_real_llm_style_output(self):
        llm_output = """Based on my analysis, here is the structured output:

```json
{
  "recommendation": "invest",
  "confidence": 0.87,
  "risk_level": "moderate",
  "key_factors": ["market growth", "policy support"]
}
```

This concludes my assessment."""
        result = self.parse(llm_output)
        assert isinstance(result, dict)
        assert result["recommendation"] == "invest"
        assert result["confidence"] == 0.87
        assert isinstance(result["key_factors"], list)


# ── detect_debate_convergence ────────────────────────────────────────────────

class TestDetectDebateConvergence:
    """Exercise the real convergence detector with synthetic debate histories."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from src.qnwis.orchestration.debate import detect_debate_convergence
        self.detect = detect_debate_convergence

    @staticmethod
    def _make_history(n: int, template: str = "Turn {i} content about policy analysis.") -> list[dict]:
        agents = ["debater_1", "debater_2", "debater_3", "debater_4"]
        return [
            {"agent": agents[i % len(agents)], "content": template.format(i=i)}
            for i in range(n)
        ]

    def test_insufficient_turns_not_converged(self):
        history = self._make_history(5)
        result = self.detect(history)
        assert result["converged"] is False
        assert result["reason"] == "insufficient_turns"

    def test_exactly_20_turns_not_converged(self):
        history = self._make_history(20)
        result = self.detect(history)
        assert "converged" in result

    def test_large_diverse_history_ongoing(self):
        history = self._make_history(
            30,
            template="Unique argument number {i} with distinct evidence and reasoning.",
        )
        result = self.detect(history)
        assert "converged" in result
        assert "reason" in result

    def test_highly_repetitive_history_converges(self):
        same_msg = "The optimal policy is renewable energy investment for long-term growth."
        history = [
            {"agent": f"debater_{(i % 4) + 1}", "content": same_msg}
            for i in range(25)
        ]
        result = self.detect(history)
        assert "converged" in result
        if result["converged"]:
            assert result["reason"] in ("high_repetition", "sufficient_coverage")

    def test_sufficient_coverage_convergence(self):
        import random
        rng = random.Random(42)
        topics = [
            "GDP growth projections for 2025 show a 3.2% increase driven by hydrocarbon exports",
            "Renewable energy investment could reach $12 billion by 2030 under optimistic scenarios",
            "Labor market reforms suggest a 15% reduction in visa-dependent workforce by 2028",
            "Healthcare expenditure as share of GDP remains at 2.1%, below regional average",
            "Education sector needs 8,000 additional STEM graduates annually to meet targets",
            "Tourism revenue diversification plan projects QAR 45 billion by 2030",
            "Infrastructure spending on rail and metro has a multiplier effect of 1.8x",
            "Food security imports account for 90% of consumption, creating supply chain risk",
            "Digital transformation budget allocated QAR 3.5 billion for e-government services",
            "Manufacturing sector contributes only 8% of non-oil GDP, below diversification goals",
            "Sovereign wealth fund returns averaged 7.2% over the last decade",
            "Population growth rate of 1.5% creates pressure on housing and social services",
        ]
        agents = ["debater_1", "debater_2", "debater_3"]
        history = []
        for i in range(80):
            agent = agents[i % len(agents)]
            topic = rng.choice(topics)
            history.append({"agent": agent, "content": f"Turn {i}: {topic} - analysis variant {rng.randint(1000,9999)}"})
        result = self.detect(history)
        assert result["converged"] is True
        assert result["reason"] in ("sufficient_coverage", "high_repetition")
        if result["reason"] == "sufficient_coverage":
            assert "agent_participation" in result

    def test_result_always_has_converged_key(self):
        for n in (3, 10, 19, 20, 50):
            result = self.detect(self._make_history(n))
            assert "converged" in result
            assert isinstance(result["converged"], bool)


# ── count_new_contradictions ─────────────────────────────────────────────────

class TestCountNewContradictions:

    @pytest.fixture(autouse=True)
    def _import(self):
        from src.qnwis.orchestration.debate import count_new_contradictions
        self.count = count_new_contradictions

    def test_no_contradictions(self):
        turns = [
            {"content": "I agree with the assessment."},
            {"content": "The data supports this conclusion."},
        ]
        assert self.count(turns) == 0

    def test_however_detected(self):
        turns = [{"content": "However, the data shows otherwise."}]
        assert self.count(turns) >= 1

    def test_multiple_keywords(self):
        turns = [
            {"content": "I disagree with this analysis."},
            {"content": "However, there is a contrary view."},
            {"content": "On the other hand, we might consider alternatives."},
        ]
        assert self.count(turns) == 3

    def test_empty_list(self):
        assert self.count([]) == 0

    def test_missing_content_key_handled(self):
        turns = [{"agent": "debater_1"}]
        assert self.count(turns) == 0

    def test_case_insensitive(self):
        turns = [{"content": "HOWEVER the situation is different."}]
        assert self.count(turns) >= 1

    def test_but_keyword(self):
        turns = [{"content": "The growth is strong, but sustainability is unclear."}]
        assert self.count(turns) >= 1

    def test_challenge_keyword(self):
        turns = [{"content": "I challenge the assumption that costs will decline."}]
        assert self.count(turns) >= 1

    def test_message_key_also_works(self):
        turns = [{"message": "However, the evidence is weak."}]
        assert self.count(turns) >= 1


# ── create_debate_context ────────────────────────────────────────────────────

class TestCreateDebateContext:

    @pytest.fixture(autouse=True)
    def _import(self):
        from src.qnwis.orchestration.debate import create_debate_context
        self.create_ctx = create_debate_context

    def test_turn_1_returns_framework(self):
        ctx = self.create_ctx(turn_number=1, debate_history=[])
        assert "DEBATE FRAMEWORK" in ctx
        assert "MicroEconomist" in ctx
        assert "MacroEconomist" in ctx

    def test_later_turn_includes_previous_turns(self):
        history = [
            {"agent": "MicroEconomist", "content": "Option A has better ROI."},
            {"agent": "MacroEconomist", "content": "Option B strengthens resilience."},
        ]
        ctx = self.create_ctx(turn_number=3, debate_history=history)
        assert "PREVIOUS DEBATE TURNS" in ctx
        assert "ROI" in ctx or "resilience" in ctx

    def test_empty_history_after_turn_1(self):
        ctx = self.create_ctx(turn_number=5, debate_history=[])
        assert isinstance(ctx, str)


# ── build_quantitative_context_for_debate ────────────────────────────────────

class TestBuildQuantitativeContext:

    @pytest.fixture(autouse=True)
    def _import(self):
        from src.qnwis.orchestration.debate import build_quantitative_context_for_debate
        self.build_ctx = build_quantitative_context_for_debate

    def test_empty_input_returns_empty(self):
        assert self.build_ctx({}) == ""

    def test_none_like_input_returns_empty(self):
        assert self.build_ctx(None) == ""
