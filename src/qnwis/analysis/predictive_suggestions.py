"""
Predictive Suggestions for QNWIS (P4).

Provides intelligent query suggestions based on user patterns and context.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class PredictiveSuggester:
    """
    Generate intelligent query suggestions for users.
    
    Uses:
    - Historical query patterns
    - Current context
    - Trending topics
    - Common ministerial questions
    """
    
    # Common ministerial questions for Qatar
    SUGGESTED_QUESTIONS = {
        "unemployment": [
            "What is Qatar's current unemployment rate?",
            "How does unemployment compare to last year?",
            "Which sectors have the highest unemployment?",
        ],
        "qatarization": [
            "What is the current Qatarization rate?",
            "How does Qatar's nationalization compare to GCC countries?",
            "Which sectors are meeting Qatarization targets?",
        ],
        "skills": [
            "What are the critical skills gaps in Qatar's workforce?",
            "Which sectors need the most training investment?",
            "What skills are most in demand?",
        ],
        "vision_2030": [
            "How is Qatar progressing toward Vision 2030 workforce goals?",
            "What are the key workforce challenges for Vision 2030?",
            "Are we on track for Vision 2030 employment targets?",
        ],
        "gcc": [
            "How does Qatar compare to other GCC countries?",
            "What are regional workforce trends in the GCC?",
            "Which GCC country has the lowest unemployment?",
        ]
    }
    
    def __init__(self):
        """Initialize predictive suggester."""
        logger.info("PredictiveSuggester initialized")
    
    def get_suggestions(
        self,
        context: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[str]:
        """
        Get query suggestions.
        
        Args:
            context: Optional context (previous query)
            category: Optional category filter
            limit: Maximum suggestions
            
        Returns:
            List of suggested questions
        """
        suggestions = []
        
        if category and category in self.SUGGESTED_QUESTIONS:
            suggestions.extend(self.SUGGESTED_QUESTIONS[category])
        else:
            # Return mix from all categories
            for cat_suggestions in self.SUGGESTED_QUESTIONS.values():
                suggestions.extend(cat_suggestions[:1])
        
        return suggestions[:limit]
    
    def get_follow_up_questions(self, previous_query: str) -> List[str]:
        """
        Get follow-up question suggestions based on previous query.
        
        Args:
            previous_query: Previous user query
            
        Returns:
            List of follow-up questions
        """
        query_lower = previous_query.lower()
        
        # Detect topic from previous query
        if "unemployment" in query_lower:
            return [
                "What are the trends in unemployment over the past year?",
                "Which sectors have the highest unemployment rates?",
                "How can we reduce unemployment in Qatar?",
            ]
        
        elif "qatarization" in query_lower or "nationalization" in query_lower:
            return [
                "Which sectors are meeting Qatarization targets?",
                "What policies can improve Qatarization rates?",
                "How does Qatar compare to other GCC countries on nationalization?",
            ]
        
        elif "skills" in query_lower or "training" in query_lower:
            return [
                "What training programs are most effective?",
                "Which skills are projected to be in high demand?",
                "How can we close the skills gap faster?",
            ]
        
        elif "vision 2030" in query_lower:
            return [
                "What are the biggest obstacles to Vision 2030 goals?",
                "Are we on track for 2030 employment targets?",
                "What sectors need the most focus for Vision 2030?",
            ]
        
        else:
            return [
                "Show me an executive summary of Qatar's labour market",
                "What are the top workforce challenges?",
                "How is the economy performing?",
            ]
    
    def get_trending_queries(self) -> List[str]:
        """
        Get trending query suggestions.
        
        Returns:
            List of trending questions
        """
        return [
            "What is Qatar's current unemployment rate?",
            "How is Vision 2030 workforce progress?",
            "What are the critical skills gaps?",
            "How does Qatar compare to GCC countries?",
            "What sectors are growing the fastest?",
        ]


# Global suggester instance
_suggester: Optional[PredictiveSuggester] = None


def get_suggester() -> PredictiveSuggester:
    """Get or create global suggester instance."""
    global _suggester
    if _suggester is None:
        _suggester = PredictiveSuggester()
    return _suggester


def get_suggestions(category: Optional[str] = None, limit: int = 5) -> List[str]:
    """
    Convenience function for getting suggestions.
    
    Args:
        category: Optional category filter
        limit: Maximum suggestions
        
    Returns:
        List of suggested questions
    """
    suggester = get_suggester()
    return suggester.get_suggestions(category=category, limit=limit)
