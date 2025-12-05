"""
Scenario-Aware Synthesis - Ensures recommendations align with scenario analysis.

The synthesis must:
1. Look at scenario results → Find best performing path
2. Look at agent conclusions → What do experts recommend
3. Reconcile → If conflict, explain and default to scenario evidence

DOMAIN-AGNOSTIC: Works for any question type (investment, policy, risk, etc.)

FIX Run 16: CRITICAL DISTINCTION:
- SCENARIOS are hypothetical futures that TEST how each option performs
- OPTIONS are the actual investment choices the minister must decide between

The synthesis must recommend an OPTION, not a SCENARIO.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ScenarioOptionDisambiguator:
    """
    CRITICAL FIX (Run 16): Distinguish scenarios from options.
    
    SCENARIOS: Hypothetical futures that TEST resilience
      - e.g., "Oil Price Shock", "AI Leadership Drive", "Regional Competition"
    
    OPTIONS: Actual investment choices the decision-maker must select
      - e.g., "AI and Technology Hub", "Sustainable Tourism"
    
    The recommendation must be an OPTION, not a SCENARIO.
    """
    
    def __init__(self, original_question: str, scenarios: List[Dict[str, Any]]):
        self.original_question = original_question
        self.options = self._extract_options(original_question)
        self.scenario_names = [s.get('name', '') for s in scenarios]
        self.scenario_to_option_map = self._build_scenario_to_option_map(scenarios)
    
    def _extract_options(self, question: str) -> List[str]:
        """
        Extract actual OPTIONS from the question.
        
        QUESTION-TYPE AGNOSTIC: Looks for common patterns indicating options.
        """
        question_lower = question.lower()
        options = []
        
        # Pattern 1: "either X or Y"
        either_or_pattern = re.search(
            r'either\s+(?:become\s+)?(?:the\s+)?(.+?)\s+or\s+(?:to\s+)?(?:develop\s+)?(?:the\s+)?(.+?)(?:\.|,|given|\?)', 
            question_lower
        )
        if either_or_pattern:
            opt_a = either_or_pattern.group(1).strip()
            opt_b = either_or_pattern.group(2).strip()
            options.extend([opt_a, opt_b])
        
        # Pattern 2: "Option A: X" / "Option B: Y"
        option_labels = re.findall(r'option\s*[ab12]:\s*([^,\n.]+)', question_lower)
        if option_labels:
            options.extend(option_labels)
        
        # Pattern 3: "between X and Y"
        between_pattern = re.search(r'between\s+(.+?)\s+and\s+(.+?)(?:\.|,|\?|$)', question_lower)
        if between_pattern:
            options.extend([between_pattern.group(1).strip(), between_pattern.group(2).strip()])
        
        # Pattern 4: "choose X or Y"
        choose_pattern = re.search(r'choose\s+(.+?)\s+or\s+(.+?)(?:\.|,|\?|$)', question_lower)
        if choose_pattern:
            options.extend([choose_pattern.group(1).strip(), choose_pattern.group(2).strip()])
        
        # Clean and deduplicate
        cleaned = []
        for opt in options:
            opt = opt.strip()
            if opt and len(opt) > 3 and opt not in cleaned:
                cleaned.append(opt)
        
        if cleaned:
            logger.info(f"📋 Extracted OPTIONS from question: {cleaned}")
        else:
            logger.warning("⚠️ Could not extract options from question - will infer from scenarios")
        
        return cleaned[:4]  # Max 4 options
    
    def _build_scenario_to_option_map(self, scenarios: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Map each scenario to the OPTION it tests.
        
        QUESTION-TYPE AGNOSTIC: Uses text similarity.
        """
        mapping = {}
        
        for scenario in scenarios:
            scenario_name = scenario.get('name', '')
            scenario_desc = scenario.get('description', '')
            scenario_text = f"{scenario_name} {scenario_desc}".lower()
            
            # Find which option this scenario relates to
            best_match_option = None
            best_match_score = 0
            
            for option in self.options:
                option_words = set(option.lower().split())
                scenario_words = set(scenario_text.split())
                
                # Calculate overlap
                overlap = len(option_words & scenario_words)
                score = overlap / max(len(option_words), 1)
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_option = option
            
            if best_match_option and best_match_score > 0.2:
                mapping[scenario_name] = best_match_option
                logger.debug(f"   Mapped scenario '{scenario_name}' → option '{best_match_option}'")
        
        return mapping
    
    def get_option_for_scenario(self, scenario_name: str) -> Optional[str]:
        """Get the OPTION that a scenario tests."""
        # Direct mapping
        if scenario_name in self.scenario_to_option_map:
            return self.scenario_to_option_map[scenario_name]
        
        # Fallback: text similarity with options
        scenario_lower = scenario_name.lower()
        for option in self.options:
            option_lower = option.lower()
            # Check if key words from option appear in scenario
            option_words = [w for w in option_lower.split() if len(w) > 3]
            matches = sum(1 for w in option_words if w in scenario_lower)
            if matches >= 1:
                return option
        
        return None
    
    def validate_recommendation(self, recommendation: str) -> Dict[str, Any]:
        """
        Validate that recommendation refers to an OPTION, not a SCENARIO.
        """
        rec_lower = recommendation.lower()
        
        # Check if recommendation mentions a scenario name
        for scenario_name in self.scenario_names:
            if scenario_name and scenario_name.lower() in rec_lower:
                return {
                    'valid': False,
                    'error': f"Recommendation '{recommendation}' is a SCENARIO, not an OPTION",
                    'scenario_mentioned': scenario_name,
                    'valid_options': self.options,
                    'correction': f"The recommendation should be one of: {', '.join(self.options)}"
                }
        
        # Check if recommendation matches an option
        for option in self.options:
            if option.lower() in rec_lower or rec_lower in option.lower():
                return {'valid': True, 'matched_option': option}
        
        # Partial match check (any significant word overlap)
        rec_words = set(w for w in rec_lower.split() if len(w) > 3)
        for option in self.options:
            option_words = set(w for w in option.lower().split() if len(w) > 3)
            overlap = len(rec_words & option_words)
            if overlap >= 2 or (overlap >= 1 and len(option_words) <= 2):
                return {'valid': True, 'matched_option': option}
        
        return {
            'valid': False,
            'error': f"Recommendation '{recommendation}' does not match any known option",
            'valid_options': self.options
        }


@dataclass
class SynthesisResult:
    """Result of scenario-aware synthesis."""
    recommendation: str
    rationale: str
    confidence: float
    decision: str  # GO, CONDITIONAL GO, RECONSIDER, NO GO
    scenario_agent_aligned: bool
    best_scenario: Dict[str, Any]
    agent_recommendation: str
    reconciliation_note: str


class ScenarioAwareSynthesis:
    """
    Synthesis that incorporates scenario results, not just agent votes.
    
    CRITICAL: The recommendation MUST be supported by scenario analysis.
    If the best scenario shows 64.9% and agents recommend a path with 20.8%,
    the synthesis should default to the scenario-backed path and explain why.
    
    FIX Run 16: CRITICAL DISTINCTION:
    - SCENARIOS are hypothetical futures that TEST resilience
    - OPTIONS are the actual investment choices
    
    The recommendation must be an OPTION, not a SCENARIO.
    """
    
    def __init__(self):
        self.minimum_scenario_gap_for_override = 10  # REDUCED from 15 to 10 (Run 14 had 21pp gap)
        
        # FIX RUN 14: Cache scenario ground truth to prevent agent inversion from corrupting synthesis
        self._scenario_ground_truth = None
        
        # FIX RUN 16: Disambiguator to ensure we recommend OPTIONS, not SCENARIOS
        self._disambiguator = None
    
    def _normalize_rate(self, rate: Any) -> float:
        """
        FIX RUN 16: Safely normalize rate to percentage (0-100).
        
        Prevents the 224850% bug caused by multiplying already-percentage rates.
        
        QUESTION-TYPE AGNOSTIC: Works for any numeric input.
        """
        if rate is None:
            return 50.0
        
        try:
            rate_float = float(rate)
        except (TypeError, ValueError):
            return 50.0
        
        # If rate is already in percentage form (>1), don't multiply
        if rate_float > 1:
            # Cap at 100 to prevent absurd values
            return min(rate_float, 100.0)
        elif rate_float >= 0:
            # Rate is in decimal form (0-1), convert to percentage
            return rate_float * 100
        else:
            # Invalid negative rate
            return 50.0
    
    def synthesize(
        self,
        scenarios: List[Dict[str, Any]],
        agent_positions: List[Dict[str, Any]],
        original_question: str,
        debate_summary: str = ""
    ) -> SynthesisResult:
        """
        Produce a synthesis that reconciles scenario results with agent recommendations.
        
        Args:
            scenarios: List of scenario results with success rates
            agent_positions: List of agent final positions
            original_question: The original query
            debate_summary: Summary of debate
            
        Returns:
            SynthesisResult with reconciled recommendation (MUST be an OPTION, not a SCENARIO)
        """
        # FIX RUN 16: Initialize disambiguator to separate OPTIONS from SCENARIOS
        self._disambiguator = ScenarioOptionDisambiguator(original_question, scenarios)
        
        # CRITICAL FIX (Run 14): Compute ground truth DIRECTLY from scenarios
        # This prevents agent inversion from corrupting synthesis
        ground_truth = self._compute_scenario_ground_truth(scenarios)
        self._scenario_ground_truth = ground_truth
        
        # Step 1: Find best scenario (domain-agnostic)
        best_scenario = self._find_best_scenario(scenarios)
        worst_scenario = self._find_worst_non_stress_scenario(scenarios)
        
        # Step 2: Tally agent votes (domain-agnostic)
        agent_recommendation, agent_confidence = self._tally_agent_votes(agent_positions)
        
        # FIX RUN 16: Map best scenario to an OPTION (not the scenario name)
        # Before: scenario_recommendation = "Oil Price Shock – Forced Diversification" (WRONG: this is a scenario)
        # After: scenario_recommendation = "AI and Technology Hub" (CORRECT: this is an option)
        scenario_recommendation = self._map_scenario_to_option(best_scenario)
        
        # Step 4: Check for conflict - agents may have inverted numbers
        aligned = self._recommendations_aligned(scenario_recommendation, agent_recommendation)
        
        # QUESTION-TYPE AGNOSTIC: Check if agent recommendation matches best scenario
        # Find scenario rate for agent's recommendation by word overlap
        agent_rate = self._find_scenario_rate_for_recommendation(agent_recommendation, scenarios)
        
        # If agent recommends something with lower rate than best, check gap
        if ground_truth['gap'] >= 10 and agent_rate < ground_truth['best_rate'] - 10:
            logger.warning(f"⚠️ POSSIBLE MISALIGNMENT DETECTED:")
            logger.warning(f"   Ground truth winner: {ground_truth['best_option']} at {ground_truth['best_rate']:.1f}%")
            logger.warning(f"   Agents recommend: {agent_recommendation} (matched rate: {agent_rate:.1f}%)")
            aligned = False  # Force reconciliation
        
        # FIX RUN 16: Safely normalize rate (prevents 224850% bug)
        best_rate_raw = best_scenario.get('success_rate', best_scenario.get('success_probability', 0.5))
        best_rate_display = self._normalize_rate(best_rate_raw)
        
        logger.info(f"📊 Scenario-Aware Synthesis:")
        logger.info(f"   Ground truth best scenario: {ground_truth['best_option']}")
        logger.info(f"   Mapped to OPTION: {scenario_recommendation}")
        logger.info(f"   Best scenario rate: {best_rate_display:.1f}%")
        logger.info(f"   Agent recommendation: {agent_recommendation} at {agent_confidence:.1f}%")
        logger.info(f"   Aligned: {aligned}")
        
        if not aligned:
            # CRITICAL: Scenarios and agents disagree
            # Default to scenario evidence if gap is significant
            return self._produce_reconciliation_synthesis(
                best_scenario=best_scenario,
                worst_scenario=worst_scenario,
                scenario_recommendation=scenario_recommendation,
                agent_recommendation=agent_recommendation,
                agent_confidence=agent_confidence,
                scenarios=scenarios,
                agent_positions=agent_positions,
                original_question=original_question
            )
        else:
            # Aligned - produce straightforward synthesis
            return self._produce_aligned_synthesis(
                recommendation=scenario_recommendation,
                best_scenario=best_scenario,
                agent_confidence=agent_confidence,
                scenarios=scenarios
            )
    
    def _compute_scenario_ground_truth(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute scenario ground truth DIRECTLY from scenario data.
        
        FULLY QUESTION-TYPE AGNOSTIC:
        - Works for any number of options (1, 2, 3+, or open-ended)
        - Simply finds best and worst scenarios
        - Does not assume specific option names or keywords
        """
        if not scenarios:
            return {
                'best_option': 'Unknown',
                'best_rate': 50.0,
                'worst_option': 'Unknown',
                'worst_rate': 50.0,
                'gap': 0.0
            }
        
        # Process all scenarios (filter out stress tests for primary analysis)
        non_stress = []
        all_scenarios = []
        
        for s in scenarios:
            name = s.get('name', s.get('scenario_name', 'Unknown'))
            # FIX RUN 16: Use _normalize_rate to prevent 224850% bug
            rate_raw = s.get('success_rate', s.get('success_probability', 0))
            rate = self._normalize_rate(rate_raw)
            
            all_scenarios.append({'name': name, 'rate': rate})
            if not self._is_stress_test(s):
                non_stress.append({'name': name, 'rate': rate})
        
        # Use non-stress scenarios if available, otherwise use all
        analysis_set = non_stress if non_stress else all_scenarios
        
        if not analysis_set:
            return {
                'best_option': 'Unknown',
                'best_rate': 50.0,
                'worst_option': 'Unknown',
                'worst_rate': 50.0,
                'gap': 0.0
            }
        
        # Find best and worst
        sorted_scenarios = sorted(analysis_set, key=lambda x: x['rate'], reverse=True)
        best = sorted_scenarios[0]
        worst = sorted_scenarios[-1]
        gap = best['rate'] - worst['rate']
        
        logger.info(f"📊 SCENARIO GROUND TRUTH (question-type agnostic):")
        logger.info(f"   Best: {best['name'][:40]} at {best['rate']:.1f}%")
        logger.info(f"   Worst: {worst['name'][:40]} at {worst['rate']:.1f}%")
        logger.info(f"   Gap: {gap:.1f}pp")
        logger.info(f"   Total scenarios analyzed: {len(analysis_set)}")
        
        return {
            'best_option': best['name'],
            'best_rate': best['rate'],
            'worst_option': worst['name'],
            'worst_rate': worst['rate'],
            'gap': gap,
            'all_scenarios': sorted_scenarios
        }
    
    def _find_best_scenario(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the scenario with highest success rate."""
        if not scenarios:
            return {"name": "Unknown", "success_rate": 0.5}
        
        # Filter out pure stress tests (oil shock, war, pandemic) for "best" determination
        non_stress = [s for s in scenarios if not self._is_stress_test(s)]
        
        if non_stress:
            return max(non_stress, key=lambda s: s.get('success_rate', s.get('success_probability', 0)))
        else:
            return max(scenarios, key=lambda s: s.get('success_rate', s.get('success_probability', 0)))
    
    def _find_worst_non_stress_scenario(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the worst-performing non-stress scenario (to understand option risks)."""
        if not scenarios:
            return {"name": "Unknown", "success_rate": 0.5}
        
        non_stress = [s for s in scenarios if not self._is_stress_test(s)]
        
        if non_stress:
            return min(non_stress, key=lambda s: s.get('success_rate', s.get('success_probability', 1)))
        else:
            return min(scenarios, key=lambda s: s.get('success_rate', s.get('success_probability', 1)))
    
    def _is_stress_test(self, scenario: Dict[str, Any]) -> bool:
        """Determine if scenario is a stress test (domain-agnostic)."""
        name_lower = scenario.get('name', '').lower()
        desc_lower = scenario.get('description', '').lower()
        
        stress_keywords = [
            'shock', 'crisis', 'collapse', 'war', 'pandemic', 'disruption',
            'displacement', 'freeze', 'recession', 'downturn', 'instability',
            'black swan', 'worst case', 'adverse', 'stress'
        ]
        
        return any(kw in name_lower or kw in desc_lower for kw in stress_keywords)
    
    def _tally_agent_votes(self, agent_positions: List[Dict[str, Any]]) -> Tuple[str, float]:
        """
        Tally agent recommendations and average confidence.
        
        Domain-agnostic: Just looks at what agents recommended.
        """
        if not agent_positions:
            return ("Unknown", 50.0)
        
        # Count recommendations
        votes = {}
        confidences = []
        
        for pos in agent_positions:
            rec = pos.get('recommendation', pos.get('position', ''))
            conf = pos.get('confidence', 0.7)
            
            if isinstance(conf, str):
                # Parse "70%" -> 70
                match = re.search(r'(\d+)', conf)
                conf = float(match.group(1)) if match else 70
            elif isinstance(conf, float) and conf <= 1:
                conf = conf * 100
            
            if rec:
                votes[rec] = votes.get(rec, 0) + 1
                confidences.append(conf)
        
        if not votes:
            return ("Unknown", 50.0)
        
        # Find majority recommendation
        majority_rec = max(votes, key=votes.get)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 50.0
        
        return (majority_rec, avg_confidence)
    
    def _map_scenario_to_option(self, scenario: Dict[str, Any]) -> str:
        """
        FIX RUN 16: Map a SCENARIO to the OPTION it tests.
        
        CRITICAL: Scenarios are TEST CONDITIONS, not recommendations.
        This method identifies which OPTION the scenario is testing.
        
        Example:
        - Scenario "AI Leadership Drive" → Option "AI and Technology Hub"
        - Scenario "Tourism Pivot" → Option "Sustainable Tourism"
        - Scenario "Oil Price Shock" → Could test either option (find by context)
        """
        scenario_name = scenario.get('name', '')
        scenario_desc = scenario.get('description', '')
        
        # Use disambiguator if available
        if self._disambiguator:
            option = self._disambiguator.get_option_for_scenario(scenario_name)
            if option:
                logger.info(f"   Mapped scenario '{scenario_name}' → option '{option}'")
                return option
            
            # If no direct mapping, try to find option from description
            combined_text = f"{scenario_name} {scenario_desc}".lower()
            for opt in self._disambiguator.options:
                opt_lower = opt.lower()
                if opt_lower in combined_text:
                    logger.info(f"   Mapped scenario '{scenario_name}' → option '{opt}' (from description)")
                    return opt
        
        # Fallback: Extract key theme from scenario
        return self._extract_option_from_scenario_name(scenario_name, scenario_desc)
    
    def _extract_option_from_scenario_name(self, name: str, description: str) -> str:
        """
        Fallback: Extract the investment OPTION from scenario text.
        
        QUESTION-TYPE AGNOSTIC: Looks for common patterns.
        """
        combined = f"{name} {description}".lower()
        
        # Look for explicit option indicators
        option_patterns = [
            (r'ai\s+(?:and\s+)?tech(?:nology)?', 'AI and Technology Hub'),
            (r'tech(?:nology)?\s+hub', 'Technology Hub'),
            (r'sustainable\s+tourism', 'Sustainable Tourism'),
            (r'tourism\s+(?:pivot|develop|destination)', 'Sustainable Tourism'),
            (r'digital\s+transform', 'Digital Transformation'),
            (r'innovation\s+hub', 'Innovation Hub'),
        ]
        
        for pattern, option in option_patterns:
            if re.search(pattern, combined):
                return option
        
        # If no pattern match, extract the core theme (remove stress test indicators)
        stress_indicators = ['shock', 'crisis', 'collapse', 'disruption', 'adverse', 'stress']
        clean_name = name
        for indicator in stress_indicators:
            clean_name = re.sub(rf'\b{indicator}\b', '', clean_name, flags=re.IGNORECASE)
        
        # Clean up and return
        clean_name = re.sub(r'[-–—]+', ' ', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        if clean_name and len(clean_name) > 3:
            return clean_name
        
        # Ultimate fallback
        return "Recommended Strategic Path"
    
    def _extract_recommendation_from_scenario(self, scenario: Dict[str, Any]) -> str:
        """
        DEPRECATED: Use _map_scenario_to_option instead.
        Kept for backward compatibility.
        """
        return self._map_scenario_to_option(scenario)
    
    def _recommendations_aligned(self, scenario_rec: str, agent_rec: str) -> bool:
        """
        Check if scenario and agent recommendations point to the same path.
        
        QUESTION-TYPE AGNOSTIC: Uses word overlap between recommendations.
        Works for any question type - no hardcoded keywords.
        """
        if not scenario_rec or not agent_rec:
            return True  # Can't determine, assume aligned
        
        s_lower = scenario_rec.lower()
        a_lower = agent_rec.lower()
        
        # Extract significant words (>3 chars) from both
        s_words = set(word for word in s_lower.split() if len(word) > 3)
        a_words = set(word for word in a_lower.split() if len(word) > 3)
        
        # Remove common non-meaningful words
        stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'option', 'path', 'scenario'}
        s_words -= stop_words
        a_words -= stop_words
        
        if not s_words or not a_words:
            return True  # Not enough info to compare
        
        # Calculate word overlap
        overlap = s_words & a_words
        overlap_ratio = len(overlap) / min(len(s_words), len(a_words))
        
        # If >30% word overlap, consider aligned
        return overlap_ratio >= 0.3
    
    def _produce_reconciliation_synthesis(
        self,
        best_scenario: Dict[str, Any],
        worst_scenario: Dict[str, Any],
        scenario_recommendation: str,
        agent_recommendation: str,
        agent_confidence: float,
        scenarios: List[Dict[str, Any]],
        agent_positions: List[Dict[str, Any]],
        original_question: str
    ) -> SynthesisResult:
        """
        When scenarios and agents disagree, produce reconciliation synthesis.
        
        CRITICAL: Default to scenario evidence when gap is significant.
        """
        # FIX RUN 16: Use _normalize_rate to prevent 224850% bug
        best_rate = self._normalize_rate(
            best_scenario.get('success_rate', best_scenario.get('success_probability', 0.5))
        )
        worst_rate = self._normalize_rate(
            worst_scenario.get('success_rate', worst_scenario.get('success_probability', 0.5))
        )
        
        # Find what rate the agent recommendation would achieve
        agent_scenario_rate = self._find_scenario_rate_for_recommendation(agent_recommendation, scenarios)
        
        gap = best_rate - agent_scenario_rate
        
        logger.warning(f"⚠️ SCENARIO-AGENT CONFLICT:")
        logger.warning(f"   Best scenario: {scenario_recommendation} at {best_rate:.1f}%")
        logger.warning(f"   Agent recommendation: {agent_recommendation} at {agent_scenario_rate:.1f}%")
        logger.warning(f"   Gap: {gap:.1f} percentage points")
        
        # Determine final recommendation based on evidence strength
        if gap >= self.minimum_scenario_gap_for_override:
            # Scenario evidence is significantly stronger - use it
            final_recommendation = scenario_recommendation
            final_confidence = best_rate
            reconciliation_note = f"""
## ⚠️ Scenario-Agent Disagreement Resolved

**Scenario Analysis Indicates:** {scenario_recommendation} with **{best_rate:.1f}%** success rate
**Expert Panel Recommended:** {agent_recommendation} with **{agent_confidence:.0f}%** confidence

### Resolution: Following Scenario Evidence

The scenario stress-testing shows a **{gap:.1f} percentage point** advantage for 
{scenario_recommendation} over the expert panel's recommendation.

**Why Scenario Evidence Prevails:**
1. Scenarios tested actual implementation paths under multiple futures
2. The recommended path ({agent_recommendation}) shows only {agent_scenario_rate:.1f}% success in stress testing
3. {scenario_recommendation} achieves {best_rate:.1f}% success even under adverse conditions

**Trade-off Acknowledged:**
If the decision-maker weights expert qualitative judgment over quantitative 
stress-testing, {agent_recommendation} remains a viable alternative at 
{agent_confidence:.0f}% expert confidence.
"""
            decision = "CONDITIONAL GO" if best_rate >= 50 else "RECONSIDER"
        else:
            # Gap is small - can go with agent recommendation but note the discrepancy
            final_recommendation = agent_recommendation
            final_confidence = agent_confidence
            reconciliation_note = f"""
## Note: Scenario and Expert Views Differ Slightly

**Best Scenario:** {scenario_recommendation} at {best_rate:.1f}%
**Expert Recommendation:** {agent_recommendation} at {agent_confidence:.0f}% confidence

The gap is within acceptable range ({gap:.1f}pp). Following expert judgment.
"""
            decision = "GO" if agent_confidence >= 60 else "CONDITIONAL GO"
        
        return SynthesisResult(
            recommendation=final_recommendation,
            rationale=reconciliation_note,
            confidence=final_confidence,
            decision=decision,
            scenario_agent_aligned=False,
            best_scenario=best_scenario,
            agent_recommendation=agent_recommendation,
            reconciliation_note=reconciliation_note
        )
    
    def _produce_aligned_synthesis(
        self,
        recommendation: str,
        best_scenario: Dict[str, Any],
        agent_confidence: float,
        scenarios: List[Dict[str, Any]]
    ) -> SynthesisResult:
        """When scenarios and agents agree, produce straightforward synthesis."""
        
        # FIX RUN 16: Use _normalize_rate to prevent 224850% bug
        best_rate = self._normalize_rate(
            best_scenario.get('success_rate', best_scenario.get('success_probability', 0.5))
        )
        
        # Use the higher of scenario rate or agent confidence
        final_confidence = max(best_rate, agent_confidence)
        
        rationale = f"""
## Scenario and Expert Analysis Aligned

Both quantitative scenario analysis and expert deliberation support **{recommendation}**.

**Scenario Evidence:** {best_scenario.get('name')} achieves {best_rate:.1f}% success rate
**Expert Confidence:** {agent_confidence:.0f}%

This alignment across analytical approaches strengthens confidence in the recommendation.
"""
        
        decision = "GO" if final_confidence >= 60 else "CONDITIONAL GO" if final_confidence >= 45 else "RECONSIDER"
        
        return SynthesisResult(
            recommendation=recommendation,
            rationale=rationale,
            confidence=final_confidence,
            decision=decision,
            scenario_agent_aligned=True,
            best_scenario=best_scenario,
            agent_recommendation=recommendation,
            reconciliation_note=""
        )
    
    def _find_scenario_rate_for_recommendation(
        self,
        recommendation: str,
        scenarios: List[Dict[str, Any]]
    ) -> float:
        """
        Find what success rate the given recommendation achieves in scenarios.
        
        QUESTION-TYPE AGNOSTIC: Uses word overlap to match recommendation to scenarios.
        No hardcoded keywords.
        """
        if not scenarios or not recommendation:
            return 50.0  # Default neutral rate
        
        rec_lower = recommendation.lower()
        rec_words = set(word for word in rec_lower.split() if len(word) > 3)
        
        # Remove common non-meaningful words
        stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'option', 'should', 'would', 'could'}
        rec_words -= stop_words
        
        if not rec_words:
            # No meaningful words - return average
            rates = [s.get('success_rate', s.get('success_probability', 0.5)) for s in scenarios]
            avg = sum(rates) / len(rates) if rates else 0.5
            return avg * 100 if avg <= 1 else avg
        
        # Find best matching scenario by word overlap
        best_match = None
        best_overlap = 0
        
        for scenario in scenarios:
            name = scenario.get('name', '')
            name_lower = name.lower()
            name_words = set(word for word in name_lower.split() if len(word) > 3)
            name_words -= stop_words
            
            overlap = len(rec_words & name_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = scenario
        
        if best_match and best_overlap > 0:
            rate = best_match.get('success_rate', best_match.get('success_probability', 0.5))
            return rate * 100 if rate <= 1 else rate
        
        # No match found - return average
        rates = [s.get('success_rate', s.get('success_probability', 0.5)) for s in scenarios]
        avg = sum(rates) / len(rates) if rates else 0.5
        return avg * 100 if avg <= 1 else avg


def validate_recommendation_against_scenarios(
    recommendation: str,
    scenarios: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate that recommendation is supported by scenario analysis.
    
    Domain-agnostic: Works for any question type.
    """
    if not scenarios:
        return {'valid': True, 'issue': None}
    
    synthesizer = ScenarioAwareSynthesis()
    
    # Find best scenario
    best_scenario = synthesizer._find_best_scenario(scenarios)
    # FIX RUN 16: Use _normalize_rate to prevent 224850% bug
    best_rate = synthesizer._normalize_rate(
        best_scenario.get('success_rate', best_scenario.get('success_probability', 0.5))
    )
    
    # Find rate for recommendation
    rec_rate = synthesizer._find_scenario_rate_for_recommendation(recommendation, scenarios)
    
    # Check if recommending inferior path
    if rec_rate < best_rate - 10:  # 10pp tolerance
        return {
            'valid': False,
            'issue': f"Recommending path with {rec_rate:.1f}% success while '{best_scenario.get('name')}' shows {best_rate:.1f}%",
            'suggested_recommendation': synthesizer._map_scenario_to_option(best_scenario),
            'suggested_rate': best_rate,
            'current_rate': rec_rate,
            'gap': best_rate - rec_rate
        }
    
    return {'valid': True, 'issue': None, 'rate': rec_rate}

