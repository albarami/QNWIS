"""
Turn Validator for debate quality control.

Validates debate turns before they're added to the transcript.
Checks for:
- Minimum substantive length
- Excessive methodology content
- Non-committal hedging

This is an optional quality gate that can log issues or force retries.
"""

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


class TurnValidator:
    """
    Validates debate turns before they're added to the transcript.
    
    Domain-agnostic: Works for any policy question type.
    """
    
    def __init__(self, original_question: str):
        """
        Initialize the turn validator.
        
        Args:
            original_question: The minister's question being debated
        """
        self.original_question = original_question
        self.min_turn_length = 200  # Minimum substantive response
        self.max_methodology_ratio = 0.4  # Max 40% methodology content
        
    def validate(self, turn_content: str) -> Dict:
        """
        Validate a turn.
        
        Args:
            turn_content: The content to validate
            
        Returns:
            dict with keys:
                - valid: bool
                - issues: list[str]
                - suggestion: str or None
        """
        issues = []
        
        # Skip validation for short system messages
        if turn_content.startswith('⚖️') or turn_content.startswith('📌'):
            return {'valid': True, 'issues': [], 'suggestion': None}
        
        # Check minimum length
        if len(turn_content) < self.min_turn_length:
            issues.append('Turn is too brief to be substantive')
        
        # Check for empty conclusions
        if self._is_non_committal(turn_content):
            issues.append('Turn avoids taking a position')
        
        # Check methodology ratio
        methodology_ratio = self._methodology_ratio(turn_content)
        if methodology_ratio > self.max_methodology_ratio:
            issues.append(f'Turn is primarily methodology discussion ({methodology_ratio:.0%})')
        
        result = {
            'valid': len(issues) == 0,
            'issues': issues,
            'suggestion': self._generate_suggestion(issues) if issues else None
        }
        
        if issues:
            logger.warning(f"Turn validation issues: {issues}")
        
        return result
    
    def _is_non_committal(self, content: str) -> bool:
        """
        Check if turn avoids taking a clear position.
        
        Returns True if the turn contains excessive hedging without conclusions.
        """
        content_lower = content.lower()
        
        # Non-committal phrases that avoid decisions
        non_committal_phrases = [
            'it depends', 'more data is needed', 'further analysis required',
            'cannot determine', 'insufficient evidence', 'remains unclear',
            'both options have merit', 'either could work', 'hard to say',
            'need more information', 'difficult to assess', 'uncertain',
            'too early to tell', 'requires further study', 'inconclusive'
        ]
        
        # Commitment phrases that show a position
        commitment_phrases = [
            'recommend', 'suggest', 'conclude', 'therefore', 'thus',
            'should', 'prefer', 'better option', 'higher probability',
            'evidence shows', 'data indicates', 'analysis suggests',
            'my assessment', 'my recommendation', 'in conclusion'
        ]
        
        non_committal_count = sum(1 for phrase in non_committal_phrases if phrase in content_lower)
        commitment_count = sum(1 for phrase in commitment_phrases if phrase in content_lower)
        
        # If more non-committal than committal, and at least 2 non-committal, flag it
        return non_committal_count >= 2 and non_committal_count > commitment_count
    
    def _methodology_ratio(self, content: str) -> float:
        """
        Estimate what fraction of content is methodology discussion.
        
        Returns float 0-1 representing methodology proportion.
        """
        methodology_terms = [
            'data', 'measure', 'statistic', 'coefficient', 'variable',
            'indicator', 'metric', 'methodology', 'approach', 'framework',
            'classification', 'category', 'aggregate', 'disaggregate',
            'granular', 'satellite', 'account', 'benchmark', 'survey',
            'sample', 'estimate', 'regression', 'correlation', 'variance',
            'input-output', 'leontief', 'matrix', 'table'
        ]
        
        words = content.lower().split()
        if len(words) == 0:
            return 0
        
        methodology_words = 0
        for word in words:
            for term in methodology_terms:
                if term in word:
                    methodology_words += 1
                    break
        
        return methodology_words / len(words)
    
    def _generate_suggestion(self, issues: List[str]) -> str:
        """
        Generate a suggestion for improving the turn.
        
        Args:
            issues: List of identified issues
            
        Returns:
            Suggestion string for agent
        """
        issues_str = ' '.join(issues).lower()
        
        if 'methodology' in issues_str:
            return (
                "Reduce methodology discussion. State your conclusion and focus on "
                "the decision implications. The minister needs a recommendation, not "
                "a data quality audit."
            )
        
        if 'position' in issues_str or 'non-committal' in issues_str:
            return (
                "Take a clear position. The minister needs a recommendation, not hedging. "
                "State your view with a confidence level (e.g., '75% confident that Option A "
                "is better because...')."
            )
        
        if 'brief' in issues_str:
            return (
                "Expand your analysis with specific evidence and quantified impacts. "
                "Provide at least 2-3 paragraphs with data citations."
            )
        
        return "Refocus on directly answering the minister's question with a clear recommendation."
    
    def get_retry_prompt(self, original_content: str, issues: List[str]) -> str:
        """
        Generate a prompt for retrying a failed turn.
        
        Args:
            original_content: The original turn content
            issues: List of identified issues
            
        Returns:
            Prompt for retry
        """
        suggestion = self._generate_suggestion(issues)
        question_display = self.original_question[:300] if len(self.original_question) > 300 else self.original_question
        
        return f"""Your previous response had quality issues: {', '.join(issues)}

SUGGESTION: {suggestion}

ORIGINAL QUESTION: "{question_display}"

Please provide a revised response that:
1. Takes a CLEAR position with confidence level
2. Focuses on the DECISION, not methodology
3. Provides SPECIFIC recommendations with evidence

Revised response:"""

