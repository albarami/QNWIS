"""
Scenario Generator for Multi-Agent Parallel Analysis.

Generates 4-6 plausible scenarios with different assumptions for parallel testing.
Supports Azure OpenAI and Anthropic based on configuration.

ENHANCED: Stake-prompting for specific scenarios (Columbia/Harvard research finding)
"""

import logging
import json
import os
import re
from typing import List, Dict, Any, Tuple

from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import get_llm_config
from .scenario_baseline_requirements import format_baselines_for_prompt

logger = logging.getLogger(__name__)


# =============================================================================
# STAKE-PROMPTING ENHANCEMENT (NEW)
# Based on finding: "5-month-old infant" changes behavior, "child" doesn't
# =============================================================================

STAKE_SPECIFICATION_TEMPLATE = """
======== CRITICAL: STAKE SPECIFICITY ========
Vague scenarios produce vague analysis. Be BRUTALLY SPECIFIC.

BAD (too vague - DO NOT DO THIS):
- "Oil prices drop significantly"
- "Competition increases from GCC"  
- "Economic conditions worsen"

GOOD (specific stakes - DO THIS):
- "Oil drops to $45/barrel for 18+ months, eliminating QR 82B (31%) of revenue, forcing 15% ministry budget cuts"
- "Saudi Arabia announces QR 50B talent fund with 0% income tax, targeting 50,000 Qatar-trained professionals by 2027"
- "GPT-6 automates 40% of financial analyst tasks by Q3 2026, affecting 12,000 Qatari private sector jobs"

EVERY scenario MUST include:
1. MAGNITUDE: Exact numbers (QR 82B, 31%, 12,000 jobs) - NOT "significant" or "major"
2. TIMELINE: Precise dates (Q2 2026, 18 months) - NOT "soon" or "coming years"
3. MECHANISM: Causal chain (A → B → C) - NOT single effects
4. STAKEHOLDER PAIN: Who loses what, with numbers
"""


class ScenarioGenerator:
    """
    Generate multiple scenarios for parallel analysis.
    
    Each scenario tests different assumptions (oil prices, competition, etc.)
    to identify robust recommendations that work across uncertainty.
    
    ENHANCED: Stake-prompting ensures scenarios are specific enough to drive
    differentiated agent reasoning.
    """
    
    def __init__(self, model: str = None):
        """
        Initialize scenario generator.
        
        Args:
            model: Model to use. Defaults to configured model for provider.
        """
        # Use environment-configured provider (azure or anthropic)
        self.config = get_llm_config()
        self.provider = self.config.provider
        self.model = model or self.config.get_model(self.provider)
        self.llm_client = LLMClient()  # Uses env config
        logger.info(f"Scenario generator initialized with {self.provider}/{self.model}")

    async def generate_scenarios(
        self, 
        query: str, 
        extracted_facts: Dict[str, Any],
        num_scenarios: int = 6,
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate 4-6 critical scenarios for parallel testing.
        
        ENHANCED: Includes stake-prompting validation for specific scenarios.
        
        Args:
            query: Original ministerial query
            extracted_facts: Facts extracted from data sources
            num_scenarios: Number of scenarios to generate
            max_retries: Retries for validation failures
            
        Returns:
            List of scenario dicts with id, name, description, modified_assumptions
            
        Raises:
            ValueError: If scenario generation fails or produces invalid JSON
            RuntimeError: If API call fails after retries
        """
        response = None
        
        for attempt in range(max_retries + 1):
            try:
                # Build enhanced prompt
                logger.info(f"🚀 Building scenario prompt for query: {query[:100]}...")
                prompt = self._build_scenario_prompt(query, extracted_facts)
                logger.info(f"📝 Prompt length: {len(prompt)} chars")
                
                # Call LLM (uses configured provider - Azure or Anthropic)
                logger.info(f"🤖 Calling LLM: {self.provider}/{self.model}...")
                response = await self.llm_client.generate(
                    prompt=prompt,
                    system="You are a scenario planning expert for Qatar ministerial intelligence. Output ONLY valid JSON array with 4-6 scenarios. No explanations, no markdown.",
                    max_tokens=4000,
                    temperature=0.5  # Balanced creativity/consistency for stake specificity
                )
                
                if not response:
                    raise ValueError("LLM returned empty response")
                
                logger.info(f"📨 LLM response received: {len(response)} chars")
                
                # Parse JSON response
                scenarios = self._parse_scenarios(response)
                
                # Validate scenarios (structural)
                self._validate_scenarios(scenarios)
                
                # Validate stake specificity (ENHANCEMENT)
                stake_warnings = self._validate_stake_specificity(scenarios)
                
                if stake_warnings and attempt < max_retries:
                    logger.warning(f"⚠️ Stake specificity issues (attempt {attempt+1}): {len(stake_warnings)} scenarios need improvement")
                    for warning in stake_warnings:
                        logger.warning(f"   - {warning['scenario_name']}: {warning['issues']}")
                    continue  # Retry with same prompt (LLM may produce better results)
                
                if stake_warnings:
                    logger.warning(f"⚠️ Returning scenarios with {len(stake_warnings)} stake warnings")
                
                logger.info(f"✅ Generated {len(scenarios)} scenarios: {[s.get('name', 'Unknown') for s in scenarios]}")
                return scenarios
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parse error: {e}")
                logger.error(f"📄 Raw response: {response[:1000] if response else 'None'}")
                if attempt == max_retries:
                    raise ValueError(f"Invalid JSON in scenario response: {e}")
            except ValueError as e:
                logger.error(f"❌ Validation error: {e}")
                if attempt == max_retries:
                    raise
            except Exception as e:
                logger.error(f"❌ Scenario generation failed: {type(e).__name__}: {e}")
                if response:
                    logger.error(f"📄 Response was: {response[:500]}")
                if attempt == max_retries:
                    raise RuntimeError(f"Scenario generation error: {type(e).__name__}: {e}")
        
        raise ValueError("Failed to generate valid scenarios after retries")
    
    def _build_scenario_prompt(self, query: str, extracted_facts: Dict[str, Any]) -> str:
        """
        Build comprehensive prompt for scenario generation.
        
        ENHANCED: Includes stake-prompting requirements for specific scenarios.
        
        Args:
            query: Original ministerial query
            extracted_facts: Extracted facts from data
            
        Returns:
            Formatted prompt string
        """
        # Format facts (limit to 50 for context window)
        formatted_facts = self._format_facts(extracted_facts)
        
        # Detect query type to generate relevant scenarios
        query_lower = query.lower()
        
        # Determine query category and relevant scenario types (ENHANCED with specificity guidance)
        if any(kw in query_lower for kw in ["labor", "workforce", "employment", "qatarization", "nationalization", "jobs"]):
            scenario_guidance = """SCENARIO TYPES (Labor/Workforce focused):
- Base Case: Current Qatarization trajectory continues (specify current rate %, target %, timeline)
- Skills Gap: Private sector demands outpace training (specify gap size, affected sectors, timeline)
- Wage Competition: GCC offers higher salaries (specify % differential, target headcount, source countries)
- Automation Disruption: AI/automation impact (specify % jobs affected, which roles, by when)
- Policy Acceleration: Stricter quotas mandated (specify new %, penalties QR amount, effective date)
- Economic Downturn: Oil shock forces cuts (specify oil price, budget cut %, programs affected)"""
        elif any(kw in query_lower for kw in ["oil", "energy", "gas", "lng", "hydrocarbon"]):
            scenario_guidance = """SCENARIO TYPES (Energy focused):
- Base Case: Oil prices stable at $70-80/barrel (specify exact price, duration, revenue QR B)
- Price Collapse: Sustained prices below $50/barrel (specify price, duration months, revenue impact QR B)
- Energy Transition: Accelerated global shift to renewables (specify demand drop %, timeline, affected jobs)
- LNG Boom: Asian demand surge doubles LNG prices (specify price increase %, revenue gain QR B)
- Production Limits: OPEC+ cuts reduce Qatar's output quotas (specify % cut, revenue impact)
- Carbon Tax: Global carbon pricing impacts hydrocarbon exports (specify $/ton, export reduction %)"""
        elif any(kw in query_lower for kw in ["tourism", "hospitality", "visitor", "fifa", "world cup"]):
            scenario_guidance = """SCENARIO TYPES (Tourism focused):
- Base Case: Steady post-World Cup tourism growth (specify visitor count, growth %, revenue QR B)
- Regional Hub: Qatar becomes primary GCC transit hub (specify market share %, additional visitors)
- Competition: Dubai/Saudi mega-projects divert visitors (specify visitor loss %, revenue impact)
- Capacity Strain: Infrastructure limits visitor growth (specify capacity ceiling, investment needed QR B)
- Premium Niche: Luxury/business travel dominates (specify segment growth %, revenue per visitor)
- Health/Safety: Regional instability impacts travel (specify visitor drop %, duration months)"""
        elif any(kw in query_lower for kw in ["food", "agriculture", "security", "import"]):
            scenario_guidance = """SCENARIO TYPES (Food Security focused):
- Base Case: Current import dependency continues (specify import %, cost QR B, key suppliers)
- Supply Disruption: Major supplier crisis (specify affected %, price spike %, duration months)
- Local Production: Domestic agriculture scales significantly (specify self-sufficiency target %, investment QR B)
- Regional Cooperation: GCC food security alliance forms (specify cost sharing %, buffer stock days)
- Price Shock: Global food prices spike 50%+ (specify duration, additional cost QR B)
- Technology: Vertical farming/desalination breakthrough (specify cost reduction %, capacity increase)"""
        elif any(kw in query_lower for kw in ["digital", "tech", "ai", "innovation", "startup"]):
            scenario_guidance = """SCENARIO TYPES (Digital/Tech focused):
- Base Case: Gradual digital transformation continues (specify digitization rate %, timeline)
- AI Disruption: Rapid AI adoption transforms economy (specify % jobs affected, productivity gain %)
- Talent War: Competition for tech talent intensifies (specify salary premium %, vacancy rate)
- Cyber Risk: Major infrastructure cyber attack (specify downtime days, economic cost QR B)
- Tech Hub: Qatar becomes regional innovation leader (specify startup count, FDI QR B)
- Regulation: Strict AI/data regulations slow adoption (specify compliance cost %, delay months)"""
        elif any(kw in query_lower for kw in ["hub", "financial", "logistics"]):
            scenario_guidance = """SCENARIO TYPES (Strategic Hub focused):
- Base Case: Incremental development continues (specify current ranking, growth rate %, timeline)
- Accelerated Investment: Major push (specify investment QR B, timeline, target metrics)
- Competitor Leapfrog: Regional rival advances faster (specify competitor, their investment, impact)
- Global Shift: Trade/finance patterns change (specify shift direction, opportunity size QR B)
- Talent Bottleneck: Skilled workforce shortage (specify gap size, affected roles, salary premium %)
- Regulatory Advantage: Policy changes create edge (specify regulation, benefit quantified)"""
        elif any(kw in query_lower for kw in ["economic", "gdp", "growth", "investment", "diversification"]):
            scenario_guidance = """SCENARIO TYPES (Economic/Growth focused):
- Base Case: Current growth continues (specify GDP growth %, key drivers, timeline)
- Oil Shock: Price collapse scenario (specify price level $, duration months, revenue impact QR B)
- Diversification Success: Non-oil growth accelerates (specify sector, growth %, job creation)
- Regional Competition: GCC competitor gains advantage (specify which country, which sector, impact QR B)
- Global Recession: External demand collapse (specify demand drop %, affected exports, duration)
- Tech Disruption: New industry opportunity (specify technology, investment needed QR B, jobs created)"""
        else:
            scenario_guidance = """SCENARIO TYPES TO CONSIDER:
- Base Case: Current trends continue (specify key metrics, growth rates, timeline)
- Optimistic: Favorable conditions (specify exact improvements with numbers)
- Pessimistic: Adverse conditions (specify exact declines with numbers)
- Disruption: Technology or policy changes the game (specify what changes, by when, impact size)
- Regional: GCC dynamics shift (specify which country, what action, Qatar impact QR B)
- Demographic: Population or labor force changes (specify change %, affected groups, timeline)"""
        
        prompt = f"""You are a scenario planning expert for ministerial intelligence in Qatar.

QUERY: {query}

EXTRACTED FACTS:
{formatted_facts}

{STAKE_SPECIFICATION_TEMPLATE}

{scenario_guidance}

YOUR TASK:
Generate 4-6 critical scenarios SPECIFICALLY TAILORED to answer this query.

REQUIRED JSON FORMAT (with stake specificity):
[
  {{
    "id": "scenario_1",
    "name": "Base Case - [Key Metric]",
    "description": "2-3 sentences with SPECIFIC numbers, timeline, and mechanism chain",
    "type": "base|optimistic|pessimistic|external_shock|competitive|black_swan",
    "modified_assumptions": {{
      "primary_variable": <specific_number>,
      "secondary_variable": <specific_number>,
      "timeline_months": <number>
    }},
    "magnitude": {{
      "primary_impact": <number>,
      "unit": "QR_billions|percentage|jobs|months",
      "affected_population": <number>
    }},
    "timeline": {{
      "trigger": "Q1 2026",
      "full_impact": "Q3 2027",
      "duration_months": 18
    }},
    "mechanism": "cause → effect → consequence → outcome",
    "stakeholder_impact": {{
      "winners": ["who benefits, how much"],
      "losers": ["who loses, how much"]
    }},
    "key_assumptions": ["assumption 1", "assumption 2"],
    "early_warning_indicators": ["indicator 1", "indicator 2"]
  }}
]

QATAR CONTEXT (use for realistic numbers):
- Government revenue: QR 200-280B annually (60%+ hydrocarbons)
- Labor force: ~2.1M total, ~380K Qatari nationals
- Qatarization targets: 50-70% in priority sectors
- GDP: ~$220B USD
- Key competitors: UAE (Dubai), Saudi Arabia (Vision 2030)

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON array
- No markdown, no explanations, no text before or after the JSON
- Each scenario must have all required fields: id, name, description, modified_assumptions
- EVERY description must have at least 2 specific numbers
- EVERY scenario must have timeline with quarter/year
- EVERY scenario must have mechanism with → showing causation
- Assumptions should be quantitative where possible
- Scenarios should be mutually exclusive but collectively comprehensive

Generate the scenarios now:"""
        
        return prompt
    
    def _format_facts(self, facts: Dict[str, Any]) -> str:
        """
        Format extracted facts for prompt.
        
        ENHANCED: Uses scenario baselines when available for stake-prompting.
        
        Args:
            facts: Dictionary of extracted facts (may include _scenario_baselines)
            
        Returns:
            Formatted string with baseline metrics and facts
        """
        if not facts:
            return "No facts extracted yet. Use realistic Qatar estimates from context above."
        
        # Check for scenario baselines (ENHANCEMENT)
        if isinstance(facts, dict) and "_scenario_baselines" in facts:
            # Use the enhanced baseline formatter for stake-prompting
            baseline_section = format_baselines_for_prompt(facts)
            
            # Also include some original facts for additional context
            original_facts = facts.get("_original_facts", [])
            if original_facts and isinstance(original_facts, list):
                additional_lines = ["\n\nADDITIONAL CONTEXT FROM DATA SOURCES:"]
                for fact in original_facts[:20]:  # Limit to 20 additional facts
                    if isinstance(fact, dict):
                        indicator = fact.get('indicator', fact.get('metric', 'Data'))
                        value = fact.get('value', fact.get('data', ''))
                        source = fact.get('source', '')
                        if source:
                            additional_lines.append(f"- {indicator}: {value} (Source: {source})")
                        else:
                            additional_lines.append(f"- {indicator}: {value}")
                if len(additional_lines) > 1:
                    baseline_section += "\n".join(additional_lines)
            
            return baseline_section
        
        # Fallback to original formatting for backward compatibility
        lines = []
        count = 0
        
        # Handle both dict and list formats (state uses list)
        if isinstance(facts, dict):
            for key, value in facts.items():
                if count >= 50:
                    break
                if key.startswith('_'):  # Skip internal keys
                    continue
                if isinstance(value, dict):
                    val = value.get('value', value)
                    source = value.get('source', 'extracted')
                    lines.append(f"- {key}: {val} (source: {source})")
                else:
                    lines.append(f"- {key}: {value}")
                count += 1
        elif isinstance(facts, list):
            for fact in facts:
                if count >= 50:
                    break
                # Each fact is a dict with various fields
                if isinstance(fact, dict):
                    indicator = fact.get('indicator', fact.get('metric', 'Data'))
                    value = fact.get('value', fact.get('data', ''))
                    source = fact.get('source', '')
                    if source:
                        lines.append(f"- {indicator}: {value} (Source: {source})")
                    else:
                        lines.append(f"- {indicator}: {value}")
                else:
                    lines.append(f"- {str(fact)}")
                count += 1
        else:
            return f"Facts available: {str(facts)[:200]}"
        
        if count >= 50 and len(facts) > 50:
            lines.append(f"... and {len(facts) - 50} more facts")
        
        return "\n".join(lines) if lines else "No facts formatted."
    
    def _parse_scenarios(self, response_content: str) -> List[Dict[str, Any]]:
        """
        Parse scenarios from LLM response with robust JSON extraction.
        
        Args:
            response_content: Raw LLM response
            
        Returns:
            List of parsed scenario dictionaries
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        if not response_content:
            raise ValueError("Empty response from LLM")
        
        content = response_content.strip()
        logger.info(f"📝 Parsing scenario response ({len(content)} chars)")
        
        # Method 1: Try direct parsing first
        try:
            scenarios = json.loads(content)
            if isinstance(scenarios, list):
                logger.info(f"✅ Direct JSON parse successful: {len(scenarios)} scenarios")
                return scenarios
        except json.JSONDecodeError:
            pass
        
        # Method 2: Remove markdown code blocks
        if "```" in content:
            # Extract content between code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                content = json_match.group(1).strip()
                try:
                    scenarios = json.loads(content)
                    if isinstance(scenarios, list):
                        logger.info(f"✅ Markdown extraction successful: {len(scenarios)} scenarios")
                        return scenarios
                except json.JSONDecodeError:
                    pass
        
        # Method 3: Find JSON array in response
        # Look for array pattern
        array_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', content)
        if array_match:
            try:
                scenarios = json.loads(array_match.group())
                if isinstance(scenarios, list):
                    logger.info(f"✅ Regex extraction successful: {len(scenarios)} scenarios")
                    return scenarios
            except json.JSONDecodeError:
                pass
        
        # Method 4: Try fixing common JSON issues
        fixed_content = content
        # Fix trailing commas
        fixed_content = re.sub(r',\s*}', '}', fixed_content)
        fixed_content = re.sub(r',\s*\]', ']', fixed_content)
        # Fix unquoted keys (common LLM error)
        fixed_content = re.sub(r'(\s)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', fixed_content)
        
        try:
            scenarios = json.loads(fixed_content)
            if isinstance(scenarios, list):
                logger.info(f"✅ Fixed JSON parse successful: {len(scenarios)} scenarios")
                return scenarios
        except json.JSONDecodeError as e:
            logger.error(f"❌ All JSON parsing methods failed: {e}")
            logger.error(f"📄 Raw content (first 1000 chars): {content[:1000]}")
            raise ValueError(f"Failed to parse scenarios: {e}. Raw response: {content[:500]}")
    
    def _validate_scenarios(self, scenarios: List[Dict[str, Any]]) -> None:
        """
        Validate scenario structure and content.
        
        Args:
            scenarios: List of scenario dictionaries
            
        Raises:
            ValueError: If scenarios are invalid
        """
        if not scenarios:
            raise ValueError("No scenarios generated")
        
        if len(scenarios) < 4:
            raise ValueError(f"Expected at least 4 scenarios, got {len(scenarios)}")
        
        if len(scenarios) > 8:
            logger.warning(f"Too many scenarios ({len(scenarios)}), using first 6")
            scenarios[:] = scenarios[:6]
        
        # Validate each scenario - core fields required
        required_fields = ['id', 'name', 'description', 'modified_assumptions']
        
        for i, scenario in enumerate(scenarios):
            # Check required fields
            for field in required_fields:
                if field not in scenario:
                    raise ValueError(
                        f"Scenario {i} missing required field '{field}': {scenario}"
                    )
            
            # Validate field types
            if not isinstance(scenario['id'], str):
                raise ValueError(f"Scenario {i} 'id' must be string")
            if not isinstance(scenario['name'], str):
                raise ValueError(f"Scenario {i} 'name' must be string")
            if not isinstance(scenario['description'], str):
                raise ValueError(f"Scenario {i} 'description' must be string")
            if not isinstance(scenario['modified_assumptions'], dict):
                raise ValueError(f"Scenario {i} 'modified_assumptions' must be dict")
            
            # Check for reasonable content lengths
            if len(scenario['name']) < 3:
                raise ValueError(f"Scenario {i} name too short: {scenario['name']}")
            if len(scenario['description']) < 20:
                raise ValueError(f"Scenario {i} description too short")
        
        # Check for duplicate IDs
        ids = [s['id'] for s in scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate scenario IDs found: {ids}")
        
        logger.info(f"✅ Validated {len(scenarios)} scenarios (structural)")

    def _validate_stake_specificity(self, scenarios: List[Dict[str, Any]]) -> List[Dict]:
        """
        Validate scenarios have specific stakes (ENHANCEMENT).
        
        Returns list of warnings (empty = all good).
        """
        warnings = []
        
        for i, scenario in enumerate(scenarios):
            scenario_warnings = []
            desc = scenario.get('description', '')
            
            # Check for numeric content
            if not self._has_numeric_content(desc):
                scenario_warnings.append("Description lacks specific numbers")
            
            # Check for timeline indicators
            if not self._has_timeline_content(desc):
                scenario_warnings.append("Description lacks timeline (Q1/2026/months)")
            
            # Check for mechanism chain (if provided)
            mechanism = scenario.get('mechanism', '')
            if mechanism and not ('→' in mechanism or '->' in mechanism):
                scenario_warnings.append("Mechanism should show causal chain with →")
            
            if scenario_warnings:
                warnings.append({
                    'scenario_id': scenario.get('id', f'scenario_{i}'),
                    'scenario_name': scenario.get('name', 'Unknown'),
                    'issues': scenario_warnings
                })
                # Add warnings to scenario for transparency
                scenario['_stake_warnings'] = scenario_warnings
        
        if warnings:
            logger.warning(f"⚠️ Stake specificity issues in {len(warnings)} scenarios")
        else:
            logger.info(f"✅ All scenarios have specific stakes")
        
        return warnings

    def _has_numeric_content(self, text: str) -> bool:
        """Check if text contains meaningful numeric content."""
        patterns = [
            r'\d+%',                    # Percentages: 31%
            r'QR\s*\d+',                # QAR amounts: QR 82B
            r'\$\d+',                   # USD amounts: $45
            r'\d+[BMK]\b',              # Billions/Millions: 82B
            r'\d{1,3},\d{3}',           # Comma numbers: 12,000
            r'\d+\s*(billion|million|thousand|jobs|years|months)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_timeline_content(self, text: str) -> bool:
        """Check if text contains timeline indicators."""
        patterns = [
            r'Q[1-4]\s*20\d{2}',        # Q1 2026
            r'20\d{2}',                  # Year: 2026
            r'\d+\s*months?',            # 18 months
            r'by\s*(end of\s*)?20\d{2}', # by 2027
            r'within\s*\d+',             # within 18
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
