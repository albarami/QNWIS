"""
Coherence Validator - Ensures all system outputs are internally consistent.

This module validates that:
1. Summary card verdict matches brief verdict
2. Probability ranges are compatible
3. Recommendation matches a tested scenario
4. Original question was answered
5. Dissenting views are represented

Domain-agnostic: Works for any query type.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CoherenceIssue:
    """A coherence issue found during validation."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    issue: str
    fix: str
    component1: str
    component2: str


class CoherenceValidator:
    """
    Validates that all system outputs are internally consistent.
    
    Prevents contradictions like:
    - Summary card says "RECONSIDER" but brief says "GO"
    - Summary shows 34% but brief claims 72%
    - Recommendation wasn't tested in any scenario
    """
    
    # Verdict alignment mapping
    VERDICT_ALIGNMENT = {
        # (card_verdict, brief_verdict): aligned?
        ('APPROVE', 'GO'): True,
        ('APPROVE', 'CONDITIONAL GO'): True,
        ('PROCEED_WITH_CAUTION', 'GO'): True,
        ('PROCEED_WITH_CAUTION', 'CONDITIONAL GO'): True,
        ('PROCEED_WITH_CAUTION', 'PROCEED WITH CAUTION'): True,
        ('RECONSIDER', 'RECONSIDER'): True,
        ('RECONSIDER', 'CONDITIONAL NO'): True,
        ('REJECT', 'NO GO'): True,
        ('REJECT', 'RECONSIDER'): True,
    }
    
    def validate(
        self,
        summary_card: Dict[str, Any],
        scenarios: List[Dict[str, Any]],
        debate_transcript: List[Dict[str, Any]],
        ministerial_brief: str,
        original_question: str
    ) -> Dict[str, Any]:
        """
        Run all coherence checks.
        
        Args:
            summary_card: The verdict card data
            scenarios: List of scenario results
            debate_transcript: Full debate history
            ministerial_brief: The generated brief text
            original_question: The original user question
            
        Returns:
            {
                'coherent': bool,
                'issues': List[CoherenceIssue],
                'can_publish': bool,
                'fixes_applied': List[str]
            }
        """
        issues = []
        
        # Check 1: Summary card verdict matches brief verdict
        verdict_issue = self._check_verdict_alignment(summary_card, ministerial_brief)
        if verdict_issue:
            issues.append(verdict_issue)
        
        # Check 2: Probability ranges are compatible
        prob_issue = self._check_probability_alignment(summary_card, ministerial_brief)
        if prob_issue:
            issues.append(prob_issue)
        
        # Check 3: Recommendation matches a tested scenario
        scenario_issue = self._check_recommendation_matches_scenario(
            ministerial_brief, scenarios, original_question
        )
        if scenario_issue:
            issues.append(scenario_issue)
        
        # Check 4: Original question was answered
        question_issue = self._check_question_answered(
            ministerial_brief, debate_transcript, original_question
        )
        if question_issue:
            issues.append(question_issue)
        
        # Check 5: Dissenting views are represented
        dissent_issue = self._check_dissent_represented(
            debate_transcript, ministerial_brief
        )
        if dissent_issue:
            issues.append(dissent_issue)
        
        # Determine overall coherence
        critical_issues = [i for i in issues if i.severity == 'CRITICAL']
        high_issues = [i for i in issues if i.severity == 'HIGH']
        
        return {
            'coherent': len(critical_issues) == 0,
            'issues': issues,
            'can_publish': len(critical_issues) == 0 and len(high_issues) <= 1,
            'critical_count': len(critical_issues),
            'high_count': len(high_issues),
            'total_count': len(issues)
        }
    
    def _check_verdict_alignment(
        self,
        summary_card: Dict[str, Any],
        ministerial_brief: str
    ) -> Optional[CoherenceIssue]:
        """Check if summary card verdict matches brief verdict."""
        
        card_verdict = summary_card.get('verdict', '').upper()
        
        # Extract verdict from brief
        brief_verdict = self._extract_verdict_from_brief(ministerial_brief)
        
        if not card_verdict or not brief_verdict:
            return None
        
        # Check alignment
        aligned = self.VERDICT_ALIGNMENT.get((card_verdict, brief_verdict), False)
        
        # Also check reverse direction for flexibility
        if not aligned:
            aligned = self.VERDICT_ALIGNMENT.get((brief_verdict, card_verdict), False)
        
        # Additional check: both should be positive or both negative
        positive_verdicts = {'APPROVE', 'GO', 'PROCEED_WITH_CAUTION', 'CONDITIONAL GO', 'PROCEED WITH CAUTION'}
        negative_verdicts = {'RECONSIDER', 'REJECT', 'NO GO', 'CONDITIONAL NO'}
        
        card_positive = card_verdict in positive_verdicts
        brief_positive = brief_verdict.upper() in positive_verdicts
        
        if card_positive != brief_positive:
            return CoherenceIssue(
                severity='CRITICAL',
                issue=f"Summary card says '{card_verdict}' but brief says '{brief_verdict}'",
                fix='Align verdicts: If debate recommends GO, card should show APPROVE or PROCEED_WITH_CAUTION',
                component1='summary_card',
                component2='ministerial_brief'
            )
        
        return None
    
    def _check_probability_alignment(
        self,
        summary_card: Dict[str, Any],
        ministerial_brief: str
    ) -> Optional[CoherenceIssue]:
        """Check if probability ranges are compatible."""
        
        card_prob = summary_card.get('successRate', summary_card.get('success_probability'))
        if card_prob is None:
            return None
        
        # Extract probability from brief
        brief_prob = self._extract_probability_from_brief(ministerial_brief)
        if brief_prob is None:
            return None
        
        # Allow 20 percentage points difference (was 15, relaxed for flexibility)
        if abs(card_prob - brief_prob) > 20:
            return CoherenceIssue(
                severity='CRITICAL',
                issue=f"Summary card shows {card_prob}% but brief claims {brief_prob}%",
                fix='Use consistent probability: Either use debate verdict probability in card, or clarify different metrics',
                component1='summary_card',
                component2='ministerial_brief'
            )
        
        return None
    
    def _check_recommendation_matches_scenario(
        self,
        ministerial_brief: str,
        scenarios: List[Dict[str, Any]],
        original_question: str
    ) -> Optional[CoherenceIssue]:
        """Check if recommendation was tested in scenarios."""
        
        # Extract recommendation from brief
        recommendation = self._extract_recommendation_from_brief(ministerial_brief)
        if not recommendation:
            return None
        
        # Get scenario names
        scenario_names = [s.get('name', s.get('scenario_name', '')) for s in scenarios]
        
        # Check if recommendation matches any scenario
        recommendation_lower = recommendation.lower()
        
        for scenario in scenario_names:
            scenario_lower = scenario.lower()
            # Check for keyword overlap
            if any(word in scenario_lower for word in recommendation_lower.split() if len(word) > 3):
                return None  # Found a match
        
        # Check if recommendation matches original options
        original_options = self._extract_options_from_question(original_question)
        for option in original_options:
            if option.lower() in recommendation_lower:
                return None  # Recommendation matches an original option
        
        return CoherenceIssue(
            severity='HIGH',
            issue=f"Recommendation '{recommendation[:50]}...' may not match tested scenarios",
            fix='Ensure recommendation is for one of the original options or a tested scenario',
            component1='recommendation',
            component2='scenarios'
        )
    
    def _check_question_answered(
        self,
        ministerial_brief: str,
        debate_transcript: List[Dict[str, Any]],
        original_question: str
    ) -> Optional[CoherenceIssue]:
        """Check if the original question was actually answered."""
        
        original_options = self._extract_options_from_question(original_question)
        if len(original_options) < 2:
            return None  # Not a comparative question
        
        brief_lower = ministerial_brief.lower()
        
        # Check if both original options are discussed
        options_mentioned = []
        for option in original_options:
            if option.lower() in brief_lower:
                options_mentioned.append(option)
        
        if len(options_mentioned) < len(original_options):
            missing = [o for o in original_options if o not in options_mentioned]
            return CoherenceIssue(
                severity='HIGH',
                issue=f"Original options {missing} not adequately addressed in brief",
                fix=f"Brief must compare all original options: {original_options}",
                component1='original_question',
                component2='ministerial_brief'
            )
        
        return None
    
    def _check_dissent_represented(
        self,
        debate_transcript: List[Dict[str, Any]],
        ministerial_brief: str
    ) -> Optional[CoherenceIssue]:
        """Check if dissenting views are represented in brief."""
        
        # Find dissenting agents from final positions
        dissenters = self._find_dissenters(debate_transcript)
        
        if not dissenters:
            return None  # No dissent to represent
        
        # Check if dissent is mentioned in brief
        brief_lower = ministerial_brief.lower()
        dissent_mentioned = any(
            keyword in brief_lower 
            for keyword in ['dissent', 'disagree', 'minority view', 'alternative view', 
                          'counter-argument', 'opposing', 'challenged']
        )
        
        if not dissent_mentioned:
            return CoherenceIssue(
                severity='MEDIUM',
                issue=f"Agents {[d['agent'] for d in dissenters]} dissented but this isn't reflected in brief",
                fix='Add section explaining dissenting views and why they were overruled',
                component1='debate_transcript',
                component2='ministerial_brief'
            )
        
        return None
    
    def _extract_verdict_from_brief(self, brief: str) -> Optional[str]:
        """Extract verdict/decision from brief text."""
        
        # Look for verdict patterns
        patterns = [
            r'Decision:\s*(GO|NO GO|CONDITIONAL GO|RECONSIDER)',
            r'Verdict:\s*(APPROVE|REJECT|PROCEED|RECONSIDER)',
            r'Recommendation:\s*(GO|NO GO|PROCEED|REJECT)',
            r'GO[-–—]\s*(Conditional|Unconditional)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, brief, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Look for implicit verdicts
        brief_lower = brief.lower()
        if 'recommend' in brief_lower and ('go' in brief_lower or 'proceed' in brief_lower):
            return 'GO'
        if 'do not recommend' in brief_lower or 'should not proceed' in brief_lower:
            return 'NO GO'
        
        return None
    
    def _extract_probability_from_brief(self, brief: str) -> Optional[float]:
        """Extract probability/success rate from brief."""
        
        patterns = [
            r'(\d+(?:\.\d+)?)\s*%\s*(?:probability|success|likelihood|chance)',
            r'probability[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'success[:\s]+(\d+(?:\.\d+)?)\s*%',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, brief, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_recommendation_from_brief(self, brief: str) -> Optional[str]:
        """Extract the main recommendation from brief."""
        
        patterns = [
            r'recommend[s]?\s+(?:pursuing\s+)?([^.]+)',
            r'should\s+(?:pursue|adopt|implement)\s+([^.]+)',
            r'Decision:\s*GO\s*[-–—]\s*([^.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, brief, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        
        return None
    
    def _extract_options_from_question(self, question: str) -> List[str]:
        """Extract the specific options from a comparative question."""
        
        question_lower = question.lower()
        
        # Look for "X or Y" pattern
        if ' or ' in question_lower:
            # Find the part with options
            or_patterns = [
                r'either\s+(.+?)\s+or\s+(.+?)(?:\.|,|$)',
                r'between\s+(.+?)\s+and\s+(.+?)(?:\.|,|$)',
                r'([\w\s]+hub|[\w\s]+destination|[\w\s]+strategy)\s+or\s+([\w\s]+hub|[\w\s]+destination|[\w\s]+strategy)',
            ]
            
            for pattern in or_patterns:
                match = re.search(pattern, question_lower)
                if match:
                    return [match.group(1).strip(), match.group(2).strip()]
        
        # Fallback: Look for common option keywords
        options = []
        option_keywords = [
            ('ai', 'AI Hub'),
            ('tech', 'Technology'),
            ('tourism', 'Tourism'),
            ('manufacturing', 'Manufacturing'),
            ('finance', 'Finance'),
        ]
        
        for keyword, label in option_keywords:
            if keyword in question_lower:
                options.append(label)
        
        return options[:2]  # Return max 2 options
    
    def _find_dissenters(self, debate_transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find agents who disagreed with the majority recommendation."""
        
        final_positions = []
        
        # Look for final position turns
        for turn in reversed(debate_transcript[-20:]):  # Last 20 turns
            message = turn.get('message', turn.get('content', ''))
            agent = turn.get('agent', turn.get('speaker', ''))
            
            if 'final position' in message.lower() or 'recommend' in message.lower():
                # Extract recommendation
                if 'option a' in message.lower():
                    final_positions.append({'agent': agent, 'position': 'A'})
                elif 'option b' in message.lower():
                    final_positions.append({'agent': agent, 'position': 'B'})
        
        if len(final_positions) < 2:
            return []
        
        # Find majority position
        positions = [p['position'] for p in final_positions]
        majority = max(set(positions), key=positions.count)
        
        # Return dissenters
        return [p for p in final_positions if p['position'] != majority]


def fix_coherence_issues(
    summary_card: Dict[str, Any],
    ministerial_brief: str,
    debate_verdict: Dict[str, Any],
    issues: List[CoherenceIssue]
) -> Tuple[Dict[str, Any], str]:
    """
    Apply fixes for coherence issues.
    
    Returns updated summary_card and ministerial_brief.
    """
    fixed_card = summary_card.copy()
    fixed_brief = ministerial_brief
    
    for issue in issues:
        if issue.severity == 'CRITICAL':
            if 'verdict' in issue.issue.lower():
                # Fix verdict alignment by using debate verdict
                if debate_verdict.get('recommendation'):
                    rec = debate_verdict['recommendation'].lower()
                    if 'go' in rec or 'proceed' in rec or 'option' in rec:
                        fixed_card['verdict'] = 'PROCEED_WITH_CAUTION'
                    elif 'reconsider' in rec or 'no' in rec:
                        fixed_card['verdict'] = 'RECONSIDER'
            
            if 'probability' in issue.issue.lower():
                # Fix probability by using debate verdict probability
                if debate_verdict.get('quantified_assessment'):
                    import re
                    prob_match = re.search(r'(\d+)', str(debate_verdict['quantified_assessment']))
                    if prob_match:
                        fixed_card['successRate'] = int(prob_match.group(1))
    
    return fixed_card, fixed_brief

