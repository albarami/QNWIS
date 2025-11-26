"""
Meta-Synthesis Node for Multi-Scenario Analysis.

Synthesizes insights across multiple parallel scenario analyses to identify:
- Robust recommendations that work across all scenarios
- Scenario-dependent strategies with conditional logic
- Key uncertainties and early warning indicators
- Final strategic guidance for leadership
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from langchain_anthropic import ChatAnthropic

from ..llm_wrapper import call_llm_with_rate_limit

logger = logging.getLogger(__name__)


async def meta_synthesis_node(scenario_results: List[Dict[str, Any]]) -> str:
    """
    Synthesize strategic intelligence across multiple scenario analyses.
    
    Args:
        scenario_results: List of completed scenario analysis results
        
    Returns:
        Comprehensive ministerial brief with cross-scenario insights
        
    Raises:
        ValueError: If scenario_results is empty or invalid
        RuntimeError: If synthesis fails
    """
    if not scenario_results:
        raise ValueError("Cannot perform meta-synthesis with no scenario results")
    
    logger.info(f"Starting meta-synthesis across {len(scenario_results)} scenarios")
    start_time = datetime.now()
    
    try:
        # Initialize LLM
        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=0.3,
            max_tokens=8000
        )
        
        # Extract and format scenario summaries
        scenario_summaries = _extract_scenario_summaries(scenario_results)
        
        # Build synthesis prompt
        prompt = _build_synthesis_prompt(scenario_summaries, scenario_results)
        
        # Call LLM with rate limiting
        logger.info("Synthesizing insights with Claude Sonnet 4...")
        response = await call_llm_with_rate_limit(llm, prompt)
        synthesis = response.content
        
        # Validate synthesis
        _validate_synthesis(synthesis)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Meta-synthesis complete in {elapsed:.1f}s ({len(synthesis)} chars)")
        
        return synthesis
        
    except Exception as e:
        logger.error(f"Meta-synthesis failed: {e}", exc_info=True)
        # Create emergency fallback
        return _emergency_synthesis(scenario_results, str(e))


def _extract_scenario_summaries(scenario_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract key information from each scenario result.
    
    Args:
        scenario_results: List of completed scenario states
        
    Returns:
        List of scenario summary dictionaries
    """
    summaries = []
    
    for result in scenario_results:
        try:
            scenario_meta = result.get('scenario_metadata', {})
            
            summary = {
                'id': result.get('scenario_id', 'unknown'),
                'name': scenario_meta.get('name', 'Unknown Scenario'),
                'description': scenario_meta.get('description', 'No description'),
                'assumptions': scenario_meta.get('modified_assumptions', {}),
                'recommendation': result.get('final_synthesis', 'No synthesis available')[:1500],
                'confidence': result.get('confidence_score', 0.0),
                'execution_time': result.get('scenario_execution_time', 0.0),
                'warnings': result.get('warnings', []),
                'reasoning_depth': len(result.get('reasoning_chain', []))
            }
            
            summaries.append(summary)
            
        except Exception as e:
            logger.warning(f"Failed to extract summary from scenario result: {e}")
            # Add minimal summary
            summaries.append({
                'name': 'Unknown Scenario',
                'description': 'Could not extract scenario information',
                'recommendation': 'Error in scenario execution',
                'confidence': 0.0
            })
    
    return summaries


def _build_synthesis_prompt(
    scenario_summaries: List[Dict[str, Any]],
    full_results: List[Dict[str, Any]]
) -> str:
    """
    Build comprehensive prompt for meta-synthesis.
    
    Args:
        scenario_summaries: Extracted scenario summaries
        full_results: Full scenario result dictionaries
        
    Returns:
        Formatted prompt string
    """
    # Format scenario details
    scenario_details = _format_scenarios(scenario_summaries)
    
    # Calculate statistics
    avg_confidence = sum(s['confidence'] for s in scenario_summaries) / len(scenario_summaries)
    total_execution_time = sum(s.get('execution_time', 0) for s in scenario_summaries)
    
    prompt = f"""You are synthesizing {len(scenario_summaries)} parallel scenario analyses for Qatar's ministerial leadership.

SCENARIO ANALYSES COMPLETED:
{scenario_details}

SYNTHESIS STATISTICS:
- Total scenarios analyzed: {len(scenario_summaries)}
- Average confidence: {avg_confidence:.0%}
- Total analysis time: {total_execution_time:.1f}s
- Analysis depth: {sum(s.get('reasoning_depth', 0) for s in scenario_summaries)} reasoning steps

YOUR TASK:
Synthesize these parallel analyses into actionable strategic intelligence. Your synthesis MUST include:

1. **ROBUST RECOMMENDATIONS** (work in ALL scenarios)
   - What actions deliver value regardless of which scenario unfolds?
   - Which strategies are "no-regret" moves?
   - What foundational capabilities are needed across all futures?

2. **SCENARIO-DEPENDENT STRATEGIES** (conditional logic)
   - IF Scenario X occurs, THEN do Y
   - What are the trigger indicators for each strategy?
   - How do we prepare contingencies without over-committing?

3. **KEY UNCERTAINTIES** (what drives divergence?)
   - Which assumptions create the biggest strategic differences?
   - What are the critical unknown variables?
   - Which uncertainties can we resolve through analysis vs monitoring?

4. **EARLY WARNING INDICATORS**
   - What signals tell us which scenario is unfolding?
   - How do we detect scenario shifts early enough to act?
   - What monitoring systems are required?

5. **FINAL STRATEGIC GUIDANCE**
   - What should leadership do NOW (immediate actions)?
   - What should be prepared but not executed (contingencies)?
   - What decisions can be deferred until uncertainty resolves?
   - What is the recommended decision-making framework?

QUALITY REQUIREMENTS:
- Be specific and actionable (no vague platitudes)
- Quantify where possible (probabilities, timelines, resource requirements)
- Acknowledge trade-offs and risks explicitly
- Provide decision criteria for scenario-dependent choices
- Flag critical dependencies and vulnerabilities
- Use ministerial-grade language (concise, authoritative, evidence-based)

STRUCTURE YOUR SYNTHESIS:

# META-SYNTHESIS: CROSS-SCENARIO STRATEGIC INTELLIGENCE

## EXECUTIVE SUMMARY
[3-4 sentences: What's the bottom line across all scenarios?]

## ROBUST RECOMMENDATIONS (High Confidence)
[Actions that work in ALL scenarios]

## SCENARIO-DEPENDENT STRATEGIES (Conditional Logic)
[If-then strategies based on scenario triggers]

## KEY UNCERTAINTIES & RISK FACTORS
[What we don't know that matters most]

## EARLY WARNING INDICATORS
[How to detect which scenario is unfolding]

## FINAL STRATEGIC GUIDANCE
[Immediate actions, contingencies, deferred decisions]

## CONFIDENCE ASSESSMENT
[Synthesis quality, data gaps, recommended next steps]

---

Provide your meta-synthesis now:"""
    
    return prompt


def _format_scenarios(summaries: List[Dict[str, Any]]) -> str:
    """
    Format scenario summaries for prompt.
    
    Args:
        summaries: List of scenario summary dicts
        
    Returns:
        Formatted string with scenario details
    """
    lines = []
    
    for i, summary in enumerate(summaries, 1):
        lines.append(f"\n### SCENARIO {i}: {summary['name']}")
        lines.append(f"**Description:** {summary['description']}")
        lines.append(f"**Modified Assumptions:** {summary.get('assumptions', {})}")
        lines.append(f"**Confidence:** {summary['confidence']:.0%}")
        lines.append(f"**Execution Time:** {summary.get('execution_time', 0):.1f}s")
        
        # Add recommendation (truncated)
        rec = summary['recommendation'][:1000]  # Limit to 1000 chars
        lines.append(f"\n**Recommendation:**")
        lines.append(rec)
        
        if summary.get('warnings'):
            lines.append(f"\n**Warnings:** {', '.join(summary['warnings'][:3])}")
        
        lines.append("\n" + "="*80)
    
    return "\n".join(lines)


def _validate_synthesis(synthesis: str) -> None:
    """
    Validate synthesis output quality.
    
    Args:
        synthesis: Generated synthesis text
        
    Raises:
        ValueError: If synthesis doesn't meet quality requirements
    """
    if not synthesis:
        raise ValueError("Synthesis is empty")
    
    if len(synthesis) < 500:
        raise ValueError(f"Synthesis too short ({len(synthesis)} chars), expected at least 500")
    
    # Check for key sections
    required_sections = [
        "ROBUST RECOMMENDATIONS",
        "SCENARIO-DEPENDENT",
        "UNCERTAINTIES",
        "WARNING INDICATORS",
        "STRATEGIC GUIDANCE"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in synthesis.upper():
            missing_sections.append(section)
    
    if len(missing_sections) > 2:
        logger.warning(
            f"Synthesis missing {len(missing_sections)} expected sections: {missing_sections}"
        )
        # Don't fail, but log warning


def _emergency_synthesis(scenario_results: List[Dict[str, Any]], error: str) -> str:
    """
    Create emergency fallback synthesis if main synthesis fails.
    
    Args:
        scenario_results: List of scenario results
        error: Error message from failed synthesis
        
    Returns:
        Emergency synthesis document
    """
    logger.error(f"Using emergency synthesis due to error: {error}")
    
    # Extract basic info
    scenario_names = [
        r.get('scenario_metadata', {}).get('name', 'Unknown')
        for r in scenario_results
    ]
    
    avg_confidence = sum(
        r.get('confidence_score', 0.0) 
        for r in scenario_results
    ) / len(scenario_results) if scenario_results else 0.0
    
    synthesis = f"""# META-SYNTHESIS: CROSS-SCENARIO ANALYSIS

## ⚠️ EMERGENCY SYNTHESIS MODE

**Note:** Full synthesis generation encountered an error. This is an automated fallback synthesis.

**Error:** {error}

## SCENARIO ANALYSIS SUMMARY

**Scenarios Analyzed:** {len(scenario_results)}
- {', '.join(scenario_names)}

**Average Confidence:** {avg_confidence:.0%}

## AVAILABLE RESULTS

{len(scenario_results)} scenario analyses completed successfully. Each scenario contains:
- Detailed agent reports
- Multi-agent debate results
- Fact verification
- Critique analysis

## RECOMMENDED NEXT STEPS

1. **Review individual scenario results** - Each contains complete analysis
2. **Manual synthesis** - Leadership should review scenarios and synthesize key insights
3. **Investigate synthesis error** - Technical team should review error: {error}
4. **Re-run if needed** - System can re-attempt synthesis with adjusted parameters

## SCENARIO SUMMARIES

"""
    
    # Add brief summaries
    for i, result in enumerate(scenario_results, 1):
        name = result.get('scenario_metadata', {}).get('name', 'Unknown')
        conf = result.get('confidence_score', 0.0)
        rec = result.get('final_synthesis', 'No synthesis')[:300]
        
        synthesis += f"\n### {i}. {name} (Confidence: {conf:.0%})\n"
        synthesis += f"{rec}...\n"
    
    synthesis += f"""

---

*Emergency synthesis generated at {datetime.now().isoformat()}*
*Technical team should investigate synthesis error*
"""
    
    return synthesis

