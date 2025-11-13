"""Simple question classifier for routing."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Classifier:
    """
    Simple question classifier.
    
    Classifies questions by complexity and intent.
    """
    
    def classify_text(self, question: str) -> Dict[str, Any]:
        """
        Classify question.
        
        Args:
            question: User's question
            
        Returns:
            Classification dict with intent, complexity, confidence
        """
        question_lower = question.lower()
        
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
        
        return {
            "intent": intent,
            "complexity": complexity,
            "confidence": 0.8,
            "entities": {}
        }
