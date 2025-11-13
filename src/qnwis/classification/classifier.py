"""Simple question classifier for routing."""

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Classifier:
    """
    Simple question classifier.

    Classifies questions by complexity, intent, and routing requirements.

    New Phase 3 capabilities:
    - Detects temporal queries (what WAS) → TimeMachine
    - Detects forecast queries (what WILL) → Predictor
    - Detects scenario queries (what IF) → Scenario
    """

    def __init__(self):
        """Initialize classifier with pattern matchers."""
        # Temporal patterns (TimeMachine)
        self.temporal_patterns = [
            r'\bwhat (was|were)\b',
            r'\b(in|during) (19|20)\d{2}\b',  # Year references
            r'\bhistorical\b',
            r'\bpast\b',
            r'\btrend\b',
            r'\byoy\b',  # Year-over-year
            r'\bqtq\b',  # Quarter-to-quarter
            r'\b(last|previous) (year|quarter|month)\b',
        ]

        # Forecast patterns (Predictor)
        self.forecast_patterns = [
            r'\bwhat will\b',
            r'\bforecast\b',
            r'\bpredict\b',
            r'\bprojection\b',
            r'\bnext (year|quarter|month)\b',
            r'\b(in|by) (19|20)\d{2}\b',  # Future year
            r'\bearly.?warning\b',
        ]

        # Scenario patterns (Scenario Agent)
        self.scenario_patterns = [
            r'\bwhat if\b',
            r'\bscenario\b',
            r'\bsimulat(e|ion)\b',
            r'\bassume\b',
            r'\bwould\b.*\bif\b',
            r'\bhow would\b',
        ]

    def classify_text(self, question: str) -> Dict[str, Any]:
        """
        Classify question.

        Args:
            question: User's question

        Returns:
            Classification dict with intent, complexity, confidence, and routing
        """
        question_lower = question.lower()

        # Detect deterministic agent routing
        route_to = self._detect_routing(question_lower)

        # Simple keyword-based classification
        complexity = "simple"
        if any(word in question_lower for word in ["compare", "analyze", "forecast", "predict"]):
            complexity = "medium"
        if any(word in question_lower for word in ["scenario", "what if", "simulate"]):
            complexity = "complex"

        intent = "baseline"
        if "trend" in question_lower or "historical" in question_lower:
            intent = "trend"
        elif "forecast" in question_lower or "predict" in question_lower:
            intent = "forecast"
        elif "compare" in question_lower or "gcc" in question_lower:
            intent = "comparison"
        elif "what if" in question_lower or "scenario" in question_lower:
            intent = "scenario"

        return {
            "intent": intent,
            "complexity": complexity,
            "confidence": 0.8,
            "entities": {},
            "route_to": route_to,  # NEW: deterministic agent routing
        }

    def _detect_routing(self, question: str) -> Optional[str]:
        """
        Detect if question should route to a deterministic agent.

        Priority order (highest first):
        1. Scenario (what if)
        2. Temporal (what was/historical)
        3. Forecast (what will/predict)

        Args:
            question: Lowercase question text

        Returns:
            Agent name ("time_machine", "predictor", "scenario") or None for LLM agents
        """
        # Check scenario first (highest specificity)
        if any(re.search(pattern, question) for pattern in self.scenario_patterns):
            logger.info("Routing to Scenario agent (what-if detected)")
            return "scenario"

        # Check temporal BEFORE forecast (to prevent "trend" misclassification)
        # Temporal is for historical data (what WAS)
        if any(re.search(pattern, question) for pattern in self.temporal_patterns):
            logger.info("Routing to TimeMachine agent (temporal detected)")
            return "time_machine"

        # Check forecast LAST (what WILL)
        # Only route to Predictor if no temporal match
        if any(re.search(pattern, question) for pattern in self.forecast_patterns):
            logger.info("Routing to Predictor agent (forecast detected)")
            return "predictor"

        # Default to LLM agents
        logger.info("Routing to LLM agents (no deterministic match)")
        return None
