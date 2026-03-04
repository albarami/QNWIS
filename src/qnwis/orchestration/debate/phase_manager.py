"""Debate phase management: opening, challenge, edge cases, and risk analysis."""

import logging
from typing import Any, Dict, List, Optional

from .json_parser import robust_json_parse

logger = logging.getLogger(__name__)

# Position-locked agent personalities for COMPARATIVE questions (Option A vs B)
_COMPARATIVE_PERSONALITIES = {
    "MicroEconomist": {
        "bias": "ADVOCATE_OPTION_A",
        "stance": (
            "YOU ARE THE CHAMPION FOR THE FIRST OPTION MENTIONED.\n"
            "Your job is to make the STRONGEST possible case for Option A.\n"
            "You must argue that Option A is CLEARLY SUPERIOR to Option B.\n"
            "Do NOT concede points easily. Challenge every argument for Option B.\n"
            "Only change position if presented with OVERWHELMING evidence."
        ),
        "typical_position": "Option A is the right choice. Option B has fatal flaws.",
        "debate_rules": (
            "- Present Option A as the clear winner\n"
            "- Attack Option B's weaknesses relentlessly\n"
            "- When challenged, defend with data\n"
            "- Do NOT say \"both have merit\" or suggest hybrids"
        ),
    },
    "MacroEconomist": {
        "bias": "ADVOCATE_OPTION_B",
        "stance": (
            "YOU ARE THE CHAMPION FOR THE SECOND OPTION MENTIONED.\n"
            "Your job is to make the STRONGEST possible case for Option B.\n"
            "You must argue that Option B is CLEARLY SUPERIOR to Option A.\n"
            "Do NOT concede points easily. Challenge every argument for Option A.\n"
            "Only change position if presented with OVERWHELMING evidence."
        ),
        "typical_position": "Option B is the right choice. Option A is unrealistic.",
        "debate_rules": (
            "- Present Option B as the clear winner\n"
            "- Attack Option A's weaknesses relentlessly\n"
            "- When challenged, defend with data\n"
            "- Do NOT say \"both have merit\" or suggest hybrids"
        ),
    },
    "SkillsAgent": {
        "bias": "SKEPTIC_OF_BOTH",
        "stance": (
            "YOU ARE SKEPTICAL OF BOTH OPTIONS.\n"
            "Your job is to challenge BOTH Option A AND Option B advocates.\n"
            "Ask hard questions: Why this amount? Why not something else entirely?\n"
            "Point out what everyone is overlooking.\n"
            "Force advocates to provide EVIDENCE, not assertions."
        ),
        "typical_position": "Neither option is as good as advocates claim. What are we missing?",
        "debate_rules": (
            "- Challenge Option A advocate's claims\n"
            "- Challenge Option B advocate's claims equally\n"
            '- Ask: "What\'s the null hypothesis? What if we do nothing?"\n'
            "- Question the assumptions everyone takes for granted"
        ),
    },
    "Nationalization": {
        "bias": "HYBRID_ADVOCATE",
        "stance": (
            "YOU BELIEVE A HYBRID/PHASED APPROACH IS BEST.\n"
            "Your job is to argue that neither pure Option A nor pure Option B is optimal.\n"
            "Propose specific hybrid allocations (e.g., 60/40, 70/30) with justification.\n"
            "But you must DEFEND this against pure option advocates."
        ),
        "typical_position": "A hybrid approach captures benefits while reducing risks.",
        "debate_rules": (
            "- Propose specific hybrid ratios with reasoning\n"
            '- Defend hybrid against "pick one" critics\n'
            "- Show how hybrid addresses weaknesses of both pure options\n"
            '- Be specific: not "some of each" but "60% A, 40% B because..."'
        ),
    },
    "PatternDetective": {
        "bias": "DEVIL_ADVOCATE",
        "stance": (
            "YOU CHALLENGE EVERY POSITION INCLUDING YOUR OWN.\n"
            "Your job is to find flaws in ALL arguments.\n"
            "If consensus is forming, break it by introducing counter-evidence.\n"
            "If everyone agrees Option A is best, make the case for Option B.\n"
            "Your goal is stress-testing, not agreement."
        ),
        "typical_position": "Wait - what about [thing nobody mentioned]?",
        "debate_rules": (
            "- Never agree without challenge\n"
            "- If 3 agents favor one option, argue for the other\n"
            "- Introduce uncomfortable facts others are ignoring\n"
            "- Force the group to earn their consensus"
        ),
    },
}

# Standard aggressive personalities for NON-COMPARATIVE questions
_STANDARD_PERSONALITIES = {
    "MicroEconomist": {
        "bias": "FISCAL_CONSERVATIVE",
        "stance": "Challenge expensive proposals. Demand ROI justification. Favor proven approaches over experiments.",
        "typical_position": "This will cost more and deliver less than claimed.",
        "debate_rules": "- Attack cost assumptions\n- Demand payback analysis\n- Question optimistic projections",
    },
    "MacroEconomist": {
        "bias": "STRATEGIC_OPTIMIST",
        "stance": "Favor bold transformational investments. Accept short-term costs for long-term positioning.",
        "typical_position": "The opportunity cost of NOT doing this is greater than the investment.",
        "debate_rules": "- Make the strategic case\n- Compare to peer countries\n- Think in decades not quarters",
    },
    "SkillsAgent": {
        "bias": "IMPLEMENTATION_REALIST",
        "stance": "Focus on whether this can actually be executed. Challenge plans that exceed human capital capacity.",
        "typical_position": "The plan is good but we can't deliver it with available talent.",
        "debate_rules": "- Question execution capacity\n- Challenge timeline assumptions\n- Demand workforce plans",
    },
    "Nationalization": {
        "bias": "NATIONAL_INTEREST_FIRST",
        "stance": "Prioritize national employment and participation. Challenge options that create expatriate dependency.",
        "typical_position": "If nationals can't do it, we shouldn't do it at this scale.",
        "debate_rules": "- Demand nationalization targets\n- Challenge foreign dependency\n- Push for capacity building",
    },
    "PatternDetective": {
        "bias": "CONTRARIAN",
        "stance": "Challenge consensus. If everyone agrees, find the flaw. Look for what's being ignored.",
        "typical_position": "You're all missing the obvious problem.",
        "debate_rules": "- Break forming consensus\n- Raise uncomfortable facts\n- Question assumptions",
    },
}

_DEFAULT_PERSONALITY = {
    "bias": "ANALYTICAL",
    "stance": "Provide objective analysis based on available evidence.",
    "typical_position": "Evidence should drive recommendations",
    "debate_rules": "- Be evidence-based\n- Challenge unsupported claims",
}


class PhaseManagerMixin:
    """Mixin providing debate phase execution methods (phases 1-4)."""

    async def _emit_moderator_redirect(self, reason: str):
        """Emit Moderator redirect when debate drifts off-topic."""
        if hasattr(self, '_smart_moderator_message') and self._smart_moderator_message:
            redirect_message = self._smart_moderator_message
            self._smart_moderator_message = None
        else:
            redirect_message = (
                f"⚠️ MODERATOR REDIRECT: {reason}\n\n"
                f"REFOCUS REQUIRED: The discussion has drifted from the core policy question.\n\n"
                f"ORIGINAL QUESTION: {self.question[:500] if hasattr(self, 'question') else 'Unknown'}\n\n"
                f"REQUIREMENTS FOR NEXT SPEAKER:\n"
                f"1. Directly address the specific options/alternatives in the question\n"
                f"2. Provide quantitative comparison where possible\n"
                f"3. Reference specific data and context\n"
                f"4. Give a clear recommendation with reasoning\n\n"
                f"Do NOT continue discussing general methodology without application to the question."
            )

        await self._emit_turn("Moderator", "redirect", redirect_message)

        if not hasattr(self, '_redirect_count'):
            self._redirect_count = 0
        self._redirect_count += 1

    async def _emit_devils_advocate_challenge(self):
        """
        Moderator challenges the emerging consensus.

        Forces agents to defend their positions and prevents premature agreement.
        """
        recent_turns = self.conversation_history[-10:]

        positions_summary = []
        for turn in recent_turns:
            agent = turn.get("agent", "")
            message = turn.get("message", "")[:300]
            if agent and agent not in ["Moderator", "DataValidator"]:
                positions_summary.append(f"- {agent}: {message[:150]}...")

        positions_text = "\n".join(positions_summary[-5:])
        question_display = self.question[:300] if len(self.question) > 300 else self.question

        challenge_message = (
            f"⚖️ **CRITICAL REVIEW INTERVENTION** (Turn {self.turn_counter})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **ORIGINAL QUESTION (STAY ON TOPIC):**\n{question_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Before we proceed further, let me stress-test the emerging positions.\n\n"
            f"**Recent positions under review:**\n{positions_text}\n\n"
            f"**CHALLENGES FOR THE PANEL:**\n\n"
            f"1. **DIRECT ANSWER (MANDATORY)**: Provide a quantified assessment and recommendation\n"
            f"2. **Assumption Check**: What key assumptions could be wrong?\n"
            f"3. **Counter-Evidence**: What data would CONTRADICT your recommendation?\n"
            f"4. **Topic Relevance**: Are you DIRECTLY answering the question?\n\n"
            f"**REQUIREMENT**: The next 3 speakers must provide QUANTIFIED assessments.\n\n"
            f"Do NOT continue with methodology discussions. ANSWER THE QUESTION with specifics."
        )

        await self._emit_turn("Moderator", "devils_advocate", challenge_message)
        logger.info(f"⚖️ Devil's Advocate challenge issued at turn {self.turn_counter}")

    async def _phase_1_opening_statements(self, agents_map: Dict[str, Any]):
        """Phase 1: Each agent presents their key findings."""
        self.current_phase = "opening"
        await self._emit_phase("opening", "All agents presenting positions")

        data_warnings = self._validate_suspicious_data()
        if data_warnings:
            logger.warning(f"⚠️ Found {len(data_warnings)} suspicious data points")
            warning_summary = "; ".join([
                f"{w['metric']}={w['value']}{w.get('unit', '')} (expected {w['expected_range']})"
                for w in data_warnings[:3]
            ])
            await self._emit_turn(
                "DataValidator", "data_quality_warning",
                f"⚠️ {len(data_warnings)} suspicious data points detected. "
                f"Validation required before analysis.\n\nExamples: {warning_summary}",
            )

        for agent_name, agent in agents_map.items():
            if not self._can_emit_turn():
                break
            topic = "Your findings on the current query"
            statement = await self._get_agent_statement(agent, agent_name, topic, "opening")
            await self._emit_turn(agent_name, "opening_statement", statement)

        micro_agent = agents_map.get("MicroEconomist")
        macro_agent = agents_map.get("MacroEconomist")
        if micro_agent and macro_agent:
            logger.info("🔥 PHASE 2A: Micro vs Macro Cross-Examination")
            macro_turns = [
                t for t in self.conversation_history
                if t.get("agent") == "MacroEconomist" and t.get("type") == "opening_statement"
            ]
            if macro_turns:
                macro_position = macro_turns[0].get("message", "")[:1000]

                if self._can_emit_turn() and hasattr(micro_agent, 'challenge_position'):
                    micro_challenge = await micro_agent.challenge_position(
                        opponent_name="MacroEconomist",
                        opponent_claim=macro_position,
                        conversation_history=self.conversation_history,
                        original_question=self.question,
                    )
                    await self._emit_turn("MicroEconomist", "challenge", micro_challenge)

                if self._can_emit_turn() and hasattr(macro_agent, 'respond_to_challenge'):
                    macro_response = await macro_agent.respond_to_challenge(
                        challenger_name="MicroEconomist",
                        challenge=micro_challenge,
                        conversation_history=self.conversation_history,
                        original_question=self.question,
                    )
                    await self._emit_turn("MacroEconomist", "response", macro_response)

    async def _get_agent_statement(
        self, agent: Any, agent_name: str, topic: str, phase: str
    ) -> str:
        """Get statement from agent (LLM or deterministic), including query context."""
        query_context = self._format_query_context()

        if hasattr(agent, "present_case"):
            question_type = getattr(self, 'question_type', 'COMPARATIVE')
            query_lower = self.question.lower()
            has_options = any(w in query_lower for w in ["or", "versus", "vs", "either", "between"])
            use_option_ab = (question_type == "COMPARATIVE" and has_options)

            if question_type in ("FORECAST", "DIAGNOSTIC", "HYBRID"):
                logger.info(
                    f"📋 FIX RUN 56: {question_type} question "
                    f"- using single-estimate personalities (no Option A/B)"
                )

            personalities = _COMPARATIVE_PERSONALITIES if use_option_ab else _STANDARD_PERSONALITIES
            personality = personalities.get(agent_name, _DEFAULT_PERSONALITY)
            debate_rules = personality.get('debate_rules', '')

            enhanced_topic = (
                f"{query_context}\n\n"
                f"YOUR ROLE AS {agent_name}: {topic}\n\n"
                f"═══════════════════════════════════════════════════════════════════════════════\n"
                f"🎭 YOUR ASSIGNED POSITION (YOU MUST DEFEND THIS):\n"
                f"═══════════════════════════════════════════════════════════════════════════════\n"
                f"Bias: {personality['bias']}\n\n"
                f"{personality['stance']}\n\n"
                f'Your Default Position: "{personality["typical_position"]}"\n\n'
                f"YOUR DEBATE RULES:\n{debate_rules}\n"
                f"═══════════════════════════════════════════════════════════════════════════════\n\n"
                f"⚠️ THIS IS A REAL DEBATE - NOT A POLITE DISCUSSION:\n"
                f"- You are LOCKED to your assigned position\n"
                f"- DEFEND your stance vigorously - do NOT be diplomatic\n"
                f"- ATTACK weak arguments from other agents\n"
                f"- Do NOT say \"I see merit in both sides\" unless you TRULY do\n"
                f"- Do NOT converge on consensus prematurely\n"
                f"- If another agent makes a weak argument, SAY SO directly\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Address the SPECIFIC QUESTION above (not generic risks)\n"
                f"2. Use the EXTRACTED FACTS provided (cite as [FACT N: value from SOURCE])\n"
                f"3. ADVOCATE for your assigned position with evidence\n"
                f"4. CHALLENGE other agents who disagree with you\n"
                f'5. Use STRONG language: "is", "will", "must" — NOT "could", "might", "perhaps"\n\n'
                f"Your expert analysis (be aggressive, not diplomatic):"
            )

            return await agent.present_case(
                enhanced_topic, self.conversation_history, original_question=self.question
            )
        else:
            report = self.agent_reports_map.get(agent_name)
            if report:
                narrative = getattr(report, 'narrative', '')
                findings = getattr(report, 'findings', [])
                if narrative:
                    query_short = self.question[:100] if len(self.question) > 100 else self.question
                    if agent_name == "ResearchSynthesizer":
                        return f"[{agent_name} - Academic Research Synthesis]:\n{narrative[:2000]}"
                    if phase == "opening":
                        return f"[{agent_name} Analysis on '{query_short}']: {narrative[:500]}"
                    elif phase == "edge_case":
                        return f"[{agent_name} Data for '{query_short}']: Historical patterns show: {narrative[:400]}"
                    elif phase == "risk":
                        return f"[{agent_name} Risk Assessment for '{query_short}']: {narrative[:400]}"
                    else:
                        return f"[{agent_name} on '{query_short}']: {narrative[:450]}"
                if findings and len(findings) > 0:
                    finding = findings[0]
                    if hasattr(finding, 'summary'):
                        return f"[{agent_name} Findings]: {finding.summary[:200]}"
            return f"[{agent_name}]: Analysis for: {self.question[:100]}..."

    async def _phase_2_challenge_defense(
        self, contradictions: List[Dict], agents_map: Dict[str, Any]
    ):
        """Phase 2: Multi-agent debate — ALL LLM agents participate."""
        self.current_phase = "challenge"
        await self._emit_phase("challenge", "Multi-agent debate on policy question")

        llm_agent_names = [
            'MicroEconomist', 'MacroEconomist', 'SkillsAgent',
            'Nationalization', 'PatternDetective',
        ]

        active_llm_agents = []
        for agent_name in llm_agent_names:
            if agent_name not in agents_map:
                logger.warning(f"⚠️ Agent '{agent_name}' NOT in agents_map")
                continue
            agent = agents_map[agent_name]
            has_capability = (
                hasattr(agent, 'present_case')
                or hasattr(agent, 'challenge_position')
                or hasattr(agent, 'respond_to_challenge')
                or hasattr(agent, 'analyze_edge_case')
            )
            if has_capability:
                active_llm_agents.append(agent_name)
                logger.info(f"✅ Agent '{agent_name}' has debate capability")
            else:
                logger.warning(f"⚠️ Agent '{agent_name}' lacks debate methods")

        if len(active_llm_agents) < 2:
            logger.warning(f"⚠️ Only {len(active_llm_agents)} agents - trying broader fallback")
            active_llm_agents = [
                name for name in agents_map.keys()
                if name not in ["DataValidator"]
                and (hasattr(agents_map[name], 'challenge_position')
                     or hasattr(agents_map[name], 'present_case'))
            ]

        logger.warning(
            f"🔥 PHASE 2: {len(active_llm_agents)} active LLM agents: {active_llm_agents}"
        )

        if len(active_llm_agents) < 2:
            logger.error("❌ Not enough LLM agents for multi-agent debate!")
            return

        phase_turns = self.MAX_TURNS_PER_PHASE.get("challenge", 60)
        num_agents = len(active_llm_agents) or 4
        min_rounds = 12 if self.debate_complexity == "complex" else 6
        max_debate_rounds = max(min_rounds, phase_turns // max(num_agents, 1))
        logger.warning(
            f"🔥 PHASE 2: {max_debate_rounds} rounds × {num_agents} agents "
            f"= {max_debate_rounds * num_agents} potential turns"
        )
        meta_debate_count = 0
        last_devils_advocate_turn = 0

        for round_num in range(1, max_debate_rounds + 1):
            logger.info(
                f"📢 Debate Round {round_num}/{max_debate_rounds} "
                f"(total turns so far: {self.turn_counter})"
            )

            if self.turn_counter - last_devils_advocate_turn >= 10 and self.turn_counter >= 10:
                await self._emit_devils_advocate_challenge()
                last_devils_advocate_turn = self.turn_counter

            balanced_agents = self._get_balanced_agent_order(active_llm_agents)

            for agent_name in balanced_agents:
                if not self._can_emit_turn():
                    break

                try:
                    recent_turns = self.conversation_history[-10:]
                    agent_recent_count = sum(
                        1 for t in recent_turns if t.get("agent") == agent_name
                    )

                    if agent_recent_count == 0 and len(recent_turns) >= 5:
                        action = "weigh_in"
                    else:
                        action = "challenge" if self.turn_counter % 2 == 0 else "weigh_in"

                    if action == "challenge":
                        other_agents = [a for a in active_llm_agents if a != agent_name]
                        if not other_agents:
                            action = "weigh_in"
                        else:
                            target = other_agents[self.turn_counter % len(other_agents)]
                            target_turns = [
                                t for t in self.conversation_history[-20:]
                                if t.get("agent") == target
                            ]
                            if not target_turns:
                                target_turns = [
                                    t for t in self.conversation_history
                                    if t.get("agent") == target
                                ]
                            if not target_turns:
                                target_position = f"[{target}'s position on the key question]"
                            else:
                                target_position = target_turns[-1].get("message", "")[:800]

                            if agent_name not in agents_map:
                                continue

                            agent = agents_map[agent_name]
                            if hasattr(agent, 'challenge_position'):
                                text = await agent.challenge_position(
                                    opponent_name=target,
                                    opponent_claim=target_position,
                                    conversation_history=self.conversation_history,
                                    original_question=self.question,
                                )
                                await self._emit_turn(agent_name, "challenge", text)
                            elif hasattr(agent, 'respond_to_challenge'):
                                text = await agent.respond_to_challenge(
                                    challenger_name=target,
                                    challenge=f"Challenge {target}'s position: {target_position[:500]}",
                                    conversation_history=self.conversation_history,
                                    original_question=self.question,
                                )
                                await self._emit_turn(agent_name, "challenge", text)
                            elif hasattr(agent, 'present_case'):
                                text = await agent.present_case(
                                    self.conversation_history, original_question=self.question
                                )
                                await self._emit_turn(agent_name, "position", text)
                            else:
                                logger.warning(f"Agent {agent_name} has no debate methods")
                            continue

                    # Weigh-in fallback
                    recent_summary = "\n".join([
                        f"{t.get('agent')}: {t.get('message', '')[:300]}..."
                        for t in recent_turns[-3:]
                    ]) if recent_turns else "Opening discussion phase"

                    if agent_name not in agents_map:
                        continue

                    agent = agents_map[agent_name]
                    if hasattr(agent, 'respond_to_challenge'):
                        text = await agent.respond_to_challenge(
                            challenger_name="Moderator",
                            challenge=(
                                f"Recent debate:\n{recent_summary}\n\n"
                                f"Add your unique perspective from your expertise."
                            ),
                            conversation_history=self.conversation_history,
                            original_question=self.question,
                        )
                        await self._emit_turn(agent_name, "weigh_in", text)
                    elif hasattr(agent, 'present_case'):
                        text = await agent.present_case(
                            self.conversation_history, original_question=self.question
                        )
                        await self._emit_turn(agent_name, "position", text)
                    elif hasattr(agent, 'challenge_position'):
                        text = await agent.challenge_position(
                            opponent_name="Previous speakers",
                            opponent_claim=recent_summary[:500] if recent_summary else "initial positions",
                            conversation_history=self.conversation_history,
                            original_question=self.question,
                        )
                        await self._emit_turn(agent_name, "weigh_in", text)
                    else:
                        logger.warning(f"Agent {agent_name} has no usable debate methods")

                except Exception as e:
                    logger.error(f"❌ {agent_name} debate error: {e}")
                    continue

                if self._topic_drift_detected:
                    await self._emit_moderator_redirect(self._topic_drift_reason)
                    self._topic_drift_detected = False
                    self._topic_drift_reason = ""

                if self._needs_binary_reminder:
                    binary_reminder = (
                        f"⚠️ MODERATOR REMINDER (Turn {self.turn_counter}):\n\n"
                        f"ORIGINAL QUESTION: {self.question[:500] if self.question else 'Unknown'}\n\n"
                        f"REQUIREMENT: The next speaker MUST:\n"
                        f"1. Directly address the SPECIFIC question above\n"
                        f"2. Provide quantified assessment\n"
                        f"3. State a clear recommendation\n"
                        f"4. Reference specific evidence\n\n"
                        f"Do NOT continue with theoretical discussions."
                    )
                    await self._emit_turn("Moderator", "redirect", binary_reminder)
                    self._needs_binary_reminder = False

            if self._check_convergence():
                logger.warning(
                    f"✅ Consensus reached at turn {self.turn_counter} "
                    f"(min required: {self.MAX_TURNS_TOTAL * 0.85:.0f})"
                )
                break

            if self.turn_counter > self.MAX_TURNS_TOTAL * 0.4 and self._detect_meta_debate():
                meta_debate_count += 1
                logger.warning(f"⚠️ Meta-debate detected ({meta_debate_count}/4)")
                if meta_debate_count >= 4:
                    logger.warning("🛑 Breaking meta-debate loop with refocus")
                    for an in active_llm_agents:
                        if not self._can_emit_turn():
                            break
                        try:
                            a = agents_map.get(an)
                            if a and hasattr(a, 'state_final_position'):
                                final = await a.state_final_position(
                                    debate_history=self.conversation_history,
                                    confidence_level=True,
                                    question_type=getattr(self, 'question_type', 'COMPARATIVE'),
                                    original_question=self.question,
                                )
                            else:
                                final = "Refocused on core policy question."
                            await self._emit_turn(an, "refocus", final)
                        except Exception as e:
                            logger.error(f"Refocus error for {an}: {e}")
                    break

    async def _debate_contradiction(
        self, contradiction: Dict, agents_map: Dict[str, Any]
    ) -> Optional[Dict]:
        """Conduct multi-turn debate for a single contradiction."""
        agent1_name = contradiction.get("agent1_name")
        agent2_name = contradiction.get("agent2_name")
        agent1 = agents_map.get(agent1_name)
        agent2 = agents_map.get(agent2_name)

        if not agent1 or not agent2:
            return None

        MAX_ROUNDS = 5
        debate_turns = []
        consensus_reached = False

        for round_num in range(MAX_ROUNDS):
            if not self._can_emit_turn():
                break

            challenge = ""
            if hasattr(agent1, 'challenge_position'):
                challenge = await agent1.challenge_position(
                    opponent_name=agent2_name,
                    opponent_claim=contradiction.get("agent2_value_str", ""),
                    conversation_history=self.conversation_history,
                    original_question=self.question,
                )
                await self._emit_turn(agent1_name, "challenge", challenge)
                debate_turns.append({"agent": agent1_name, "type": "challenge", "message": challenge})

            response = ""
            if hasattr(agent2, 'respond_to_challenge'):
                response = await agent2.respond_to_challenge(
                    challenger_name=agent1_name,
                    challenge=challenge,
                    conversation_history=self.conversation_history,
                    original_question=self.question,
                )
                await self._emit_turn(agent2_name, "response", response)
                debate_turns.append({"agent": agent2_name, "type": "response", "message": response})

            if self._detect_consensus(response):
                logger.info(f"✓ Consensus reached on round {round_num}")
                consensus_reached = True
                break

            if round_num >= 10 and self._detect_meta_debate():
                logger.warning(f"⚠️ Meta-debate detected at round {round_num}. Refocusing.")
                await self._emit_turn(
                    "Moderator", "refocus",
                    f"Let's refocus on the core policy question: {self.question}\n\n"
                    f"Provide a concise final position.",
                )
                break

            if self._detect_substantive_completion():
                logger.info(f"✓ Substantive completion detected at round {round_num}")
                await self._emit_turn(
                    "Moderator", "completion",
                    "Debate has reached substantive completion. Proceeding to synthesis.",
                )
                consensus_reached = True
                break

        resolution = await self._synthesize_resolution_llm(
            contradiction, debate_turns, consensus_reached
        )
        return resolution

    async def _generate_edge_cases_llm(
        self, question: str, conversation_history: List[Dict], llm_client: Any
    ) -> List[Dict]:
        """Generate context-aware edge cases using LLM."""
        debate_summary = self._summarize_debate(conversation_history)

        prompt = (
            f"Question: {question}\n\n"
            f"Debate summary: {debate_summary}\n\n"
            f"Generate 5 edge case scenarios that could invalidate the recommendations:\n\n"
            f"1. Economic shocks (oil price collapse 50%+, recession)\n"
            f"2. Regional competition (Saudi/UAE wage matching, policy changes)\n"
            f"3. Technology disruption (automation eliminating 30% of jobs)\n"
            f"4. Political instability (regional conflict, expat exodus)\n"
            f"5. Black swan events (pandemic-level disruption)\n\n"
            f"For each return JSON with: description, severity, probability_pct, "
            f"impact_on_recommendations, relevant_agents.\n\nReturn as JSON array."
        )

        response = await llm_client.generate_with_routing(
            prompt=prompt, task_type="debate", temperature=0.6, max_tokens=2000
        )

        try:
            edge_cases = robust_json_parse(response, default=[])
            if isinstance(edge_cases, list):
                return edge_cases
            elif isinstance(edge_cases, dict) and "edge_cases" in edge_cases:
                return edge_cases["edge_cases"]
            return []
        except Exception as e:
            logger.error(f"Failed to parse edge cases: {e}")
            return []

    async def _phase_3_edge_cases(
        self, edge_cases: List[Dict], agents_map: Dict[str, Any]
    ):
        """Phase 3: Explore edge cases with relevant agents."""
        self.current_phase = "edge_case"

        question_type = getattr(self, 'question_type', 'COMPARATIVE')
        if question_type in ("FORECAST", "DIAGNOSTIC", "HYBRID"):
            await self._emit_phase("edge_case", "Stress-testing probability estimate")
            await self._emit_turn(
                "Moderator", "edge_case_instruction",
                f"═══════════════════════════════════════════════════════════════════════════════\n"
                f"⚠️ EDGE CASE ANALYSIS ({question_type} QUESTION)\n"
                f"═══════════════════════════════════════════════════════════════════════════════\n\n"
                f"REMINDER: This is a {question_type} question. There is NO Option A vs Option B.\n"
                f"You are stress-testing the SINGLE probability estimate.\n\n"
                f"For each edge case scenario:\n"
                f"1. How would it affect your probability estimate?\n"
                f"2. Would probability go UP or DOWN? By how much?\n"
                f"3. What early warning signs should trigger reassessment?\n\n"
                f"🚫 FORBIDDEN: Do NOT create Option A/B/C frameworks.\n\n"
                f"Analyze the edge cases NOW.\n"
                f"═══════════════════════════════════════════════════════════════════════════════",
            )
        else:
            await self._emit_phase("edge_case", "Exploring edge case scenarios")

        for edge_case in edge_cases:
            if not self._can_emit_turn():
                break

            description = edge_case.get("description", "Unknown scenario")
            if self.emit_event:
                await self.emit_event(
                    "debate:edge_case", "running",
                    {"message": f"Scenario: {description[:100]}...", **edge_case},
                )

            relevant_agents = self._select_relevant_agents_for_scenario(edge_case, agents_map)
            available_agents = [a for a in relevant_agents if a in agents_map][:3]

            for agent_name in available_agents:
                if not self._can_emit_turn():
                    break
                if agent_name not in agents_map:
                    continue

                agent = agents_map[agent_name]
                if hasattr(agent, 'analyze_edge_case'):
                    analysis = await agent.analyze_edge_case(
                        edge_case, self.conversation_history,
                        question_type=getattr(self, 'question_type', 'COMPARATIVE'),
                        original_question=self.question,
                    )
                else:
                    analysis = await self._get_agent_statement(
                        agent, agent_name, f"Edge case: {description}", "edge_case"
                    )
                await self._emit_turn(agent_name, "edge_case_analysis", analysis)

    def _select_relevant_agents_for_scenario(
        self, edge_case: Dict, agents_map: Dict[str, Any]
    ) -> List[str]:
        """Select most relevant agents for an edge case scenario."""
        if "relevant_agents" in edge_case:
            return edge_case["relevant_agents"]

        description = edge_case.get("description", "").lower()
        severity = edge_case.get("severity", "medium")
        relevant = []

        if any(w in description for w in ["economic", "oil", "recession", "fiscal"]):
            relevant.extend(["LabourEconomist", "NationalStrategy", "NationalStrategyLLM"])
        if any(w in description for w in ["competition", "saudi", "uae", "regional", "wage"]):
            relevant.extend(["Nationalization", "SkillsAgent", "NationalStrategyLLM"])
        if any(w in description for w in ["technology", "automation", "ai", "disruption"]):
            relevant.extend(["SkillsAgent", "PatternDetective"])
        if any(w in description for w in ["political", "instability", "conflict", "exodus"]):
            relevant.extend(["NationalStrategyLLM", "Nationalization", "LabourEconomist"])
        if severity == "critical":
            relevant.extend(["TimeMachine", "Predictor"])

        seen = set()
        deduplicated = []
        for agent in relevant:
            if agent not in seen and agent in agents_map:
                seen.add(agent)
                deduplicated.append(agent)

        if not deduplicated:
            deduplicated = [
                name for name in agents_map.keys()
                if name not in ["DataValidator"]
                and hasattr(agents_map.get(name), 'analyze_edge_case')
            ]

        return [a for a in deduplicated if a in agents_map]

    async def _phase_4_risk_analysis(self, agents_map: Dict[str, Any]) -> List[Dict]:
        """Phase 4: Each agent identifies risks specific to the options being debated."""
        self.current_phase = "risk"

        question_type = getattr(self, 'question_type', 'COMPARATIVE')
        if question_type in ("FORECAST", "DIAGNOSTIC", "HYBRID"):
            await self._emit_phase("risk", "Identifying risks to probability estimate")
            await self._emit_turn(
                "Moderator", "risk_phase_instruction",
                f"═══════════════════════════════════════════════════════════════════════════════\n"
                f"⚠️ RISK ANALYSIS INSTRUCTIONS ({question_type} QUESTION)\n"
                f"═══════════════════════════════════════════════════════════════════════════════\n\n"
                f"REMINDER: This is a {question_type} question. There is NO Option A vs Option B.\n"
                f"You are analyzing risks to the SINGLE probability estimate you provided.\n\n"
                f"Your risk analysis must:\n"
                f"1. Identify risks that could LOWER the probability of success\n"
                f"2. Identify factors that could RAISE the probability of success\n"
                f"3. Assess likelihood and impact of each risk\n"
                f"4. Suggest contingencies and early warning indicators\n\n"
                f"🚫 FORBIDDEN: Do NOT create Option A/B/C frameworks.\n\n"
                f"Analyze the risks NOW.\n"
                f"═══════════════════════════════════════════════════════════════════════════════",
            )
        else:
            await self._emit_phase("risk", "Identifying risks for specific options")

        risks_identified = []
        llm_agents = {
            name: agent for name, agent in agents_map.items()
            if hasattr(agent, 'identify_catastrophic_risks')
        }

        safe_question = self._rephrase_for_content_filter(self.question[:500])

        if question_type in ("FORECAST", "DIAGNOSTIC", "HYBRID"):
            query_context = (
                f"\nQUESTION (SINGLE OUTCOME - NOT A vs B):\n{safe_question}\n\n"
                f"This is a {question_type} question. Analyze risks to a SINGLE probability estimate.\n\n"
                f"Focus on:\n1. What could prevent success?\n"
                f"2. What assumptions might be wrong?\n"
                f"3. What external factors could change the probability?\n"
            )
        else:
            query_context = (
                f"\nThe decision being analyzed:\n{safe_question}\n\n"
                f"Please focus your analysis on practical considerations for the specific options,\n"
                f"identifying implementation challenges and resource requirements.\n"
            )
        query_context = self._rephrase_for_content_filter(query_context)

        for agent_name, agent in llm_agents.items():
            if not self._can_emit_turn():
                break
            try:
                risk_response = await agent.identify_catastrophic_risks(
                    conversation_history=self.conversation_history,
                    mode="question_specific",
                    query_context=query_context,
                    question_type=getattr(self, 'question_type', 'COMPARATIVE'),
                )
                await self._emit_turn(agent_name, "risk_identification", risk_response)
                risks_identified.append({"agent": agent_name, "risk": risk_response})
            except Exception as e:
                error_str = str(e).lower()
                if "content_filter" in error_str or "jailbreak" in error_str or "filtered" in error_str:
                    logger.warning(f"Content filter blocked {agent_name}, using fallback")
                    fallback = await self._get_fallback_risk_analysis(
                        agent_name, agent, self.question[:300]
                    )
                    await self._emit_turn(agent_name, "risk_analysis_fallback", fallback)
                    risks_identified.append({"agent": agent_name, "risk": fallback, "fallback": True})
                else:
                    logger.error(f"Risk analysis failed for {agent_name}: {e}")
                    continue

            if risks_identified and risks_identified[-1].get("risk"):
                last_risk = risks_identified[-1]["risk"]
                assessors = self._select_risk_assessors(agent_name, last_risk, llm_agents)
                for other_name in assessors[:2]:
                    if not self._can_emit_turn():
                        break
                    try:
                        other_agent = llm_agents[other_name]
                        assessment = await other_agent.assess_risk_likelihood(
                            risk_description=last_risk,
                            conversation_history=self.conversation_history,
                        )
                        await self._emit_turn(other_name, "risk_assessment", assessment)
                    except Exception as e:
                        logger.warning(f"Risk assessment failed for {other_name}: {e}")

        return risks_identified

    async def _get_fallback_risk_analysis(
        self, agent_name: str, agent: Any, question: str
    ) -> str:
        """Fallback risk analysis with content-filter-safe prompt."""
        simple_prompt = (
            f"As a {agent_name.replace('_', ' ').replace('Agent', '').strip()} analyst, "
            f"please briefly describe potential challenges for this decision:\n\n"
            f"{question}\n\nWhat are 2-3 practical considerations to keep in mind?"
        )
        try:
            return await agent.llm.generate(
                prompt=simple_prompt, temperature=0.3, max_tokens=1200
            )
        except Exception as e:
            logger.error(f"Fallback also failed for {agent_name}: {e}")
            return f"[{agent_name}] Risk analysis temporarily unavailable."

    def _select_risk_assessors(
        self, risk_identifier: str, risk_description: str, llm_agents: Dict[str, Any]
    ) -> List[str]:
        """Select 2 most relevant agents to assess a risk."""
        risk_lower = risk_description.lower()
        candidates = [name for name in llm_agents.keys() if name != risk_identifier]

        scored = []
        for candidate in candidates:
            score = 0
            if candidate == "Nationalization" and any(
                w in risk_lower for w in ["qatarization", "policy", "national", "expat"]
            ):
                score += 3
            if candidate == "SkillsAgent" and any(
                w in risk_lower for w in ["skill", "training", "education", "workforce"]
            ):
                score += 3
            if "Strategy" in candidate and any(
                w in risk_lower for w in ["strategy", "systemic", "long-term", "structural"]
            ):
                score += 2
            if "PatternDetective" in candidate and any(
                w in risk_lower for w in ["anomaly", "pattern", "unexpected", "historical"]
            ):
                score += 2
            if candidate == "LabourEconomist" and any(
                w in risk_lower for w in ["economic", "employment", "unemployment", "wage"]
            ):
                score += 3
            scored.append((candidate, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored]
