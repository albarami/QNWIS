"""
Smart Moderator for content-based debate intervention.

Instead of intervening every N turns, the SmartModerator evaluates each turn
and intervenes when:
- Methodology tangents are detected (I-O tables, Leontief, etc.)
- Repetition is detected (same points made multiple times)
- Topic drift is detected (low relevance to original question)

This ensures the debate stays focused on helping the minister make a decision.
"""

import logging
import re
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


class SmartModerator:
    """
    Moderator that intervenes based on debate quality, not just turn count.
    
    Domain-agnostic: Works for any policy question type (binary, open, single-option).
    """
    
    def __init__(self, original_question: str):
        """
        Initialize the smart moderator.
        
        Args:
            original_question: The minister's question being debated
        """
        self.original_question = original_question
        self.question_keywords = self._extract_keywords(original_question)
        self.turns_since_progress = 0
        self.max_turns_without_progress = 5  # Intervene after 5 stagnant turns
        self.methodology_warning_issued = False
        self.repetition_warning_issued = False
        self._intervention_count = 0
        
        # Track consecutive methodology turns for spiral detection
        self.consecutive_methodology_turns = 0
        self.max_consecutive_methodology = 3  # Intervene after 3 consecutive methodology turns
        
        # Track cited statistics for contradiction detection
        self.cited_statistics: Dict[str, Dict] = {}  # metric -> {value, agent, turn}
        
        logger.info(f"SmartModerator initialized with {len(self.question_keywords)} question keywords")
    
    def _extract_keywords(self, question: str) -> Set[str]:
        """
        Extract key concepts from the question for relevance checking.
        
        Domain-agnostic: Works for any policy question.
        """
        # Common stopwords to filter out
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'or', 'and', 'to', 'of', 'in', 'for', 
            'by', 'with', 'which', 'what', 'how', 'should', 'would', 'could', 
            'given', 'our', 'their', 'this', 'that', 'these', 'those', 'from',
            'into', 'upon', 'about', 'between', 'during', 'before', 'after',
            'above', 'below', 'under', 'over', 'through', 'than', 'more', 'most',
            'some', 'any', 'each', 'every', 'both', 'either', 'neither', 'whether',
            'while', 'during', 'consider', 'considering', 'regarding', 'offers',
            'highest', 'lowest', 'best', 'worst', 'strategic', 'path', 'long-term'
        }
        
        # Split on whitespace and punctuation
        words = re.split(r'[\s,;:!?\.\(\)\[\]\{\}]+', question.lower())
        
        # Filter: keep words with 4+ chars that aren't stopwords
        keywords = {w for w in words if len(w) >= 4 and w not in stopwords}
        
        return keywords
    
    def _detect_methodology_tangent(self, turn_content: str) -> bool:
        """
        Detect if turn is focused on methodology rather than substance.
        
        Returns True if the turn contains excessive methodology discussion.
        """
        methodology_indicators = [
            # Data methodology
            'input-output table', 'i-o table', 'i/o table', 'leontief',
            'satellite account', 'isic rev', 'classification system',
            'data granularity', 'disaggregat', 'methodolog',
            
            # Statistical methodology
            'econometric', 'coefficient', 'elasticity estimate',
            'statistical significance', 'regression', 'correlation matrix',
            'confidence interval', 'p-value', 'standard error',
            
            # Data quality debates
            'whether the data', 'sufficiently granular', 'data limitation',
            'measurement approach', 'accounting framework', 'benchmark data',
            'data quality', 'data availability', 'data source reliability',
            
            # Academic tangents
            'literature suggests', 'theoretical framework', 'academic consensus',
            'epistemological', 'ontological', 'methodological debate'
        ]
        
        content_lower = turn_content.lower()
        methodology_mentions = sum(1 for ind in methodology_indicators if ind in content_lower)
        
        # If more than 3 methodology terms in one turn, it's a tangent
        is_tangent = methodology_mentions >= 3
        
        if is_tangent:
            logger.warning(f"Methodology tangent detected: {methodology_mentions} indicators found")
        
        return is_tangent
    
    def _detect_repetition(self, turn_content: str, previous_turns: List[Dict]) -> bool:
        """
        Detect if turn repeats points already made.
        
        Returns True if the turn contains significant repetition.
        """
        if len(previous_turns) < 3:
            return False
        
        # Get recent content (last 5 turns, excluding Moderator turns)
        recent_content = []
        for t in previous_turns[-7:]:
            agent = t.get('agent', '')
            if agent != 'Moderator':
                msg = t.get('message', '')[:500]
                recent_content.append(msg.lower())
        
        if not recent_content:
            return False
        
        recent_text = ' '.join(recent_content)
        
        # Check for repeated phrases (sentences > 50 chars)
        turn_sentences = [s.strip() for s in turn_content.split('.') if len(s.strip()) > 50]
        
        repeated = 0
        for sentence in turn_sentences:
            sentence_lower = sentence.lower()
            # Check if significant portion of sentence appears in recent turns
            words = sentence_lower.split()
            if len(words) >= 8:
                # Check for 8-word sequences
                for i in range(len(words) - 7):
                    phrase = ' '.join(words[i:i+8])
                    if phrase in recent_text:
                        repeated += 1
                        break
        
        is_repetitive = repeated >= 2
        
        if is_repetitive:
            logger.warning(f"Repetition detected: {repeated} repeated phrases")
        
        return is_repetitive
    
    def _check_question_relevance(self, turn_content: str) -> float:
        """
        Score how relevant the turn is to the original question (0-1).
        
        Domain-agnostic: Uses keyword matching and decision language detection.
        """
        content_lower = turn_content.lower()
        
        # Check for question keywords
        keyword_hits = sum(1 for kw in self.question_keywords if kw in content_lower)
        keyword_score = min(keyword_hits / max(len(self.question_keywords), 1), 1.0)
        
        # Check for decision-focused language
        decision_terms = [
            'recommend', 'suggest', 'prefer', 'better option', 'higher probability',
            'more likely', 'should choose', 'optimal', 'advantage', 'disadvantage',
            'risk', 'opportunity', 'trade-off', 'compared to', 'versus', 'alternatively',
            'therefore', 'conclude', 'assessment', 'in conclusion', 'verdict',
            'success rate', 'probability of', 'confidence', 'likelihood',
            'minister', 'decision', 'strategy', 'policy implication'
        ]
        decision_hits = sum(1 for term in decision_terms if term in content_lower)
        decision_score = min(decision_hits / 3, 1.0)
        
        # Combine scores (decision language matters more)
        relevance = (keyword_score * 0.4) + (decision_score * 0.6)
        
        return relevance
    
    def evaluate_turn(
        self, 
        turn_content: str, 
        previous_turns: List[Dict],
        agent_name: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> Dict:
        """
        Evaluate a debate turn and decide if intervention is needed.
        
        Args:
            turn_content: The content of the current turn
            previous_turns: List of previous debate turns
            agent_name: Name of the agent (for contradiction tracking)
            turn_number: Current turn number (for contradiction tracking)
            
        Returns:
            dict with keys:
                - should_intervene: bool
                - intervention_type: str or None
                - intervention_message: str or None
                - contradiction_warnings: list (if any contradictions detected)
        """
        result = {
            'should_intervene': False,
            'intervention_type': None,
            'intervention_message': None,
            'contradiction_warnings': []
        }
        
        # Skip evaluation for very short turns (likely system messages)
        if len(turn_content) < 100:
            return result
        
        # Check for methodology tangent - ENHANCED with consecutive tracking
        is_methodology_turn = self._detect_methodology_tangent(turn_content)
        if is_methodology_turn:
            self.consecutive_methodology_turns += 1
            self.turns_since_progress += 1
            
            # Intervene after 3 CONSECUTIVE methodology turns (stricter than before)
            if self.consecutive_methodology_turns >= self.max_consecutive_methodology:
                result['should_intervene'] = True
                result['intervention_type'] = 'methodology_spiral'
                result['intervention_message'] = self._generate_methodology_spiral_intervention()
                self.consecutive_methodology_turns = 0  # Reset
                self._intervention_count += 1
                logger.warning(f"SmartModerator intervention #{self._intervention_count}: METHODOLOGY SPIRAL after {self.max_consecutive_methodology} consecutive turns")
                return result
        else:
            # Not a methodology turn - reset consecutive counter
            self.consecutive_methodology_turns = 0
        
        # Check for statistic contradictions (NEW)
        if agent_name and turn_number:
            contradictions = self._detect_statistic_contradictions(
                agent_name, turn_number, turn_content
            )
            if contradictions:
                result['contradiction_warnings'] = contradictions
                logger.warning(f"Contradictions detected: {contradictions}")
        
        # Check for excessive "I concede but maintain" ping-pong (NEW)
        if self._detect_ping_pong(turn_content):
            self.turns_since_progress += 1
            if self.turns_since_progress >= 3:
                result['should_intervene'] = True
                result['intervention_type'] = 'ping_pong_redirect'
                result['intervention_message'] = self._generate_ping_pong_redirect()
                self._intervention_count += 1
                logger.info(f"SmartModerator intervention #{self._intervention_count}: ping-pong redirect")
                return result
        
        # Check for repetition
        if self._detect_repetition(turn_content, previous_turns):
            self.turns_since_progress += 1
            if self.turns_since_progress >= 4 and not self.repetition_warning_issued:
                result['should_intervene'] = True
                result['intervention_type'] = 'repetition_redirect'
                result['intervention_message'] = self._generate_repetition_redirect()
                self.repetition_warning_issued = True
                self._intervention_count += 1
                logger.info(f"SmartModerator intervention #{self._intervention_count}: repetition redirect")
                return result
        
        # Check for low relevance
        relevance = self._check_question_relevance(turn_content)
        if relevance < 0.3:
            self.turns_since_progress += 1
            if self.turns_since_progress >= 5:
                result['should_intervene'] = True
                result['intervention_type'] = 'relevance_redirect'
                result['intervention_message'] = self._generate_relevance_redirect()
                self._intervention_count += 1
                logger.info(f"SmartModerator intervention #{self._intervention_count}: relevance redirect (score: {relevance:.2f})")
                return result
        else:
            # Good turn - reset counter
            self.turns_since_progress = 0
            # Reset warnings after good progress
            if relevance > 0.6:
                self.methodology_warning_issued = False
                self.repetition_warning_issued = False
        
        return result
    
    def _detect_ping_pong(self, turn_content: str) -> bool:
        """Detect 'I concede but maintain' ping-pong patterns."""
        content_lower = turn_content.lower()
        
        ping_pong_phrases = [
            'i concede that', 'i partially concede', 'i concede but',
            'i agree, however', 'that is correct, but', 'i acknowledge, but',
            'valid point, however', 'i grant that, but', 'fair point, but',
            'however, i maintain', 'nonetheless, i stand by', 'that said, i still'
        ]
        
        matches = sum(1 for phrase in ping_pong_phrases if phrase in content_lower)
        return matches >= 2  # Two or more ping-pong phrases = flag
    
    def _detect_statistic_contradictions(
        self, 
        agent_name: str, 
        turn_number: int, 
        turn_content: str
    ) -> List[str]:
        """
        Detect if this turn contradicts previously cited statistics.
        
        Returns list of contradiction warnings.
        """
        import re
        warnings = []
        
        # Extract "X%" patterns with context
        # Look for patterns like "grew 11.8%", "only 0.8%", "increased 26%"
        patterns = [
            r'(grew|growth|increased|rose|up|annual|annually|rate)\s*(?:of\s*)?(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s*(growth|increase|rise|annual)',
            r'only\s*(\d+\.?\d*)\s*%',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, turn_content.lower())
            for match in matches:
                # Extract the percentage value
                pct_value = None
                for m in match:
                    try:
                        pct_value = float(m)
                        if 0 < pct_value < 100:  # Reasonable percentage
                            break
                    except (ValueError, TypeError):
                        continue
                
                if pct_value is None:
                    continue
                
                # Get surrounding context (for metric identification)
                context_match = re.search(
                    rf'.{{0,50}}{pct_value}\s*%.{{0,30}}',
                    turn_content.lower()
                )
                if context_match:
                    context = context_match.group()
                    metric_key = self._extract_metric_key(context)
                    
                    if metric_key and len(metric_key) > 5:
                        existing = self.cited_statistics.get(metric_key)
                        
                        if existing:
                            # Check if significantly different (more than 2% absolute difference)
                            diff = abs(float(existing['value']) - pct_value)
                            if diff > 2.0:
                                warnings.append(
                                    f"CONTRADICTION: {agent_name} cited {pct_value}% for '{metric_key}', "
                                    f"but {existing['agent']} cited {existing['value']}% "
                                    f"(Turn {existing['turn']})"
                                )
                        else:
                            # First citation - record it
                            self.cited_statistics[metric_key] = {
                                'value': pct_value,
                                'agent': agent_name,
                                'turn': turn_number
                            }
        
        return warnings
    
    def _extract_metric_key(self, context: str) -> str:
        """Extract a metric key from context."""
        key_terms = []
        
        important_terms = [
            'employment', 'growth', 'rate', 'participation', 'unemployment',
            'gdp', 'revenue', 'investment', 'productivity', 'output', 'workforce',
            'national', 'ict', 'tourism', 'sector', 'annual', 'quarterly',
            'absorption', 'graduate', 'wage', 'salary', 'labor', 'labour'
        ]
        
        for term in important_terms:
            if term in context:
                key_terms.append(term)
        
        return '_'.join(sorted(key_terms[:4]))  # Max 4 terms, sorted for consistency
    
    def _generate_methodology_redirect(self) -> str:
        """Generate redirect message for methodology tangents."""
        question_display = self.original_question[:400] if len(self.original_question) > 400 else self.original_question
        
        return f"""⚖️ MODERATOR INTERVENTION — METHODOLOGY TANGENT DETECTED

The debate has spent multiple turns discussing data classification, measurement approaches, 
or statistical methodology. While methodological rigor matters, the minister needs actionable guidance.

🔴 IMMEDIATE REQUIREMENT FOR ALL AGENTS:

Your next response must:
1. STATE your conclusion on the methodology point in ONE sentence 
   (e.g., "Available data is sufficient to conclude that...")
2. THEN directly address: "{question_display}"
3. PROVIDE a specific recommendation with confidence level

❌ Do NOT continue debating data granularity or classification systems.
✅ DO provide your best assessment given available evidence.

The minister needs a decision, not a perfect dataset."""

    def _generate_methodology_spiral_intervention(self) -> str:
        """Generate HARD STOP intervention for methodology spirals."""
        question_display = self.original_question[:400] if len(self.original_question) > 400 else self.original_question
        
        return f"""⚖️ MODERATOR INTERVENTION — METHODOLOGY SPIRAL DETECTED 🛑

The debate has spent {self.max_consecutive_methodology}+ CONSECUTIVE turns debating statistics 
rather than making a strategic recommendation.

🔴 HARD STOP ON DATA DEBATES

RULING: Use approximate figures going forward. Small percentage differences 
do not change the strategic recommendation.

🔴 YOUR NEXT RESPONSE MUST:

1. STOP challenging employment/growth/participation statistics
2. DIRECTLY COMPARE the options in the original question:
   - "Option A offers [X] while Option B offers [Y]"
3. STATE which option you recommend and WHY with a probability

The minister needs a decision in the next 10 turns. No more methodology debates.

Original question: "{question_display}"

⚠️ ANY FURTHER METHODOLOGY DISCUSSION WILL BE TERMINATED."""

    def _generate_ping_pong_redirect(self) -> str:
        """Generate redirect for 'I concede but maintain' patterns."""
        question_display = self.original_question[:400] if len(self.original_question) > 400 else self.original_question
        
        return f"""⚖️ MODERATOR INTERVENTION — CIRCULAR DEBATE DETECTED

The debate is stuck in a cycle of "I concede X but maintain Y" exchanges.
Each turn must add NEW information, not just acknowledge and reassert.

🔴 REQUIREMENT FOR YOUR NEXT RESPONSE:

1. If you AGREE with a point, say "I agree" and MOVE ON
2. If you DISAGREE, provide NEW evidence (not re-stating your position)
3. If debate is stuck, propose a SYNTHESIS or COMPROMISE position

DO NOT use phrases like:
- "I concede that... but"
- "Fair point, however I maintain..."
- "I partially agree, but..."

Instead:
- Present NEW data not yet discussed
- Propose a specific recommendation with confidence level
- Move toward a VERDICT

Original question: "{question_display}"
"""

    def _generate_repetition_redirect(self) -> str:
        """Generate redirect message for repetition."""
        question_display = self.original_question[:400] if len(self.original_question) > 400 else self.original_question
        
        return f"""⚖️ MODERATOR INTERVENTION — REPETITION DETECTED

The debate is cycling through points already made. Each turn must add NEW information 
or reach NEW conclusions.

🔴 IMMEDIATE REQUIREMENT:

Your next response must either:
1. INTRODUCE new evidence not yet discussed
2. SYNTHESIZE existing points into a concrete recommendation
3. IDENTIFY a specific disagreement that needs resolution
4. MOVE TO final position if consensus is emerging

Original question: "{question_display}"

Do not restate points already made. Progress toward a verdict."""

    def _generate_relevance_redirect(self) -> str:
        """Generate redirect message for topic drift."""
        question_display = self.original_question[:400] if len(self.original_question) > 400 else self.original_question
        
        return f"""⚖️ MODERATOR INTERVENTION — OFF-TOPIC DRIFT

The debate has drifted from the minister's question. Every turn must directly help answer:

"{question_display}"

🔴 IMMEDIATE REQUIREMENT:

Your next response must:
1. BEGIN with "Regarding [specific aspect of the question]..."
2. PROVIDE analysis that directly informs the decision
3. END with a concrete implication for the recommendation

Stay focused on what the minister needs to decide."""

    def reset_warnings(self):
        """Reset warning flags (useful at phase transitions)."""
        self.methodology_warning_issued = False
        self.repetition_warning_issued = False
        self.turns_since_progress = 0
        logger.info("SmartModerator warnings reset")
    
    @property
    def intervention_count(self) -> int:
        """Return the number of interventions made."""
        return self._intervention_count

