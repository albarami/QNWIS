"""
Debate Context Generation for NSIC System.

Provides context injection for debates including:
- Consensus statistics that all agents must use
- Reference figures to prevent methodology spirals
- Phase-appropriate context

This is domain-agnostic and works for any policy question.
"""

import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def generate_consensus_statistics(
    extracted_facts: Optional[Dict] = None,
    query_classification: Optional[Dict] = None,
    domain_hints: Optional[List[str]] = None
) -> str:
    """
    Generate a set of consensus statistics that all agents must use.
    
    Prevents methodology debates about which number is correct by establishing
    agreed-upon reference figures at the start of the debate.
    
    This is DOMAIN-AGNOSTIC: it extracts relevant figures from available data
    or provides guidance on how to handle missing data.
    
    Args:
        extracted_facts: Facts extracted by the RAG layer (if available)
        query_classification: Classification of the query type
        domain_hints: Hints about the domain (e.g., ["labor", "technology"])
        
    Returns:
        Markdown-formatted consensus statistics for injection
    """
    
    if extracted_facts and len(extracted_facts) > 0:
        return _generate_from_extracted_facts(extracted_facts, query_classification)
    else:
        return _generate_generic_guidelines(query_classification, domain_hints)


def _generate_from_extracted_facts(
    facts: Dict[str, Any],
    classification: Optional[Dict] = None
) -> str:
    """Generate consensus statistics from extracted facts."""
    
    # Build table from actual extracted data
    fact_rows = []
    
    for source, data in facts.items():
        if isinstance(data, dict):
            for metric, value in data.items():
                if isinstance(value, (int, float, str)):
                    fact_rows.append(f"| {metric} | {value} | {source} |")
        elif isinstance(data, list):
            for item in data[:10]:  # Limit to first 10
                if isinstance(item, dict) and 'metric' in item:
                    fact_rows.append(f"| {item.get('metric', 'N/A')} | {item.get('value', 'N/A')} | {source} |")
    
    if fact_rows:
        table = "\n".join(fact_rows[:20])  # Limit total rows
    else:
        table = "| No specific metrics extracted | - | Data extraction pending |"
    
    return f"""
═══════════════════════════════════════════════════════════════════════
📊 AGREED REFERENCE STATISTICS — USE THESE FIGURES
═══════════════════════════════════════════════════════════════════════

These figures are extracted from the available data sources. All agents 
MUST use these figures consistently. Do NOT introduce conflicting statistics.

| Metric | Value | Source |
|--------|-------|--------|
{table}

═══════════════════════════════════════════════════════════════════════
⚠️ DATA CONSISTENCY RULES
═══════════════════════════════════════════════════════════════════════

1. USE THESE FIGURES: If a metric above is relevant, cite it exactly.

2. IF YOU CITE A NEW STATISTIC: Ensure it doesn't contradict the above.
   - If it does, explicitly state: "Newer data shows X (vs. Y above)"
   - Then use the newer figure consistently for the rest of the debate

3. IF DATA IS MISSING: Say "NOT IN DATA" and provide qualitative analysis.
   Do NOT fabricate statistics.

4. MAXIMUM 1 TURN on any data discrepancy. State which figure you trust
   and move to the strategic decision.

The minister doesn't need perfect data — they need your best assessment.
═══════════════════════════════════════════════════════════════════════
"""


def _generate_generic_guidelines(
    classification: Optional[Dict] = None,
    domain_hints: Optional[List[str]] = None
) -> str:
    """Generate generic data guidelines when no facts are extracted."""
    
    return """
═══════════════════════════════════════════════════════════════════════
📊 DATA USAGE GUIDELINES — PREVENT METHODOLOGY SPIRALS
═══════════════════════════════════════════════════════════════════════

No pre-extracted statistics are available for this query. 
Follow these rules to prevent methodology debates:

═══════════════════════════════════════════════════════════════════════
⚠️ DATA CONSISTENCY RULES (MANDATORY)
═══════════════════════════════════════════════════════════════════════

1. FIRST CITATION WINS: The first agent to cite a statistic for a metric
   establishes the reference value. Subsequent agents must use that figure
   or explicitly acknowledge they're using updated data.

   ❌ BAD: Agent A says "growth was 11.8%", Agent B says "only 0.8%"
   ✅ GOOD: Agent B says "Earlier we cited 11.8%, but MoL 2024 data shows 0.8%"

2. ONE TURN MAXIMUM for any data discrepancy:
   - State which source you trust
   - Explain in ONE sentence why
   - Move immediately to strategic implications

3. NO METHODOLOGY TANGENTS:
   - Do NOT debate whether data is "sufficiently granular"
   - Do NOT discuss I-O tables, Leontief coefficients, satellite accounts
   - Do NOT debate classification systems or measurement approaches
   
   If methodology is relevant, state your conclusion and move on:
   ❌ BAD: "The PSA ICT Satellite Account aggregates AI under..."
   ✅ GOOD: "Data limitations exist, but available evidence suggests..."

4. WHEN DATA IS INSUFFICIENT:
   - State: "Precise data unavailable, but..."
   - Provide your best qualitative assessment
   - Give a confidence range (e.g., "40-60% confidence")

═══════════════════════════════════════════════════════════════════════
REMEMBER: The minister needs a decision, not a data quality audit.
═══════════════════════════════════════════════════════════════════════
"""


def generate_contradiction_detection_context(previous_stats: Dict[str, str]) -> str:
    """
    Generate context about statistics already cited in the debate.
    
    This is injected into agent prompts to prevent contradiction.
    
    Args:
        previous_stats: Dict mapping metric names to cited values
        
    Returns:
        Context string for agent prompts
    """
    if not previous_stats:
        return ""
    
    stats_list = "\n".join([
        f"   - {metric}: {value}" 
        for metric, value in list(previous_stats.items())[:15]
    ])
    
    return f"""
═══════════════════════════════════════════════════════════════════════
📋 STATISTICS ALREADY CITED IN THIS DEBATE
═══════════════════════════════════════════════════════════════════════

These figures have been cited. Use them consistently:
{stats_list}

If you have different data, explicitly acknowledge the difference:
"Earlier we cited [X], but my analysis uses [Y] because [reason]"
═══════════════════════════════════════════════════════════════════════
"""


class StatisticTracker:
    """
    Tracks statistics cited during a debate to detect contradictions.
    
    Domain-agnostic: Works for any metric type.
    """
    
    def __init__(self):
        self.cited_stats: Dict[str, Dict[str, Any]] = {}  # metric -> {value, agent, turn}
        self.contradiction_warnings: List[str] = []
        
    def extract_and_track(self, agent_name: str, turn_number: int, turn_content: str) -> List[str]:
        """
        Extract statistics from turn content and check for contradictions.
        
        Returns list of contradiction warnings (empty if none).
        """
        warnings = []
        
        # Extract percentage statistics: "X%", "X percent"
        pct_pattern = r'(\d+\.?\d*)\s*%'
        pct_matches = re.findall(pct_pattern, turn_content)
        
        # Extract growth/rate context around percentages
        for pct in pct_matches:
            # Find context around this percentage
            context_pattern = rf'([\w\s]{{10,50}}){pct}\s*%'
            context_matches = re.findall(context_pattern, turn_content)
            
            for context in context_matches:
                # Create a normalized metric key
                metric_key = self._normalize_metric_key(context)
                
                if metric_key and len(metric_key) > 5:
                    existing = self.cited_stats.get(metric_key)
                    
                    if existing and abs(float(existing['value']) - float(pct)) > 1.0:
                        # Contradiction detected
                        warning = (
                            f"⚠️ CONTRADICTION: {agent_name} (Turn {turn_number}) cited {pct}% for "
                            f"'{metric_key}', but {existing['agent']} (Turn {existing['turn']}) "
                            f"cited {existing['value']}%"
                        )
                        warnings.append(warning)
                        self.contradiction_warnings.append(warning)
                    elif not existing:
                        # First citation - record it
                        self.cited_stats[metric_key] = {
                            'value': pct,
                            'agent': agent_name,
                            'turn': turn_number
                        }
        
        return warnings
    
    def _normalize_metric_key(self, context: str) -> str:
        """Normalize context to a metric key."""
        context = context.lower().strip()
        
        # Remove common words
        stopwords = ['the', 'a', 'an', 'is', 'was', 'were', 'at', 'to', 'of', 'in', 'for']
        words = [w for w in context.split() if w not in stopwords]
        
        # Keep key terms
        key_terms = []
        important = ['employment', 'growth', 'rate', 'participation', 'unemployment', 
                    'gdp', 'revenue', 'investment', 'productivity', 'output', 'workforce',
                    'national', 'ict', 'tourism', 'sector', 'annual', 'quarterly']
        
        for word in words:
            for term in important:
                if term in word:
                    key_terms.append(term)
                    break
        
        return '_'.join(key_terms[:4])  # Max 4 terms
    
    def get_cited_stats_context(self) -> str:
        """Get context string of all cited statistics."""
        return generate_contradiction_detection_context(
            {k: f"{v['value']}% ({v['agent']}, Turn {v['turn']})" 
             for k, v in self.cited_stats.items()}
        )
    
    def get_contradiction_count(self) -> int:
        """Return number of contradictions detected."""
        return len(self.contradiction_warnings)


# Phase-specific prompts
PHASE_CONTEXT_PROMPTS = {
    'OPENING': """
🎯 OPENING PHASE: Present your initial analysis and position.
- State your recommendation clearly
- Provide supporting evidence
- Identify key uncertainties
""",
    
    'ANALYSIS': """
🔍 ANALYSIS PHASE: Deepen the analysis with data.
- Cite specific statistics (use agreed figures above)
- Quantify impacts where possible
- Identify trade-offs
⚠️ BUDGET: Maximum 25 turns for this phase.
""",
    
    'CHALLENGE': """
⚔️ CHALLENGE PHASE: Test each other's positions.
- Challenge specific claims, not general positions
- Request clarification on weak points
- Defend your position with new evidence
""",
    
    'DELIBERATION': """
🤔 DELIBERATION PHASE: Synthesize toward consensus.
- Acknowledge valid points from other perspectives
- Identify areas of agreement
- Narrow down remaining disagreements
""",
    
    'EDGE_CASES': """
🔮 EDGE CASE PHASE: Stress-test the recommendations.
- Consider low-probability, high-impact scenarios
- Identify contingencies needed
- Propose trigger points for strategy changes
""",
    
    'RISK_ASSESSMENT': """
⚠️ RISK PHASE: Comprehensive risk evaluation.
- List top 3-5 risks with likelihood and impact
- Propose mitigations for each
- Identify early warning indicators
""",
    
    'CONSENSUS': """
🤝 CONSENSUS PHASE: Converge on final recommendations.
- State your final position clearly
- Highlight key trade-offs the minister should consider
- Provide confidence level for your recommendation
""",
    
    'FINAL': """
📋 FINAL PHASE: Present your verdict.
- One clear recommendation
- Top 3 supporting reasons
- Top 3 risks to monitor
- Confidence level (0-100%)
"""
}


def get_phase_context(phase_name: str) -> str:
    """Get context prompt for a specific debate phase."""
    return PHASE_CONTEXT_PROMPTS.get(phase_name.upper(), "")

