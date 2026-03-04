"""Orchestrates multi-turn agent debates for the QNWIS council."""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ...llm.client import LLMClient
from ._convergence import detect_debate_convergence
from ..smart_moderator import SmartModerator
from ..turn_validator import TurnValidator
from ..question_locker import QuestionLocker, create_question_lock_prompt, create_phase_reminder

from .phase_manager import PhaseManagerMixin
from .verdict import VerdictMixin
from .statistics import StatisticsMixin

logger = logging.getLogger(__name__)


def create_debate_context(turn_number: int, debate_history: List[Dict]) -> str:
    """Create debate context that highlights recent micro vs macro arguments."""
    if turn_number == 1:
        return """
# DEBATE FRAMEWORK

This analysis includes both MICROECONOMIC and MACROECONOMIC perspectives:

**MicroEconomist** focuses on:
- Project-level costs and returns
- Market efficiency and price signals
- Opportunity costs
- ROI, NPV, financial viability

**MacroEconomist** focuses on:
- National-level aggregate effects
- Strategic security and resilience
- Systemic risks and externalities
- Long-term structural transformation

**YOUR ROLE**:
- Provide your perspective through your analytical lens
- Engage with other perspectives when they challenge your analysis
- Acknowledge valid points from other analysts
- Help synthesize the tension between efficiency and strategy
"""

    recent_turns = debate_history[-3:] if len(debate_history) > 3 else debate_history
    context = "\n# PREVIOUS DEBATE TURNS:\n\n"
    for turn in recent_turns:
        agent = turn.get("agent", "Unknown")
        content = turn.get("content", "")[:500]
        context += f"**{agent}**: {content}...\n\n"

    context += "\nBuild on these perspectives. Challenge assumptions if warranted. Find synthesis where possible.\n"
    return context


class LegendaryDebateOrchestrator(PhaseManagerMixin, VerdictMixin, StatisticsMixin):
    """
    ADAPTIVE 6-phase legendary debate system.
    Adjusts depth based on question complexity.

    SIMPLE questions (factual): 25-40 turns, 3-5 minutes
    COMPLEX questions (strategic): 100-150 turns, 25-35 minutes
    """

    DEBATE_CONFIGS = {
        "simple": {
            "max_turns": 40,
            "phases": {
                "opening": 10,
                "challenge": 15,
                "edge_case": 8,
                "risk": 5,
                "consensus": 2,
            },
        },
        "standard": {
            "max_turns": 80,
            "phases": {
                "opening": 12,
                "analysis": 20,
                "challenge": 20,
                "edge_case": 15,
                "risk": 12,
                "consensus": 6,
            },
        },
        "complex": {
            "max_turns": 45,
            "phases": {
                "opening": 6,
                "analysis": 8,
                "challenge": 10,
                "edge_case": 8,
                "risk": 6,
                "consensus": 7,
            },
        },
        "comparative": {
            "max_turns": 45,
            "phases": {
                "opening": 6,
                "option_a_advocacy": 8,
                "option_b_advocacy": 8,
                "challenge": 8,
                "cross_examination": 6,
                "risk": 4,
                "consensus": 5,
            },
        },
    }

    PHASE_BUDGET_STRICT = True

    PHASE_HARD_LIMITS = {
        'opening': 6,
        'analysis': 8,
        'challenge': 10,
        'edge_case': 8,
        'risk': 6,
        'consensus': 7,
    }

    MAX_TURNS_TOTAL = 45
    MAX_TURNS_PER_PHASE = DEBATE_CONFIGS["standard"]["phases"]

    PHASE_TRANSITION_PROMPTS = {
        'OPENING_TO_ANALYSIS': (
            "═══════════════════════════════════════════════════════════════════════════════\n"
            "📌 PHASE TRANSITION: Opening → Analysis\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
            "Opening statements are complete. All agents have introduced their perspective.\n\n"
            "NEXT PHASE REQUIREMENTS:\n"
            "- Challenge specific claims with counter-evidence\n"
            "- Identify key disagreements\n"
            "- Begin quantifying trade-offs\n"
            "- Reference specific data to support or refute claims\n\n"
            "Do NOT repeat opening positions. ADVANCE the analysis toward a decision.\n"
            "═══════════════════════════════════════════════════════════════════════════════"
        ),
        'ANALYSIS_TO_DELIBERATION': (
            "═══════════════════════════════════════════════════════════════════════════════\n"
            "📌 PHASE TRANSITION: Analysis → Deliberation\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
            "Key issues have been identified. Evidence has been presented.\n\n"
            "NEXT PHASE REQUIREMENTS:\n"
            "- Synthesize areas of agreement\n"
            "- Resolve remaining disagreements with evidence\n"
            "- Begin forming a consensus recommendation\n"
            "- Quantify confidence levels\n\n"
            "Move toward a VERDICT. The minister needs a decision.\n"
            "═══════════════════════════════════════════════════════════════════════════════"
        ),
        'DELIBERATION_TO_CONSENSUS': (
            "═══════════════════════════════════════════════════════════════════════════════\n"
            "📌 PHASE TRANSITION: Deliberation → Consensus\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
            "Time to reach a conclusion.\n\n"
            "EACH AGENT MUST NOW:\n"
            "1. State their FINAL POSITION (not a summary of debate)\n"
            "2. Provide a CONCRETE RECOMMENDATION\n"
            "3. Assign a CONFIDENCE LEVEL (percentage)\n"
            "4. Note any REMAINING CONCERNS\n\n"
            "The next round will synthesize these into a ministerial recommendation.\n"
            "═══════════════════════════════════════════════════════════════════════════════"
        ),
    }

    def __init__(
        self,
        emit_event_fn: Callable,
        llm_client: LLMClient,
        on_turn_complete: Optional[Callable] = None,
        scenario_id: str = "",
        scenario_name: str = "",
    ):
        self.emit_event = emit_event_fn
        self.llm_client = llm_client
        self.on_turn_complete = on_turn_complete
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.conversation_history: List[Dict[str, Any]] = []
        self.turn_counter = 0
        self.start_time = None
        self.current_phase = None
        self.phase_turn_counters = defaultdict(int)
        self.resolutions = []
        self.agent_reports_map = {}
        self.question = ""
        self.extracted_facts: List[Dict[str, Any]] = []
        self.debate_complexity = "standard"
        self.agent_turn_counts = defaultdict(int)
        self.question_type = "COMPARATIVE"
        self._topic_drift_detected = False
        self._topic_drift_reason = ""
        self._needs_binary_reminder = False
        self._smart_moderator: Optional[SmartModerator] = None
        self._turn_validator: Optional[TurnValidator] = None
        self._question_locker: Optional[QuestionLocker] = None

    def _get_balanced_agent_order(self, agents_list: List[str]) -> List[str]:
        """Return agents ordered by fewest turns first to ensure balanced participation."""
        return sorted(agents_list, key=lambda a: self.agent_turn_counts.get(a, 0))

    def _get_engagement_prompt(self, previous_agent: str) -> str:
        """Generate engagement prompt for agents that fail validation."""
        return (
            f"═══════════════════════════════════════════════════════════════════════════════\n"
            f"MANDATORY ENGAGEMENT REQUIREMENT (FIX 5)\n"
            f"═══════════════════════════════════════════════════════════════════════════════\n\n"
            f"Your response MUST begin with ONE of these patterns:\n\n"
            f"1. \"I challenge {previous_agent}'s claim that [X] because [evidence]...\"\n"
            f"2. \"Building on {previous_agent}'s point about [X], the data shows [Y]...\"\n"
            f"3. \"I question {previous_agent}'s assumption that [X]...\"\n"
            f"4. \"While {previous_agent} correctly notes [X], they overlook [Y]...\"\n"
            f"5. \"I agree with {previous_agent} on [X], but we must also consider [Y]...\"\n\n"
            f"Responses without engagement will be REJECTED."
        )

    def _format_query_context(self) -> str:
        """Format the query and extracted facts as context to inject into agent prompts."""
        context_parts = []

        context_parts.append("=" * 60)
        context_parts.append("🔒 TOPIC LOCK - YOU MUST ONLY DISCUSS:")
        context_parts.append("=" * 60)
        context_parts.append(self.question)
        context_parts.append("")
        context_parts.append("EVERY sentence must answer: 'How does this help decide the question above?'")
        context_parts.append("")
        context_parts.append("FORBIDDEN (immediate disqualification):")
        context_parts.append("- General economic theory not specific to this question")
        context_parts.append("- Historical examples unless directly relevant to the decision at hand")
        context_parts.append("- Tangential topics not in the question")
        context_parts.append("- Meta-discussion about methodology")
        context_parts.append("- Repetition of points already made")
        context_parts.append("")

        if hasattr(self, 'calculated_results') and self.calculated_results:
            context_parts.append("=" * 60)
            context_parts.append("CALCULATED FINANCIAL RESULTS (DETERMINISTIC - DO NOT MODIFY)")
            context_parts.append("=" * 60)
            context_parts.append("")
            context_parts.append(self._format_calculated_summary())
            context_parts.append("")
            context_parts.append("⚠️ CRITICAL: Interpret these CALCULATED numbers. DO NOT generate new numbers.")
            context_parts.append("")

        if hasattr(self, 'calculation_warning') and self.calculation_warning:
            context_parts.append("⚠️ DATA CONFIDENCE WARNING:")
            context_parts.append(self.calculation_warning)
            context_parts.append("")

        question_type = getattr(self, 'question_type', 'COMPARATIVE')

        if question_type == "COMPARATIVE" and hasattr(self, 'cross_scenario_context') and self.cross_scenario_context:
            context_parts.append("=" * 60)
            context_parts.append("CROSS-SCENARIO QUANTITATIVE ANALYSIS (6 SCENARIOS)")
            context_parts.append("=" * 60)
            context_parts.append("")
            context_parts.append(self.cross_scenario_context)
            context_parts.append("")
            context_parts.append("⚠️ CRITICAL: Reference these computed scenario results in your arguments.")
            context_parts.append("⚠️ DO NOT invent success rates - use the values from the table above.")
            context_parts.append("")
            logger.info("✅ COMPARATIVE question - injected cross-scenario context")

        elif question_type in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
            context_parts.append("=" * 60)
            context_parts.append(f"📊 {question_type} ANALYSIS - DERIVE YOUR OWN PROBABILITY")
            context_parts.append("=" * 60)
            context_parts.append("")
            context_parts.append(
                f"QUESTION TYPE: {question_type}\n\n"
                f"You are analyzing a {question_type.lower()} question. This is a SINGLE-OUTCOME forecast.\n"
                f"There is NO Option A vs Option B. You are estimating ONE probability.\n\n"
                f"🚫 FORBIDDEN FORMAT (IMMEDIATE DISQUALIFICATION):\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f'✗ "Option A (strategy X) — 41% success rate, Option B (strategy Y) — 54%"\n'
                f'✗ "Scenario A vs Scenario B comparison"\n'
                f'✗ "Monte Carlo analysis shows X% vs Y%"\n'
                f"✗ Any A/B or dual-option framing\n\n"
                f"If you use Option A/B format for a {question_type} question, your response will be REJECTED.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ REQUIRED FORMAT - SINGLE PROBABILITY ESTIMATE:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"### PROBABILITY ESTIMATE\n"
                f"**Central Estimate:** [X]%\n"
                f"**Range:** [Lower]% - [Upper]%\n"
                f"**Confidence:** [High/Medium/Low]\n\n"
                f"### KEY FACTORS (ranked by impact)\n"
                f"1. [Most important factor]: [Evidence]\n"
                f"2. [Second factor]: [Evidence]\n"
                f"3. [Third factor]: [Evidence]\n\n"
                f"### REASONING\n"
                f"[Your detailed justification for the SINGLE probability estimate]\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"REMEMBER: ONE probability. NOT Option A vs Option B.\n"
            )
            context_parts.append("")
            logger.warning(f"⚠️ {question_type} question - agents will derive their own probability estimates")

        if hasattr(self, 'case_studies_context') and self.case_studies_context:
            logger.info(f"📚 INJECTING case studies: {len(self.case_studies_context)} chars")
            context_parts.append("=" * 60)
            context_parts.append("📚 COMPARATIVE CASE STUDIES (REAL DATA FROM AUTHORITATIVE SOURCES)")
            context_parts.append("=" * 60)
            context_parts.append("")
            context_parts.append(self.case_studies_context)
            context_parts.append("")
            context_parts.append("🚨 MANDATORY: You MUST cite at least ONE case study in your response!")
            context_parts.append("")

        if hasattr(self, 'agent_reports_map') and self.agent_reports_map:
            logger.info(f"🔬 INJECTING {len(self.agent_reports_map)} agent reports into debate context")
            context_parts.append("=" * 60)
            context_parts.append("🔬 ANALYST REPORTS (FROM OTHER AGENTS)")
            context_parts.append("=" * 60)
            context_parts.append("")
            context_parts.append("Reference these analyses from your colleagues:")
            context_parts.append("")

            for agent_name, report in self.agent_reports_map.items():
                if report:
                    narrative = getattr(report, 'narrative', '')
                    if narrative and len(narrative) > 50:
                        if agent_name.lower() in [
                            'researchsynthesizer', 'research', 'financial', 'market', 'operations',
                        ]:
                            max_chars = 3000
                        else:
                            max_chars = 800
                        truncated = narrative[:max_chars] + "..." if len(narrative) > max_chars else narrative
                        context_parts.append(f"### {agent_name.upper()} ANALYSIS:")
                        context_parts.append(truncated)
                        context_parts.append("")

            context_parts.append("🚨 MANDATORY: Reference at least ONE analyst finding in your argument!")
            context_parts.append("")

        if self.extracted_facts:
            context_parts.append("=" * 60)
            context_parts.append("🚨 MANDATORY DATA SOURCE - USE ONLY THESE NUMBERS 🚨")
            context_parts.append("=" * 60)
            context_parts.append("")
            context_parts.append("⛔ CRITICAL RULE: You may ONLY cite statistics from this list.")
            context_parts.append("⛔ Citing ANY number not in this list = FABRICATION = REJECTION")
            context_parts.append("⛔ If a metric you need is NOT here, write: 'NOT IN DATA'")
            context_parts.append("")

            fact_index = 1
            for fact in self.extracted_facts[:40]:
                source = fact.get("source", "Unknown")
                metric = fact.get("metric", fact.get("description", ""))
                value = fact.get("value", "")
                year = fact.get("year", "")
                if metric and value:
                    context_parts.append(
                        f"[FACT {fact_index}] {metric}: {value} | Source: {source} | Year: {year}"
                    )
                    fact_index += 1

            context_parts.append("")
            context_parts.append("=" * 60)
            context_parts.append("CITATION FORMAT (REQUIRED):")
            context_parts.append("  ✅ 'ICT employment is [FACT 3: 2.1% from LMIS]'")
            context_parts.append("  ✅ 'NOT IN DATA - cannot provide ICT national participation rate'")
            context_parts.append("  ❌ 'ICT employs 0.8% of nationals' (NO SOURCE = FABRICATION)")
            context_parts.append("=" * 60)
        else:
            context_parts.append("")
            context_parts.append("⚠️ WARNING: No extracted data available for this query.")
            context_parts.append("⚠️ You must write 'NOT IN DATA' for any statistics.")
            context_parts.append("⚠️ DO NOT fabricate numbers - provide qualitative analysis only.")

        context_parts.append("-" * 60)
        context_parts.append("Please keep your analysis focused on the specific question above.")
        context_parts.append("-" * 60)

        if self._question_locker and self._question_locker.question_type == 'comparative':
            context_parts.append("")
            context_parts.append(self._question_locker.get_question_reminder())
            context_parts.append(self._question_locker.get_comparison_requirement())

        return "\n".join(context_parts)

    def _format_calculated_summary(self) -> str:
        """Format calculated results into a summary for agent prompts."""
        if not hasattr(self, 'calculated_results') or not self.calculated_results:
            return "No calculations available."

        lines = []
        for option in self.calculated_results.get("options", []):
            metrics = option.get("metrics", {})
            lines.append(f"### {option.get('option_name', 'Option')}")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| NPV | {metrics.get('npv_formatted', 'N/A')} |")
            lines.append(f"| IRR | {metrics.get('irr_formatted', 'N/A')} |")
            lines.append(f"| Payback | {metrics.get('payback_years', 'N/A')} years |")
            lines.append(f"| ROI | {metrics.get('roi_formatted', 'N/A')} |")
            lines.append(
                f"| Data Confidence | {option.get('metadata', {}).get('data_confidence', 'N/A')}% |"
            )
            lines.append("")
            sensitivity = option.get("sensitivity", [])[:3]
            if sensitivity:
                lines.append("**Key Sensitivity Scenarios:**")
                for scenario in sensitivity:
                    viable = "✓" if scenario.get("still_viable") else "✗"
                    lines.append(
                        f"- {scenario.get('scenario')}: NPV {scenario.get('npv_change_pct')}% change {viable}"
                    )
                lines.append("")

        comparison = self.calculated_results.get("comparison")
        if comparison:
            lines.append("### COMPARISON RESULT")
            lines.append("")
            lines.append(f"**Winner:** {comparison.get('winner')}")
            lines.append(f"**Confidence:** {comparison.get('confidence')}%")
            lines.append(f"**Margin:** {comparison.get('margin')} points")
            lines.append("")
            lines.append(f"**Recommendation:** {comparison.get('recommendation', 'N/A')}")

        return "\n".join(lines)

    def _inject_context_into_conversation(self):
        """Inject query context as the first turn in conversation history."""
        if not self.conversation_history or self.conversation_history[0].get("type") != "context":
            context_turn = {
                "agent": "Moderator",
                "turn": 0,
                "type": "context",
                "message": self._format_query_context(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.conversation_history.insert(0, context_turn)

    def _detect_question_complexity(self, question: str) -> str:
        """
        Detect question complexity based on question TYPE, not keywords.

        Returns "simple", "standard", "complex", or "comparative".
        """
        question_lower = question.lower().strip()
        word_count = len(question.split())

        complex_signals = 0

        if any(w in question_lower for w in ["should", "recommend", "advise", "propose", "suggest"]):
            complex_signals += 2

        comparative_patterns = [
            "vs", "versus", " or ", "compared to", "match", "compete",
            "against", "relative to", "option a", "option b", "either",
        ]
        is_comparative = any(w in question_lower for w in comparative_patterns)
        if is_comparative:
            complex_signals += 2
            if " or " in question_lower and any(
                w in question_lower for w in ["billion", "million", "invest", "fund", "allocat", "strategic"]
            ):
                logger.warning("🆚 Query detected as A vs B COMPARISON - using COMPARATIVE debate config")
                return "comparative"

        if any(w in question_lower for w in ["billion", "million", "budget", "invest", "allocat", "spend", "fund"]):
            complex_signals += 3
        if any(w in question_lower for w in ["strategic", "policy", "strategy", "long-term", "plan", "national"]):
            complex_signals += 2
        if any(w in question_lower for w in [
            "national", "country", "government", "ministry", "minister",
            "regional", "federal", "state", "sovereign", "public sector",
        ]):
            complex_signals += 2
        if any(w in question_lower for w in ["labor", "labour", "workforce", "employment", "economic", "economy"]):
            complex_signals += 1
        if word_count >= 15:
            complex_signals += 1
        if word_count >= 25:
            complex_signals += 1
        if any(c in question for c in ["$", "QAR", "USD"]):
            complex_signals += 2

        if complex_signals >= 2:
            logger.warning(f"🔥 Query classified as COMPLEX ({complex_signals} strategic signals)")
            return "complex"

        simple_patterns = [
            question_lower.startswith("what is the ") and word_count < 8,
            question_lower.startswith("how many ") and word_count < 6,
            question_lower.startswith("when did ") and word_count < 8,
            question_lower.startswith("who is ") and word_count < 6,
        ]
        is_policy_related = any(
            w in question_lower for w in ["policy", "trend", "analysis", "strategic", "national"]
        )

        if any(simple_patterns) and not is_policy_related:
            logger.info("Query classified as SIMPLE (factual lookup pattern)")
            return "simple"

        logger.info("Query classified as STANDARD (80 turns)")
        return "standard"

    def _apply_debate_config(self, complexity: str):
        """Apply debate configuration based on complexity."""
        config = self.DEBATE_CONFIGS.get(complexity, self.DEBATE_CONFIGS["standard"])
        self.MAX_TURNS_TOTAL = config["max_turns"]
        self.MAX_TURNS_PER_PHASE = config["phases"]
        self.debate_complexity = complexity
        logger.info(f"Debate configuration: {complexity.upper()} (max_turns={self.MAX_TURNS_TOTAL})")

    async def conduct_legendary_debate(
        self,
        question: str,
        contradictions: List[Dict],
        agents_map: Dict[str, Any],
        agent_reports_map: Dict[str, Any],
        llm_client: LLMClient,
        extracted_facts: Optional[List[Dict[str, Any]]] = None,
        debate_depth: Optional[str] = None,
        calculated_results: Optional[Dict[str, Any]] = None,
        calculation_warning: Optional[str] = None,
        cross_scenario_context: Optional[str] = None,
        scenario_results: Optional[List[Dict[str, Any]]] = None,
        case_studies_context: Optional[str] = None,
        question_type: Optional[str] = None,
    ) -> Dict:
        """Execute complete 6-phase legendary debate."""
        self.question = question
        self.start_time = datetime.now()
        self.conversation_history = []
        self.turn_counter = 0
        self.resolutions = []
        self.agent_reports_map = agent_reports_map
        self.extracted_facts = extracted_facts or []
        self.calculated_results = calculated_results
        self.calculation_warning = calculation_warning
        self.cross_scenario_context = cross_scenario_context or ""
        self.question_type = question_type or "COMPARATIVE"
        logger.info(f"📋 Question type for debate: {self.question_type}")
        self.scenario_results = scenario_results or []
        self.case_studies_context = case_studies_context or ""
        if self.case_studies_context:
            logger.info("📚 CASE STUDIES LOADED for debate context")
        if self.scenario_results:
            logger.info(f"📊 SCENARIO RESULTS LOADED: {len(self.scenario_results)} scenarios")
            for sr in self.scenario_results:
                sr_name = sr.get('scenario', {}).get('name', sr.get('scenario_name', 'Unknown'))
                sr_rate = self._extract_scenario_rate(sr)
                logger.info(f"   - {sr_name}: {sr_rate:.1f}%")
        else:
            logger.warning("⚠️ NO SCENARIO RESULTS AVAILABLE FOR DEBATE")

        self._smart_moderator = SmartModerator(question)
        self._turn_validator = TurnValidator(question)
        self._question_locker = QuestionLocker(question)
        logger.info("🧠 SmartModerator initialized for content-based intervention")
        logger.info(
            f"🔒 QuestionLocker initialized: type={self._question_locker.question_type}, "
            f"options={self._question_locker.options}"
        )

        self.phase_turn_counters = defaultdict(int)

        logger.warning("🔥🔥🔥 DEBATE ORCHESTRATOR STARTING 🔥🔥🔥")
        logger.warning(f"🔍 DEBATE_DEPTH INPUT: '{debate_depth}' (type={type(debate_depth).__name__})")

        if debate_depth and debate_depth.strip():
            depth_to_complexity = {
                "standard": "simple",
                "deep": "standard",
                "legendary": "complex",
            }
            depth_lower = debate_depth.strip().lower()
            complexity = depth_to_complexity.get(depth_lower, "complex")
            logger.warning(f"🎚️ USER SELECTED DEPTH: '{debate_depth}' → complexity='{complexity}'")
        else:
            complexity = self._detect_question_complexity(question)
            logger.warning(f"🔍 Auto-detected complexity: {complexity}")

        self._apply_debate_config(complexity)
        logger.warning(f"🎚️ CONFIGURED MAX_TURNS_TOTAL = {self.MAX_TURNS_TOTAL}")

        self._inject_context_into_conversation()
        logger.info(f"📋 Injected query context: {len(self.extracted_facts)} facts available")

        # Phase 1: Opening Statements
        await self._phase_1_opening_statements(agents_map)

        # Transition: Opening → Analysis
        scenario_anchor = self._build_scenario_anchor(phase="analysis")
        phase_reminder = self._question_locker.get_phase_reminder("analysis") if self._question_locker else ""
        await self._emit_turn(
            "Moderator", "phase_transition",
            self.PHASE_TRANSITION_PROMPTS['OPENING_TO_ANALYSIS'] + "\n" + scenario_anchor + "\n" + phase_reminder,
        )
        if self._smart_moderator:
            self._smart_moderator.reset_warnings()

        # Phase 2: Challenge/Defense
        await self._phase_2_challenge_defense(contradictions, agents_map)

        # Circuit breaker
        circuit_breaker_threshold = self.MAX_TURNS_TOTAL * 0.90
        if self.turn_counter >= circuit_breaker_threshold:
            logger.warning("⚠️ CIRCUIT BREAKER TRIGGERED! Fast-tracking to synthesis")
            consensus_data = await self._phase_5_consensus_building(agents_map, llm_client)
            final_report = await self._phase_6_final_synthesis(self.conversation_history, llm_client)
            return {
                "total_turns": self.turn_counter,
                "phases_completed": 4,
                "conversation_history": self.conversation_history,
                "final_report": final_report,
                "resolutions": self.resolutions,
                "consensus": consensus_data,
                "execution_time_minutes": (datetime.now() - self.start_time).seconds / 60,
                "truncated": True,
            }

        # Transition: Analysis → Deliberation
        scenario_anchor = self._build_scenario_anchor(phase="edge_case")
        phase_reminder = self._question_locker.get_phase_reminder("edge_case") if self._question_locker else ""
        await self._emit_turn(
            "Moderator", "phase_transition",
            self.PHASE_TRANSITION_PROMPTS['ANALYSIS_TO_DELIBERATION'] + "\n" + scenario_anchor + "\n" + phase_reminder,
        )
        if self._smart_moderator:
            self._smart_moderator.reset_warnings()

        # Phase 3: Edge Cases
        edge_cases = await self._generate_edge_cases_llm(question, self.conversation_history, llm_client)
        await self._phase_3_edge_cases(edge_cases, agents_map)

        # Phase 4: Risk Analysis
        if self.turn_counter < self.MAX_TURNS_TOTAL * 0.85:
            await self._phase_4_risk_analysis(agents_map)
        else:
            logger.warning("Skipping Phase 4 (Risk Analysis) to ensure synthesis completes")

        # Transition: Deliberation → Consensus
        scenario_anchor = self._build_scenario_anchor(phase="final")
        phase_reminder = self._question_locker.get_phase_reminder("final_position") if self._question_locker else ""
        await self._emit_turn(
            "Moderator", "phase_transition",
            self.PHASE_TRANSITION_PROMPTS['DELIBERATION_TO_CONSENSUS'] + "\n" + scenario_anchor + "\n" + phase_reminder,
        )
        if self._smart_moderator:
            self._smart_moderator.reset_warnings()

        # Phase 5: Consensus Building
        try:
            consensus_data = await self._phase_5_consensus_building(agents_map, llm_client)
        except Exception as e:
            logger.error(f"Phase 5 failed: {e}, using fallback consensus")
            consensus_data = {"narrative": "Consensus building interrupted", "agreements": []}

        # Phase 6: Final Synthesis
        try:
            final_report = await self._phase_6_final_synthesis(self.conversation_history, llm_client)
        except Exception as e:
            logger.error(f"Phase 6 failed: {e}, using fallback synthesis")
            final_report = (
                f"Debate completed with {self.turn_counter} turns. "
                f"See conversation history for details."
            )

        return {
            "total_turns": self.turn_counter,
            "phases_completed": 6,
            "conversation_history": self.conversation_history,
            "final_report": final_report,
            "resolutions": self.resolutions,
            "consensus": consensus_data,
            "execution_time_minutes": (datetime.now() - self.start_time).seconds / 60,
            "truncated": False,
        }

    def _can_emit_turn(self) -> bool:
        """Check if we can emit another turn. PREVENTS RUNAWAY TURN GENERATION."""
        if self.turn_counter >= self.MAX_TURNS_TOTAL:
            logger.warning(f"Hit max total turns limit ({self.MAX_TURNS_TOTAL})")
            return False
        if self.current_phase and self.current_phase in self.MAX_TURNS_PER_PHASE:
            phase_limit = self.MAX_TURNS_PER_PHASE[self.current_phase]
            if self.phase_turn_counters[self.current_phase] >= phase_limit:
                logger.warning(f"Hit max turns for {self.current_phase} ({phase_limit})")
                return False
        return True

    async def _emit_turn(self, agent_name: str, turn_type: str, message: str):
        """Emit a conversation turn event with limit checking and phase budget enforcement."""
        if not self._can_emit_turn():
            return

        self.turn_counter += 1
        if self.current_phase:
            self.phase_turn_counters[self.current_phase] += 1
            if self._is_phase_budget_exceeded():
                budget_warning = self._generate_phase_budget_warning()
                if budget_warning:
                    logger.warning(
                        f"⏰ PHASE BUDGET EXCEEDED: {self.current_phase} has "
                        f"{self.phase_turn_counters[self.current_phase]} turns"
                    )

        self.agent_turn_counts[agent_name] += 1

        turn_data = {
            "agent": agent_name,
            "turn": self.turn_counter,
            "type": turn_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "phase": self.current_phase or "unknown",
        }

        self.conversation_history.append(turn_data)

        if self.emit_event:
            await self.emit_event("debate:turn", "streaming", turn_data)

        # NSIC live debate logging callback
        if self.on_turn_complete:
            try:
                self.on_turn_complete(
                    engine="A",
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    turn_num=self.turn_counter,
                    agent_name=agent_name,
                    content=message,
                    gpu_id=None,
                )
            except Exception as e:
                logger.debug(f"NSIC callback error (non-fatal): {e}")

        # Topic relevance check
        is_relevant, reason = self._check_topic_relevance(message)
        if not is_relevant:
            logger.warning(f"⚠️ Topic drift detected at turn {self.turn_counter}: {reason}")
            self._topic_drift_detected = True
            self._topic_drift_reason = reason

        # Smart moderation evaluation
        if self._smart_moderator and agent_name not in ["Moderator", "DataValidator"]:
            moderation = self._smart_moderator.evaluate_turn(message, self.conversation_history)
            if moderation['should_intervene']:
                self._topic_drift_detected = True
                self._topic_drift_reason = f"SmartModerator: {moderation['intervention_type']}"
                self._smart_moderator_message = moderation['intervention_message']
                logger.info(f"🧠 SmartModerator flagged intervention: {moderation['intervention_type']}")

        # Periodic question-relevance check
        if self.turn_counter > 0 and self.turn_counter % 10 == 0:
            recent_turns = self.conversation_history[-10:]
            question_lower = self.question.lower() if self.question else ""
            question_words = set(
                word for word in question_lower.split()
                if len(word) > 4 and word not in [
                    "should", "would", "could", "which", "what", "about",
                    "between", "given", "consider",
                ]
            )

            concept_mentions = 0
            for t in recent_turns:
                msg = t.get("message", "").lower()
                matches = sum(1 for word in question_words if word in msg)
                if matches >= 2:
                    concept_mentions += 1

            analytical_count = 0
            for t in recent_turns:
                msg = t.get("message", "").lower()
                if any(kw in msg for kw in [
                    "recommend", "conclude", "assessment", "analysis shows",
                    "evidence suggests", "probability", "success rate",
                    "based on", "therefore", "in conclusion",
                ]):
                    analytical_count += 1

            if concept_mentions < 3 and analytical_count < 3:
                logger.warning(f"⚠️ Debate may be drifting from question at turn {self.turn_counter}")
                self._needs_binary_reminder = True

    def _is_phase_budget_exceeded(self) -> bool:
        """Check if current phase has exceeded its turn budget."""
        if not self.current_phase:
            return False

        hard_limit = self.PHASE_HARD_LIMITS.get(self.current_phase)
        if hard_limit:
            current_turns = self.phase_turn_counters.get(self.current_phase, 0)
            if current_turns >= hard_limit:
                logger.warning(
                    f"⛔ HARD LIMIT REACHED: {self.current_phase} at {current_turns}/{hard_limit} turns"
                )
                return True

        config = self.DEBATE_CONFIGS.get(self.debate_complexity, self.DEBATE_CONFIGS["standard"])
        phases = config.get("phases", {})
        budget = phases.get(self.current_phase, 50)
        current_turns = self.phase_turn_counters.get(self.current_phase, 0)
        return current_turns >= budget

    def _generate_phase_budget_warning(self) -> str:
        """Generate a warning message when phase budget is exceeded."""
        hard_limit = self.PHASE_HARD_LIMITS.get(self.current_phase, 0)
        config = self.DEBATE_CONFIGS.get(self.debate_complexity, self.DEBATE_CONFIGS["standard"])
        phases = config.get("phases", {})
        budget = hard_limit if hard_limit else phases.get(self.current_phase, 50)
        current_turns = self.phase_turn_counters.get(self.current_phase, 0)

        if hard_limit and current_turns >= hard_limit:
            return (
                f"⛔ PHASE LIMIT REACHED — MANDATORY TRANSITION\n\n"
                f"The {self.current_phase.upper()} phase has reached its {hard_limit}-turn HARD LIMIT.\n\n"
                f"IMMEDIATE TRANSITION TO NEXT PHASE REQUIRED.\n\n"
                f"All agents must now move to the next phase.\n"
                f"No more {self.current_phase.lower()}-style responses allowed.\n\n"
                f"🔴 ANY CONTINUATION OF DATA DEBATES, METHODOLOGY DISCUSSION, OR\n"
                f"   STATISTIC CHALLENGES WILL BE BLOCKED.\n\n"
                f"The minister needs a decision. Provide your recommendation NOW."
            )

        return (
            f"⏰ PHASE BUDGET WARNING: The {self.current_phase} phase has used "
            f"{current_turns}/{budget} allocated turns.\n\n"
            f"The debate must progress to the next phase. Remaining turns should focus on:\n"
            f"- Synthesizing key points\n"
            f"- Stating clear positions\n"
            f"- Moving toward a recommendation\n\n"
            f"Do NOT continue methodology debates or data quality discussions."
        )

    async def _emit_phase(self, phase_name: str, message: str):
        """Emit phase change event."""
        self.current_phase = phase_name
        if self.emit_event:
            await self.emit_event(f"debate:{phase_name}", "running", {"message": message})

    def _summarize_debate(self, history: list) -> str:
        """Summarize debate for prompts."""
        if not history:
            return "No debate history yet."
        return self._format_history(history[-20:])
