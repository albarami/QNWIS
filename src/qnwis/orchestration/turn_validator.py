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
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TurnValidator:
    """
    Validates debate turns before they're added to the transcript.
    
    Domain-agnostic: Works for any policy question type.
    
    Enhanced with:
    - Contradiction detection
    - Ping-pong pattern detection
    - Methodology ratio checking
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
        
        # Track cited statistics for contradiction detection
        self.cited_statistics: Dict[str, Dict] = {}  # metric_key -> {value, agent, turn}
        
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

    def validate_with_context(
        self,
        turn_content: str,
        agent_name: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> Dict:
        """
        Validate turn with contradiction detection.
        
        Args:
            turn_content: The content to validate
            agent_name: Name of the agent (for tracking)
            turn_number: Turn number (for tracking)
            
        Returns:
            dict with keys:
                - valid: bool
                - issues: list[str]
                - suggestion: str or None
                - contradictions: list[str] (any detected contradictions)
        """
        # Start with basic validation
        result = self.validate(turn_content)
        result['contradictions'] = []
        
        # Detect contradictions if we have context
        if agent_name and turn_number:
            contradictions = self._detect_contradictions(agent_name, turn_number, turn_content)
            if contradictions:
                result['contradictions'] = contradictions
                result['issues'].append(f"Contradicts previously cited statistics: {len(contradictions)} conflicts")
                result['valid'] = False
        
        # Detect ping-pong pattern
        if self._is_ping_pong(turn_content):
            result['issues'].append("Turn uses excessive 'I concede but maintain' patterns")
            result['valid'] = False
        
        return result
    
    def _detect_contradictions(
        self,
        agent_name: str,
        turn_number: int,
        turn_content: str
    ) -> List[str]:
        """
        Detect if this turn contradicts previously cited statistics.
        
        Returns list of contradiction warnings.
        """
        warnings = []
        
        # Extract percentage patterns with context
        patterns = [
            r'(\w+(?:\s+\w+)*?)\s+(?:grew|growth|increased|rose|is|was|at)\s*(?:by\s*)?(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s+(growth|increase|rate|participation)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, turn_content.lower())
            for match in matches:
                # Extract components
                try:
                    if isinstance(match[0], str) and isinstance(match[1], str):
                        context_words = match[0] if not match[0].replace('.', '').isdigit() else match[1]
                        pct_str = match[1] if match[0] == context_words else match[0]
                        pct_value = float(pct_str)
                        
                        if not (0 < pct_value < 100):
                            continue
                            
                        # Create metric key from context
                        metric_key = self._normalize_metric(context_words)
                        
                        if metric_key and len(metric_key) > 3:
                            existing = self.cited_statistics.get(metric_key)
                            
                            if existing:
                                diff = abs(float(existing['value']) - pct_value)
                                if diff > 2.0:  # More than 2% absolute difference
                                    warnings.append(
                                        f"'{metric_key}': {agent_name} cited {pct_value}% but "
                                        f"{existing['agent']} cited {existing['value']}% (Turn {existing['turn']})"
                                    )
                            else:
                                # First citation - record it
                                self.cited_statistics[metric_key] = {
                                    'value': pct_value,
                                    'agent': agent_name,
                                    'turn': turn_number
                                }
                except (ValueError, IndexError, TypeError):
                    continue
        
        return warnings
    
    def _normalize_metric(self, context: str) -> str:
        """Normalize context to a metric key."""
        key_terms = []
        
        important = [
            'employment', 'growth', 'rate', 'participation', 'unemployment',
            'gdp', 'revenue', 'investment', 'productivity', 'output', 'workforce',
            'national', 'ict', 'tourism', 'sector', 'annual', 'absorption'
        ]
        
        context_lower = context.lower()
        for term in important:
            if term in context_lower:
                key_terms.append(term)
        
        return '_'.join(sorted(key_terms[:3]))
    
    def _is_ping_pong(self, content: str) -> bool:
        """Detect 'I concede but maintain' ping-pong patterns."""
        content_lower = content.lower()
        
        ping_pong_phrases = [
            'i concede that', 'i partially concede', 'i concede but',
            'i agree, however', 'that is correct, but', 'i acknowledge, but',
            'however, i maintain', 'nonetheless, i stand by', 'that said, i still'
        ]
        
        matches = sum(1 for phrase in ping_pong_phrases if phrase in content_lower)
        return matches >= 2

