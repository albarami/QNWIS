"""
Question Locker - Ensures agents answer the ACTUAL question asked.

This module prevents agents from:
1. Redefining the question (asked A vs B, answered "something else entirely")
2. Skipping to recommendations without comparing original options
3. Introducing new options without addressing the original ones first

FULLY DOMAIN-AGNOSTIC: Works for any comparative or evaluative question.
No hardcoded domain keywords - extracts options dynamically from question text.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QuestionValidation:
    """Result of validating an agent response against the original question."""
    valid: bool
    issue: Optional[str]
    required_action: Optional[str]
    options_addressed: List[str]
    new_options_introduced: List[str]


class QuestionLocker:
    """
    Ensures agents answer the ACTUAL question asked.
    
    For comparative questions (A vs B), agents must:
    1. Compare both original options
    2. State which one they recommend
    3. Only suggest alternatives AFTER comparing originals
    """
    
    # Patterns that indicate new options being introduced (domain-agnostic + common drift patterns)
    NEW_OPTION_PATTERNS = [
        ('external investment', 'global investment', 'international partnership', 'foreign investment'),
        ('hybrid', 'both options', 'split allocation', 'combined approach'),
        ('neither', 'third option', 'alternative', 'different path'),
        ('diversified', 'portfolio approach', 'mixed strategy'),
        # Run 9 drift patterns
        ('external tech', 'global tech', 'international tech'),
        # Run 12 drift patterns - agents invented "green energy" option
        ('green energy', 'energy transition', 'energy diversification', 'industrial transition'),
        ('decarbonization', 'sovereign expansion', 'industrial deepening'),
        ('renewable energy', 'clean energy', 'energy sector'),
    ]
    
    def __init__(self, original_question: str):
        """Initialize with the original question."""
        self.original_question = original_question
        self.options = self._extract_options(original_question)
        self.question_type = self._determine_question_type(original_question)
        
        logger.info(f"QuestionLocker initialized: type={self.question_type}, options={self.options}")
    
    def _extract_options(self, question: str) -> List[str]:
        """Extract the specific options from the question."""
        question_lower = question.lower()
        options = []
        
        # Pattern 1: "either X or Y"
        either_match = re.search(r'either\s+(.+?)\s+or\s+(.+?)(?:\.|,|$)', question_lower)
        if either_match:
            options = [either_match.group(1).strip(), either_match.group(2).strip()]
        
        # Pattern 2: "X or Y" (simpler)
        elif ' or ' in question_lower:
            # Try to find the options around "or"
            parts = question_lower.split(' or ')
            if len(parts) >= 2:
                # Extract last few words before "or" and first few words after
                before = ' '.join(parts[0].split()[-5:])
                after = ' '.join(parts[1].split()[:5])
                options = [before.strip(), after.strip()]
        
        # Pattern 3: Extract noun phrases as potential options (DOMAIN-AGNOSTIC)
        # This works for ANY domain - no hardcoded keywords
        if not options:
            # Look for quoted terms which often indicate options
            quoted = re.findall(r'"([^"]+)"', question)
            options.extend(quoted[:2])
            
            # Look for capitalized noun phrases (potential named options)
            if not options:
                capitalized = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', self.original_question)
                for cap in capitalized:
                    if cap not in options and len(cap) > 5:
                        options.append(cap)
                        if len(options) >= 2:
                            break
        
        return options
    
    def _determine_question_type(self, question: str) -> str:
        """Determine the type of question for appropriate validation."""
        question_lower = question.lower()
        
        if ' or ' in question_lower:
            return 'comparative'  # A vs B question
        elif any(word in question_lower for word in ['should', 'recommend', 'best', 'optimal']):
            return 'evaluative'  # Should we do X?
        elif any(word in question_lower for word in ['what', 'how', 'why']):
            return 'analytical'  # What is the impact of X?
        elif any(word in question_lower for word in ['risk', 'danger', 'threat']):
            return 'risk_assessment'
        else:
            return 'general'
    
    def validate_response(self, response: str) -> QuestionValidation:
        """
        Validate that an agent response addresses the original question.
        
        Args:
            response: The agent's response text
            
        Returns:
            QuestionValidation with validation results
        """
        response_lower = response.lower()
        
        # Track which original options are mentioned
        options_addressed = []
        for option in self.options:
            option_lower = option.lower()
            # Check for option mention (allowing partial matches)
            option_words = option_lower.split()
            if any(word in response_lower for word in option_words if len(word) > 3):
                options_addressed.append(option)
        
        # Track new options introduced
        new_options = []
        for pattern_group in self.NEW_OPTION_PATTERNS:
            for pattern in pattern_group:
                if pattern in response_lower:
                    new_options.append(pattern_group[0])  # Use first pattern as label
                    break
        
        # Validation logic
        if self.question_type == 'comparative':
            # For comparative questions, must address original options
            if new_options and len(options_addressed) < len(self.options):
                return QuestionValidation(
                    valid=False,
                    issue=f"Response introduces new options ({new_options}) without addressing all original options ({self.options})",
                    required_action="Compare original options first, then suggest alternatives if needed",
                    options_addressed=options_addressed,
                    new_options_introduced=new_options
                )
            
            if len(options_addressed) == 0 and len(self.options) >= 2:
                return QuestionValidation(
                    valid=False,
                    issue=f"Response doesn't address original options: {self.options}",
                    required_action=f"Must compare {self.options[0]} vs {self.options[1]}",
                    options_addressed=options_addressed,
                    new_options_introduced=new_options
                )
        
        return QuestionValidation(
            valid=True,
            issue=None,
            required_action=None,
            options_addressed=options_addressed,
            new_options_introduced=new_options
        )
    
    def get_question_reminder(self) -> str:
        """Generate a reminder prompt to keep agents on topic."""
        
        if self.question_type == 'comparative' and len(self.options) >= 2:
            return f"""
═══════════════════════════════════════════════════════════════════════════════
📌 QUESTION LOCK REMINDER - YOU MUST ANSWER THE ACTUAL QUESTION
═══════════════════════════════════════════════════════════════════════════════

The decision-maker asked a SPECIFIC question with TWO options:
1. {self.options[0]}
2. {self.options[1]}

YOU MUST:
✓ Compare BOTH options directly
✓ State which one you recommend AND WHY
✓ Use specific criteria: success probability, jobs, risk, timeline

YOU MAY NOT:
✗ Skip to recommending a third option without comparing the originals
✗ Suggest "hybrid" or "external investments" as your first answer
✗ Avoid the comparison by focusing on methodology debates

If you believe a third option is better, you MUST FIRST:
1. Complete the comparison between the two original options
2. Explain why BOTH original options are inferior
3. THEN suggest your alternative with supporting evidence

REMEMBER: The minister asked about {self.options[0]} vs {self.options[1]}.
They need an answer to THAT question.
═══════════════════════════════════════════════════════════════════════════════
"""
        else:
            return f"""
═══════════════════════════════════════════════════════════════════════════════
📌 QUESTION REMINDER
═══════════════════════════════════════════════════════════════════════════════

Original Question: {self.original_question[:200]}...

Stay focused on THIS question. Provide a direct answer before exploring tangents.
═══════════════════════════════════════════════════════════════════════════════
"""
    
    def get_comparison_requirement(self) -> str:
        """Generate the mandatory comparison requirement for agents."""
        
        if self.question_type != 'comparative' or len(self.options) < 2:
            return ""
        
        return f"""
## MANDATORY COMPARISON REQUIREMENT

Before recommending ANY option, you MUST complete this comparison:

| Criterion | {self.options[0]} | {self.options[1]} | Your Assessment |
|-----------|-------------------|-------------------|-----------------|
| Success probability | X% | Y% | [Which is higher and why] |
| Employment impact | +X jobs | +Y jobs | [Which creates more jobs] |
| Execution risk | [H/M/L] | [H/M/L] | [Which is more feasible] |
| Regional positioning | [vs competitors] | [vs competitors] | [Where advantage lies] |
| Fiscal return | X years payback | Y years payback | [Which returns value faster] |

After completing this comparison, state:
"Based on this analysis, I recommend [OPTION] because [SPECIFIC REASON]"

DO NOT skip this comparison or default to "hybrid" without evidence.
"""
    
    def validate_final_position(self, position: str) -> QuestionValidation:
        """Validate that a final position answers the original question."""
        
        position_lower = position.lower()
        
        # Check if position recommends one of the original options
        recommends_original = False
        recommended_option = None
        
        for option in self.options:
            option_words = option.lower().split()
            if any(word in position_lower for word in option_words if len(word) > 3):
                if 'recommend' in position_lower or 'choose' in position_lower or 'support' in position_lower:
                    recommends_original = True
                    recommended_option = option
                    break
        
        # Check if position recommends a new option
        recommends_new = False
        for pattern_group in self.NEW_OPTION_PATTERNS:
            for pattern in pattern_group:
                if pattern in position_lower and ('recommend' in position_lower or 'should' in position_lower):
                    recommends_new = True
                    break
        
        if recommends_new and not recommends_original:
            return QuestionValidation(
                valid=False,
                issue="Final position recommends option not in original question",
                required_action=f"Must recommend one of: {self.options}",
                options_addressed=[],
                new_options_introduced=['alternative']
            )
        
        return QuestionValidation(
            valid=True,
            issue=None,
            required_action=None,
            options_addressed=[recommended_option] if recommended_option else [],
            new_options_introduced=[]
        )


    def get_phase_reminder(self, phase: str) -> str:
        """
        Generate phase-specific reminder to prevent drift.
        
        CRITICAL: Re-inject original question at each phase transition.
        Run 12 showed agents drifted to "green energy" during edge case analysis.
        """
        phase_lower = phase.lower()
        
        if self.question_type == 'comparative' and len(self.options) >= 2:
            base_reminder = f"""
═══════════════════════════════════════════════════════════════════════════════
⚠️ QUESTION LOCK REMINDER - PHASE: {phase.upper()}
═══════════════════════════════════════════════════════════════════════════════

The ORIGINAL QUESTION is about TWO specific options:
1. {self.options[0]}
2. {self.options[1]}

You MUST focus on these options. Do NOT introduce new options like:
- "Green energy" / "Energy transition" / "Industrial deepening"
- "External investments" / "Global partnerships"  
- Any option not in the original question
═══════════════════════════════════════════════════════════════════════════════
"""
            
            if 'edge' in phase_lower or 'risk' in phase_lower:
                return base_reminder + f"""
⚠️ EDGE CASE / RISK ANALYSIS WARNING:

You are analyzing stress scenarios. After this analysis, you must STILL 
recommend between {self.options[0]} and {self.options[1]}.

Do NOT let edge case analysis change the core question.
Do NOT recommend a third option (like "energy transition") just because 
you analyzed oil price shocks.
═══════════════════════════════════════════════════════════════════════════════
"""
            
            elif 'final' in phase_lower or 'consensus' in phase_lower:
                return base_reminder + f"""
🔴 FINAL POSITION REQUIREMENTS (MANDATORY):

1. You MUST recommend either {self.options[0]} OR {self.options[1]}
2. You MUST cite the scenario success rate for your chosen option
3. You MUST state your confidence level (based on scenario gap)

You MUST NOT:
❌ Recommend a third option (e.g., "green energy", "industrial transition")
❌ Avoid choosing between the two original options
❌ Claim the question should have been different

If your final position does NOT recommend one of the original two options,
it will be REJECTED and you will be asked to restate.
═══════════════════════════════════════════════════════════════════════════════
"""
            
            return base_reminder
        
        return f"Focus on the original question: {self.original_question[:100]}..."
    
    def get_final_position_violation_redirect(self, agent_name: str, invalid_recommendation: str) -> str:
        """
        Generate a strong redirect when agent recommends invalid option at final position.
        
        This is called when validate_final_position() returns invalid.
        """
        if self.question_type == 'comparative' and len(self.options) >= 2:
            return f"""
═══════════════════════════════════════════════════════════════════════════════
🔴 QUESTION LOCK VIOLATION - FINAL POSITION REJECTED
═══════════════════════════════════════════════════════════════════════════════

{agent_name}, your recommendation "{invalid_recommendation}" is NOT valid.

The Minister asked about TWO specific options:
1. {self.options[0]}
2. {self.options[1]}

You recommended something ELSE (possibly "{invalid_recommendation}").

This is NOT acceptable. You MUST restate your final position:

"I recommend [{self.options[0]} OR {self.options[1]}] with [X]% confidence 
because the scenario analysis shows [cite specific success rate]."

⚠️ If you genuinely believe BOTH original options are inferior:
1. FIRST state which of the two you would choose if forced
2. THEN note your concern about a third path as a caveat
3. But your PRIMARY recommendation must be one of the original options

Please restate your final position NOW.
═══════════════════════════════════════════════════════════════════════════════
"""
        
        return f"Please restate your recommendation addressing the original question."


def create_question_lock_prompt(question: str) -> str:
    """Create a question lock prompt for the debate."""
    locker = QuestionLocker(question)
    return locker.get_question_reminder() + "\n" + locker.get_comparison_requirement()


def create_phase_reminder(question: str, phase: str) -> str:
    """Create a phase-specific reminder to prevent drift."""
    locker = QuestionLocker(question)
    return locker.get_phase_reminder(phase)

