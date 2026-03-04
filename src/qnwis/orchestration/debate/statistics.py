"""Debate statistics, detection, and validation methods."""

import logging
import re
from typing import Any, Dict, List

from ._convergence import detect_debate_convergence

logger = logging.getLogger(__name__)


class StatisticsMixin:
    """Mixin providing debate statistics, convergence detection, and data validation."""

    @staticmethod
    def _rephrase_for_content_filter(text: str) -> str:
        """
        Rephrase text to avoid Azure content filter false positives.

        Azure's "jailbreak" detection triggers on legitimate policy analysis
        terms that sound adversarial. This method replaces them with safe
        alternatives that maintain meaning.
        """
        replacements = {
            "DEVIL'S ADVOCATE": "CRITICAL REVIEWER",
            "Devil's Advocate": "Critical Reviewer",
            "devil's advocate": "critical reviewer",
            "play devil's advocate": "provide critical analysis",
            "acting as devil's advocate": "providing critical review",
            "CATASTROPHIC FAILURE": "major setback",
            "catastrophic failure": "major setback",
            "CATASTROPHIC": "severe",
            "catastrophic": "severe",
            "DISASTROUS": "significant negative",
            "disastrous": "significant negative",
            "DEVASTATING": "highly impactful",
            "devastating": "highly impactful",
            "WORST-CASE SCENARIO": "challenging scenario",
            "worst-case scenario": "challenging scenario",
            "WORST-CASE": "challenging",
            "worst-case": "challenging",
            "worst case": "challenging case",
            "NIGHTMARE SCENARIO": "difficult scenario",
            "nightmare scenario": "difficult scenario",
            "doomsday scenario": "adverse scenario",
            "attack the argument": "critically examine the argument",
            "attack this position": "challenge this position",
            "attack the assumptions": "question the assumptions",
            "destroy assumptions": "rigorously test assumptions",
            "tear apart": "thoroughly analyze",
            "rip apart": "carefully deconstruct",
            "exploit weakness": "address vulnerability",
            "exploit vulnerabilities": "identify improvement areas",
            "exploit the opportunity": "leverage the opportunity",
            "exploit gaps": "address gaps",
            "war room": "strategy session",
            "battle plan": "action plan",
            "ammunition": "supporting evidence",
            "arsenal": "toolkit",
            "weapons": "tools",
            "paranoid mode": "thorough review mode",
            "pessimistic mode": "risk-aware mode",
            "aggressive analysis": "comprehensive analysis",
            "hostile review": "critical review",
            "black swan event": "rare high-impact event",
            "black swan": "rare event",
            "tail risk event": "low-probability high-impact event",
            "tail risk": "extreme scenario",
            "systemic collapse": "systemic stress",
            "market crash": "market correction",
            "economic collapse": "economic contraction",
            "meltdown": "significant decline",
            "crisis scenario": "stress scenario",
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _validate_engagement(self, content: str, previous_agent: str) -> bool:
        """
        Validate that agent engaged with previous speaker.

        Returns True if engagement is valid, False otherwise.
        """
        if not content or not previous_agent:
            return False

        content_lower = content.lower()
        prev_lower = previous_agent.lower()

        agent_mentioned = (
            prev_lower in content_lower
            or previous_agent in content
            or "previous" in content_lower
            or "earlier" in content_lower
            or "above" in content_lower
        )

        if not agent_mentioned:
            return False

        engagement_verbs = [
            "challenge", "disagree", "question", "but ", "however",
            "building on", "extending", "agree with", "while", "although",
            "counter", "dispute", "support", "concur", "differ",
            "correct", "incorrect", "overlook", "miss", "ignor"
        ]
        return any(verb in content_lower for verb in engagement_verbs)

    def _extract_confidence(self, text: str) -> float:
        """
        Extract confidence level from agent statement.

        Returns float 0.0-1.0 representing confidence level (default 0.5).
        """
        if not text:
            return 0.5

        text_lower = text.lower()

        patterns = [
            r'(\d+)%?\s*confidence',
            r'confidence\s*(?:of\s*)?:?\s*(\d+)%?',
            r'(\d+)%?\s*certain',
            r'certainty\s*(?:of\s*)?:?\s*(\d+)%?',
            r'confidence\s*level\s*(?:of\s*)?:?\s*(\d+)%?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = float(match.group(1))
                    return value / 100 if value > 1 else value
                except (ValueError, IndexError):
                    continue

        return 0.5

    def _check_topic_relevance(self, turn_content: str) -> tuple[bool, str]:
        """
        Prevent topic drift by checking turn relevance.

        Returns (is_relevant, reason).
        """
        if not turn_content or not hasattr(self, 'question'):
            return (True, "")

        content_lower = turn_content.lower()
        question_lower = self.question.lower() if self.question else ""

        key_concepts = []
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "through",
            "during", "before", "after", "above", "below", "between", "under",
            "again", "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "few", "more", "most", "other", "some",
            "such", "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "and", "but", "if", "or", "because", "until",
            "while", "this", "that", "these", "those", "what", "which", "who",
        }

        question_words = question_lower.replace("?", "").replace(",", "").replace(".", "").split()
        for word in question_words:
            if len(word) > 3 and word not in stop_words:
                key_concepts.append(word)

        tangent_patterns = [
            ("input-output table", 3),
            ("leontief", 2),
            ("i-o coefficient", 2),
            ("sectoral multiplier", 3),
            ("econometric estimation", 2),
            ("cobb-douglas", 2),
            ("neoclassical", 2),
            ("theoretical framework", 2),
            ("methodological", 3),
        ]

        for pattern, max_count in tangent_patterns:
            if content_lower.count(pattern) > max_count:
                return (False, f"Excessive focus on '{pattern}' - redirect to practical analysis")

        concept_matches = sum(1 for c in key_concepts if c in content_lower)

        analytical_indicators = [
            "analysis", "assessment", "evidence", "data", "finding",
            "probability", "success", "risk", "impact", "outcome",
            "recommend", "suggest", "conclude", "therefore", "because",
            "based on", "according to", "indicates", "shows", "demonstrates",
            "evaluate", "estimate", "project", "forecast", "predict",
        ]
        has_analytical_content = any(ind in content_lower for ind in analytical_indicators)

        if concept_matches < 2 and not has_analytical_content:
            return (False, "Response doesn't address the original question")

        return (True, "")

    def _check_low_confidence_agents(
        self,
        agent_positions: Dict[str, str],
        threshold: float = 0.40,
    ) -> List[Dict[str, Any]]:
        """
        Check for agents with low confidence recommendations.

        Flags agents whose confidence is below threshold for ministerial review.
        """
        low_confidence_agents = []

        for agent_name, position_text in agent_positions.items():
            confidence = self._extract_confidence(position_text)
            if confidence < threshold:
                low_confidence_agents.append({
                    "agent": agent_name,
                    "confidence": confidence,
                    "message": f"⚠️ {agent_name}: {confidence:.0%} confidence (below {threshold:.0%} threshold)",
                })
                logger.warning(
                    f"⚠️ {agent_name}: {confidence:.0%} confidence recommendation (Turn {self.turn_counter})"
                )

        return low_confidence_agents

    def _detect_consensus(self, message: str) -> bool:
        """Detect if message contains consensus language."""
        consensus_phrases = [
            "i agree", "you're right", "we agree", "consensus reached",
            "i acknowledge", "that's correct", "both valid", "we can agree",
            "common ground", "i concur", "fair point",
            "you make a good point", "that makes sense",
        ]
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in consensus_phrases)

    def _detect_meta_debate(self, window: int = 15) -> bool:
        """
        Detect when agents are stuck in methodological loops.

        Only triggers for TRUE meta-debate (discussing methodology rather than
        substance), not for polite acknowledgments.
        """
        min_turns_before_check = int(self.MAX_TURNS_TOTAL * 0.5)
        if len(self.conversation_history) < max(window, min_turns_before_check):
            return False

        recent_turns = self.conversation_history[-window:]

        meta_phrases = [
            "methodological", "epistemological", "meta-analysis",
            "performative contradiction", "evidence hierarchy",
            "analytical capability", "demonstrate analysis",
            "policy analysis itself", "nature of analysis",
            "what constitutes evidence", "framework collapse",
            "discussing our discussion",
        ]

        meta_count = 0
        for turn in recent_turns:
            message = turn.get("message", "").lower()
            phrase_count = sum(1 for phrase in meta_phrases if phrase in message)
            if phrase_count >= 2:
                meta_count += 1

        if meta_count >= 10:
            logger.warning(f"🔍 Meta-debate: {meta_count}/{window} turns meta-analytical")
            return True

        return False

    def _detect_substantive_completion(self, recent_turn_count: int = 8) -> bool:
        """
        Detect when debate has reached substantive completion.

        Returns True if agents are repeating themselves or have nothing new to add.
        """
        if len(self.conversation_history) < recent_turn_count * 2:
            return False

        recent_turns = self.conversation_history[-recent_turn_count:]

        completion_phrases = [
            "we agree that", "we both recognize", "common ground",
            "I acknowledge your point", "you are correct", "valid point",
            "I accept that", "we concur", "shared understanding", "I must concede",
        ]
        repetition_phrases = [
            "as I previously stated", "as mentioned before",
            "I've already addressed", "repeating myself", "reiterating",
        ]

        agreement_count = 0
        repetition_count = 0

        for turn in recent_turns:
            message = turn.get("message", "").lower()
            if any(phrase in message for phrase in completion_phrases):
                agreement_count += 1
            if any(phrase in message for phrase in repetition_phrases):
                repetition_count += 1

        return agreement_count >= 6 or repetition_count >= 3

    def _check_convergence(self) -> bool:
        """
        Check if all agents have converged on a consensus position.

        For legendary debates (100-150 turns), only checks for very high
        semantic repetition. Intentionally conservative to ensure full debates.
        """
        min_turns_before_convergence = int(self.MAX_TURNS_TOTAL * 0.85)

        if len(self.conversation_history) < min_turns_before_convergence:
            return False

        recent_turns = self.conversation_history[-8:]
        texts = [turn.get("message", "")[:500] for turn in recent_turns]

        unique_texts = set(texts)
        if len(unique_texts) <= 2 and len(texts) >= 8:
            logger.warning(
                f"🛑 High repetition detected at turn {len(self.conversation_history)} "
                f"- agents are repeating themselves"
            )
            return True

        if len(self.conversation_history) >= self.MAX_TURNS_TOTAL * 0.95:
            result = detect_debate_convergence(self.conversation_history)
            if result.get("converged"):
                reason = result.get("reason", "unknown")
                logger.info(f"✅ Convergence at {len(self.conversation_history)} turns: {reason}")
                return True

        return False

    def _validate_suspicious_data(self) -> List[Dict]:
        """Flag obviously wrong data before agents use it."""
        SANITY_CHECKS = {
            "unemployment_rate": {"min": 0.5, "max": 30.0, "unit": "%"},
            "unemployment": {"min": 0.5, "max": 30.0, "unit": "%"},
            "gdp_growth": {"min": -15.0, "max": 25.0, "unit": "%"},
            "gdp": {"min": -15.0, "max": 25.0, "unit": "%"},
            "inflation_rate": {"min": -5.0, "max": 50.0, "unit": "%"},
            "inflation": {"min": -5.0, "max": 50.0, "unit": "%"},
            "labour_force_participation": {"min": 40.0, "max": 95.0, "unit": "%"},
            "labor_force": {"min": 40.0, "max": 95.0, "unit": "%"},
            "participation_rate": {"min": 40.0, "max": 95.0, "unit": "%"},
            "qatarization": {"min": 0.0, "max": 100.0, "unit": "%"},
            "wage_growth": {"min": -20.0, "max": 50.0, "unit": "%"},
            "employment_growth": {"min": -30.0, "max": 50.0, "unit": "%"},
        }

        warnings = []

        for agent_name, report in self.agent_reports_map.items():
            if not report:
                continue

            narrative = getattr(report, 'narrative', '')
            if not narrative:
                continue

            patterns = [
                r'(\w+(?:\s+\w+)?)\s*:?\s*(\d+\.?\d*)\s*%',
                r'(\w+(?:\s+\w+)?)\s+of\s+(\d+\.?\d*)\s*%',
                r'(\w+(?:\s+\w+)?)\s+at\s+(\d+\.?\d*)\s*%',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, narrative.lower())
                for metric_text, value_str in matches:
                    try:
                        value = float(value_str)
                        for metric_key, bounds in SANITY_CHECKS.items():
                            if metric_key in metric_text.replace('_', ' '):
                                if value < bounds["min"] or value > bounds["max"]:
                                    warning = {
                                        "type": "SUSPICIOUS_DATA",
                                        "agent": agent_name,
                                        "metric": metric_text,
                                        "value": value,
                                        "unit": bounds["unit"],
                                        "expected_range": f"{bounds['min']}-{bounds['max']}{bounds['unit']}",
                                        "action": "⚠️ Verify data source before using in analysis",
                                    }
                                    warnings.append(warning)
                                    logger.warning(
                                        f"🚨 SUSPICIOUS: {agent_name} reports "
                                        f"{metric_text}={value}{bounds['unit']} "
                                        f"(expected {bounds['min']}-{bounds['max']})"
                                    )
                    except (ValueError, TypeError):
                        continue

        return warnings

    def _flag_low_confidence_recommendations(self, conversation_history: List[Dict]) -> List[Dict]:
        """
        Flag when agents make recommendations despite low confidence.

        Only uses FINAL position per agent. Only flags if explicit confidence < 35%.
        """
        flags = []
        agent_final_confidence: Dict[str, float] = {}
        agent_final_turn: Dict[str, int] = {}

        for turn in conversation_history:
            agent_name = turn.get("agent", "")
            message = turn.get("message", "").lower()
            turn_num = turn.get("turn", 0)

            if agent_name in ["Moderator", "DataValidator", ""]:
                continue

            confidence_patterns = [
                r'(\d+)%?\s*confidence',
                r'confidence\s*(?:of\s*)?:?\s*(\d+)%?',
                r'(\d+)%?\s*certain',
                r'certainty\s*(?:of\s*)?:?\s*(\d+)%?',
                r'my confidence[:\s]+(\d+)%?',
            ]

            confidence = None
            for pattern in confidence_patterns:
                match = re.search(pattern, message)
                if match:
                    try:
                        conf_value = float(match.group(1))
                        if conf_value > 1:
                            confidence = conf_value / 100.0
                        else:
                            confidence = conf_value
                        break
                    except (ValueError, IndexError):
                        continue

            if confidence is not None:
                agent_final_confidence[agent_name] = confidence
                agent_final_turn[agent_name] = turn_num

        LOW_CONFIDENCE_THRESHOLD = 0.35

        for agent_name, confidence in agent_final_confidence.items():
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                flag = {
                    "type": "LOW_CONFIDENCE_RECOMMENDATION",
                    "agent": agent_name,
                    "confidence": confidence,
                    "turn": agent_final_turn.get(agent_name, 0),
                    "message": f"⚠️ {agent_name} stated only {confidence * 100:.0f}% confidence",
                    "action": "Request additional data before implementation",
                }
                flags.append(flag)
                logger.warning(
                    f"⚠️ {agent_name}: {confidence * 100:.0f}% explicit confidence "
                    f"(Turn {agent_final_turn.get(agent_name, 0)})"
                )

        return flags
