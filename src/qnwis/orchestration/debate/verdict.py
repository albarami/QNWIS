"""Verdict extraction, consensus building, and final synthesis."""

import json
import logging
import re
from typing import Any, Dict, List

from .json_parser import robust_json_parse

logger = logging.getLogger(__name__)


class VerdictMixin:
    """Mixin providing verdict, consensus, and synthesis methods."""

    async def _phase_5_consensus_building(
        self,
        agents_map: Dict[str, Any],
        llm_client: Any,
    ) -> Dict:
        """
        Build sophisticated consensus using LLM synthesis.

        Includes confidence validation — flags agents below 65% threshold.
        """
        self.current_phase = "consensus"
        await self._emit_phase("consensus", "Synthesizing final positions")

        final_positions = []
        agent_position_texts = {}
        llm_agents = {
            name: agent for name, agent in agents_map.items()
            if hasattr(agent, 'state_final_position')
        }

        scenario_table = self._build_scenario_table_for_final_position()
        logger.info("📊 Injecting scenario table into all final position prompts")

        MAX_RETRIES = 2

        for agent_name, agent in llm_agents.items():
            if not self._can_emit_turn():
                break

            retries = 0
            final_pos = None
            validation = {'valid': False}

            while retries <= MAX_RETRIES:
                context = scenario_table
                if retries > 0:
                    context += f"\n\n{validation.get('correction_prompt', '')}"
                    logger.warning(
                        f"🔄 RETRY {retries}/{MAX_RETRIES} for {agent_name} "
                        f"- previous: {validation.get('error_type', 'unknown')}"
                    )

                final_pos = await agent.state_final_position(
                    debate_history=self.conversation_history,
                    confidence_level=True,
                    scenario_context=context,
                    question_type=getattr(self, 'question_type', 'COMPARATIVE'),
                    original_question=self.question,
                )

                validation = self._validate_agent_scenario_citation(final_pos, agent_name)

                if validation['valid']:
                    break

                if validation.get('action') == 'HARD_REJECT':
                    logger.error(f"🚨 HARD_REJECT for {agent_name}: {validation.get('error_type')}")
                    retries += 1
                elif validation.get('action') == 'SOFT_REJECT':
                    logger.warning(f"⚠️ SOFT_REJECT for {agent_name}: {validation.get('error_type')}")
                    retries += 1
                else:
                    break

            if not validation['valid'] and validation.get('error_type') == 'INVERSION':
                logger.error(
                    f"🚨 {agent_name} failed validation after {MAX_RETRIES} retries "
                    f"- forcing correction"
                )
                final_pos += (
                    f"\n\n⚠️ VALIDATION OVERRIDE: This agent's scenario citations were corrected.\n"
                    f"Actual scenario results: {validation.get('actual_winner')} at "
                    f"{validation.get('actual_winner_rate', 0):.1f}%,\n"
                    f"{validation.get('actual_loser')} at "
                    f"{validation.get('actual_loser_rate', 0):.1f}%.\n"
                )

            await self._emit_turn(agent_name, "final_position", final_pos)

            final_positions.append({
                "agent": agent_name,
                "position": final_pos,
                "citation_valid": validation['valid'],
                "retries": retries,
            })
            agent_position_texts[agent_name] = final_pos

        low_confidence_agents = self._check_low_confidence_agents(
            agent_position_texts, threshold=0.65
        )

        positions_text = "\n\n".join([
            f"{p['agent']}: {p['position']}" for p in final_positions
        ])

        confidence_warning = ""
        if low_confidence_agents:
            warning_list = "\n".join([a["message"] for a in low_confidence_agents])
            confidence_warning = (
                f"\n\n⚠️ LOW CONFIDENCE WARNING:\n"
                f"{len(low_confidence_agents)} agent(s) have confidence below 40% threshold:\n"
                f"{warning_list}\n\n"
                f"These recommendations require additional data validation before ministerial action.\n"
            )

        synthesis_prompt = f"""After {self.turn_counter} turns of debate, synthesize the final consensus.

ORIGINAL QUESTION: {self.question[:500] if self.question else 'Unknown'}

Final positions from all agents:
{positions_text}
{confidence_warning}

REQUIRED OUTPUT FORMAT (as JSON):
{{
  "direct_answer": "Your SPECIFIC answer to the original question",
  "quantified_assessment": {{
    "metric_type": "probability/impact/risk/confidence/score",
    "value": "X% or HIGH/MEDIUM/LOW or numeric score",
    "reasoning": "Evidence-based explanation"
  }},
  "key_findings": ["Finding 1", "Finding 2", "..."],
  "areas_of_consensus": ["..."],
  "remaining_disagreements": ["..."],
  "confidence_level": "X%",
  "recommendation": "Clear, actionable recommendation",
  "risks_and_mitigations": ["Risk 1: Mitigation", "..."],
  "next_steps": ["Action 1", "Action 2", "..."]
}}

Format as structured JSON."""

        consensus = await llm_client.generate_with_routing(
            prompt=synthesis_prompt,
            task_type="debate",
            temperature=0.2,
            max_tokens=1500,
        )

        consensus_data = robust_json_parse(consensus, default=None)

        if consensus_data is None:
            logger.warning("Could not parse consensus JSON, creating structured fallback")
            consensus_data = {
                "consensus_reached": "partial" if "consensus" in consensus.lower() else "none",
                "areas_of_agreement": [],
                "areas_of_disagreement": [],
                "confidence": 0.5,
                "recommendation": "Further analysis required",
                "raw_synthesis": consensus[:2000] if consensus else "No synthesis generated",
            }

        await self._emit_turn(
            "Moderator", "consensus_synthesis", json.dumps(consensus_data, indent=2)
        )

        return consensus_data

    async def _phase_6_final_synthesis(
        self,
        conversation_history: List[Dict],
        llm_client: Any,
    ) -> str:
        """Final synthesis of the entire debate."""
        await self._emit_phase("final_synthesis", "Generating final report")

        full_history_text = self._format_history(conversation_history)

        prompt = f"""Generate a comprehensive executive summary of the debate.

ORIGINAL QUESTION: {self.question[:500] if self.question else 'Unknown'}

Debate History ({len(conversation_history)} turns):
{full_history_text[:50000]}

CRITICAL REQUIREMENTS:
1. Your FIRST paragraph must DIRECTLY ANSWER the original question
2. Provide quantified metrics relevant to the question (probability, impact, risk, score)
3. Base conclusions on evidence discussed in the debate
4. Give actionable recommendations

The report should rival a top-tier consulting firm's output.
Include:
- Executive Summary with CLEAR VERDICT on the original question
- Quantified Assessment (appropriate to the question type)
- Key Findings from the Debate
- Evidence-Based Recommendations
- Risk Assessment
- Confidence Level
- Decision (GO/NO-GO/CONDITIONAL) or Clear Conclusion"""

        synthesis_text = await llm_client.generate_with_routing(
            prompt=prompt,
            task_type="debate",
            temperature=0.3,
            max_tokens=3000,
        )

        confidence_flags = self._flag_low_confidence_recommendations(conversation_history)

        if confidence_flags:
            synthesis_text += "\n\n## ⚠️ DATA QUALITY WARNINGS\n\n"
            for flag in confidence_flags:
                synthesis_text += f"- **{flag['agent']}**: {flag['message']}\n"
            synthesis_text += (
                "\n**RECOMMENDATION:** Commission comprehensive data audit "
                "before policy implementation.\n"
            )

        return synthesis_text

    async def _synthesize_resolution_llm(
        self,
        contradiction: Dict,
        debate_turns: List[Dict],
        consensus_reached: bool,
    ) -> Dict:
        """Use LLM to synthesize resolution from debate."""
        history_text = "\n".join([
            f"{turn['agent']} ({turn['type']}): {turn['message'][:200]}..."
            for turn in debate_turns
        ])

        prompt = f"""Synthesize the resolution of this debate.

ORIGINAL CONTRADICTION:
- {contradiction.get('agent1_name')}: {contradiction.get('agent1_value_str')}
- {contradiction.get('agent2_name')}: {contradiction.get('agent2_value_str')}

DEBATE HISTORY ({len(debate_turns)} turns):
{history_text}

Consensus reached: {consensus_reached}

Provide resolution:
1. What was resolved?
2. Which agent(s) were correct?
3. What's the recommended value/action?
4. Confidence (0-1)

Format as JSON:
{{
  "resolution": "agent1_correct|agent2_correct|both_valid|neither_valid",
  "explanation": "detailed explanation",
  "recommended_value": value or null,
  "recommended_citation": "citation" or null,
  "confidence": 0.0-1.0,
  "action": "use_agent1|use_agent2|use_both|flag_for_review",
  "consensus_reached": true/false
}}
"""

        try:
            response = await self.llm_client.generate_with_routing(
                prompt=prompt,
                task_type="debate",
                temperature=0.2,
                max_tokens=800,
            )

            resolution = robust_json_parse(response, default=None)

            if resolution is None:
                logger.warning("Could not parse resolution JSON, using fallback")
                resolution = {
                    "action": "inconclusive",
                    "explanation": f"Debate completed after {len(debate_turns)} turns",
                    "confidence": 0.5,
                }

            resolution["debate_turns_count"] = len(debate_turns)

            action = resolution.get('action', 'unknown')
            explanation = resolution.get('explanation', 'No explanation')[:100]
            logger.info(f"Resolution synthesized: {action} - {explanation}...")
            return resolution

        except Exception as e:
            logger.error(f"Failed to synthesize resolution: {e}")
            return {
                "resolution": "both_valid" if consensus_reached else "neither_valid",
                "explanation": (
                    f"Debate concluded after {len(debate_turns)} turns. "
                    + ("Consensus reached." if consensus_reached else "No clear consensus.")
                ),
                "recommended_value": None,
                "recommended_citation": None,
                "confidence": 0.6 if consensus_reached else 0.4,
                "action": "use_both" if consensus_reached else "flag_for_review",
                "consensus_reached": consensus_reached,
                "debate_turns_count": len(debate_turns),
                "error": str(e),
            }

    def _extract_scenario_rate(self, scenario_result: Dict[str, Any]) -> float:
        """Extract success rate from a scenario result (domain-agnostic)."""
        if scenario_result is None:
            return 0.0

        engine_b = scenario_result.get('engine_b_results') or {}
        monte_carlo = engine_b.get('monte_carlo') or scenario_result.get('monte_carlo') or {}

        if not isinstance(monte_carlo, dict):
            monte_carlo = {}

        rate = monte_carlo.get('success_rate')
        if rate is not None:
            return float(rate) * 100 if rate <= 1 else float(rate)

        rate = scenario_result.get('success_rate')
        if rate is not None:
            return float(rate) * 100 if rate <= 1 else float(rate)

        rate = scenario_result.get('confidence')
        if rate is not None:
            return float(rate) * 100 if rate <= 1 else float(rate)

        return 0.0

    def _build_scenario_anchor(self, phase: str = "general") -> str:
        """
        Build PERSISTENT scenario anchor to inject at EVERY phase.

        Fully domain and question-type agnostic: works for comparative, single
        option, risk assessment, optimal rate, multiple options, open-ended.
        """
        if not self.scenario_results:
            return ""

        scenarios_sorted = []
        for sr in self.scenario_results:
            name = sr.get('scenario', {}).get('name', sr.get('scenario_name', 'Unknown'))
            rate = self._extract_scenario_rate(sr)
            scenarios_sorted.append({'name': name, 'rate': rate})

        scenarios_sorted.sort(key=lambda x: x['rate'], reverse=True)

        if not scenarios_sorted:
            return ""

        best = scenarios_sorted[0]
        worst = scenarios_sorted[-1]
        gap = best['rate'] - worst['rate'] if len(scenarios_sorted) > 1 else 0

        scenario_rows = []
        for i, s in enumerate(scenarios_sorted[:6], 1):
            marker = "🏆" if i == 1 else "  "
            scenario_rows.append(f"║  {marker} {i}. {s['name'][:35]:35} │ {s['rate']:5.1f}% ║")

        rows_text = "\n".join(scenario_rows)

        anchor = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  🎯 SCENARIO STRESS-TEST RESULTS — GROUND TRUTH                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  These are the actual results from Monte Carlo simulation:                    ║
║                                                                               ║
{rows_text}
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  📊 SUMMARY:                                                                  ║
║     Best:  {best['name'][:30]:30} at {best['rate']:.1f}%                      ║
║     Worst: {worst['name'][:30]:30} at {worst['rate']:.1f}%                    ║
║     Gap:   {gap:.1f} percentage points                                         ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  ⚠️ RULES:                                                                    ║
║  1. DO NOT cite percentages that don't appear in this table                   ║
║  2. Your recommendation should align with scenario evidence                   ║
║  3. If you disagree with scenarios, state EXPLICIT quantified reasons         ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

        if phase == "edge_case":
            anchor += (
                "\n⚠️ EDGE CASE WARNING:\n"
                "You are about to analyze stress scenarios.\n"
                "Stress scenarios may show lower success rates.\n"
                "DO NOT confuse stress-test rates with the primary scenario rates above.\n"
            )
        elif phase == "final":
            anchor += (
                f"\n🔴 FINAL POSITION RULES:\n\n"
                f"1. Your cited success rates MUST match the numbers in the table above\n"
                f"2. DO NOT invent percentages\n"
                f"3. The best-performing scenario is: {best['name'][:40]} at {best['rate']:.1f}%\n"
                f"4. Your recommendation should be grounded in this evidence\n"
            )

        return anchor

    def _build_scenario_table_for_final_position(self) -> str:
        """Backward compatibility wrapper."""
        return self._build_scenario_anchor(phase="final")

    def _validate_agent_scenario_citation(
        self, agent_response: str, agent_name: str = ""
    ) -> Dict[str, Any]:
        """
        Validate that agent cites ACTUAL scenario numbers, not fabricated ones.

        Fully question-type agnostic: simply checks that cited percentages
        exist in actual scenario results.
        """
        if not self.scenario_results:
            return {'valid': True, 'note': 'No scenarios to validate against', 'action': 'ACCEPT'}

        actual_rates = []
        best_scenario = None
        best_rate = 0

        for sr in self.scenario_results:
            name = sr.get('scenario', {}).get('name', sr.get('scenario_name', 'Unknown'))
            rate = self._extract_scenario_rate(sr)
            actual_rates.append({'name': name, 'rate': rate})
            if rate > best_rate:
                best_rate = rate
                best_scenario = name

        if not actual_rates:
            return {'valid': True, 'note': 'No scenario rates found', 'action': 'ACCEPT'}

        cited_pattern = r'(?:≈|~|about|around|approximately)?\s*(\d+(?:\.\d+)?)\s*%'
        cited_matches = re.findall(cited_pattern, agent_response)
        cited_percentages = [float(m) for m in cited_matches if 15 <= float(m) <= 100]

        if not cited_percentages:
            return {'valid': True, 'note': 'No scenario-range percentages cited', 'action': 'ACCEPT'}

        tolerance = 5.0
        fabricated = []

        for cited in cited_percentages:
            matches_any = any(abs(cited - s['rate']) <= tolerance for s in actual_rates)
            if not matches_any:
                fabricated.append(cited)

        if fabricated:
            actual_rates_str = ", ".join([
                f"{s['name'][:20]}={s['rate']:.1f}%"
                for s in sorted(actual_rates, key=lambda x: -x['rate'])[:5]
            ])

            logger.warning(f"⚠️ FABRICATED RATES for {agent_name}: {fabricated}")
            logger.warning(f"   Actual rates: {actual_rates_str}")

            return {
                'valid': False,
                'error_type': 'FABRICATION',
                'action': 'SOFT_REJECT',
                'fabricated_rates': fabricated,
                'actual_rates': [s['rate'] for s in actual_rates],
                'best_scenario': best_scenario,
                'best_rate': best_rate,
                'correction_prompt': (
                    f"\n⚠️ CITATION ERROR: Some percentages don't match scenario results\n\n"
                    f"Your cited rates that don't match: {fabricated}\n\n"
                    f"Actual scenario results:\n{actual_rates_str}\n\n"
                    f"Best performing: {best_scenario[:40]} at {best_rate:.1f}%\n\n"
                    f"Please revise your response using ONLY the actual scenario percentages.\n"
                ),
            }

        return {'valid': True, 'action': 'ACCEPT', 'note': 'All citations match scenarios'}

    def _format_history(self, history: list) -> str:
        """Format conversation history for prompts."""
        lines = []
        for turn in history:
            agent = turn.get("agent", "Unknown")
            message = turn.get("message", "")
            lines.append(f"{agent}: {message[:200]}...")
        return "\n".join(lines)
