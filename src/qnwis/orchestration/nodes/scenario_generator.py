"""
Scenario Generator for Multi-Agent Parallel Analysis.

Generates 4-6 plausible scenarios with different assumptions for parallel testing.
Supports Azure OpenAI and Anthropic based on configuration.
"""

import logging
import json
import os
from typing import List, Dict, Any

from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import get_llm_config

logger = logging.getLogger(__name__)


class ScenarioGenerator:
    """
    Generate multiple scenarios for parallel analysis.
    
    Each scenario tests different assumptions (oil prices, competition, etc.)
    to identify robust recommendations that work across uncertainty.
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
        extracted_facts: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate 4-6 critical scenarios for parallel testing.
        
        Args:
            query: Original ministerial query
            extracted_facts: Facts extracted from data sources
            
        Returns:
            List of scenario dicts with id, name, description, modified_assumptions
            
        Raises:
            ValueError: If scenario generation fails or produces invalid JSON
            RuntimeError: If API call fails after retries
        """
        response = None
        try:
            # Build prompt
            logger.info(f"🚀 Building scenario prompt for query: {query[:100]}...")
            prompt = self._build_scenario_prompt(query, extracted_facts)
            logger.info(f"📝 Prompt length: {len(prompt)} chars")
            
            # Call LLM (uses configured provider - Azure or Anthropic)
            logger.info(f"🤖 Calling LLM: {self.provider}/{self.model}...")
            response = await self.llm_client.generate(
                prompt=prompt,
                system="You are a scenario planning expert for Qatar ministerial intelligence. Output ONLY valid JSON array with 4-6 scenarios. No explanations, no markdown.",
                max_tokens=4000,
                temperature=0.4  # Slightly creative for diverse scenarios
            )
            
            if not response:
                raise ValueError("LLM returned empty response")
            
            logger.info(f"📨 LLM response received: {len(response)} chars")
            
            # Parse JSON response
            scenarios = self._parse_scenarios(response)
            
            # Validate scenarios
            self._validate_scenarios(scenarios)
            
            logger.info(f"✅ Generated {len(scenarios)} scenarios: {[s.get('name', 'Unknown') for s in scenarios]}")
            return scenarios
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            logger.error(f"📄 Raw response: {response[:1000] if response else 'None'}")
            raise ValueError(f"Invalid JSON in scenario response: {e}")
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Scenario generation failed: {type(e).__name__}: {e}")
            if response:
                logger.error(f"📄 Response was: {response[:500]}")
            raise RuntimeError(f"Scenario generation error: {type(e).__name__}: {e}")
    
    def _build_scenario_prompt(self, query: str, extracted_facts: Dict[str, Any]) -> str:
        """
        Build comprehensive prompt for scenario generation.
        
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
        
        # Determine query category and relevant scenario types
        if any(kw in query_lower for kw in ["labor", "workforce", "employment", "qatarization", "nationalization", "jobs"]):
            scenario_guidance = """SCENARIO TYPES (Labor/Workforce focused):
- Base Case: Current Qatarization trajectory continues
- Skills Gap: Private sector skill demands outpace training capacity
- Wage Competition: GCC countries offer higher salaries, causing brain drain
- Automation Disruption: AI/automation replaces 20% of current job targets
- Policy Acceleration: Government mandates stricter Qatarization quotas
- Economic Downturn: Oil price shock forces budget cuts to training programs"""
        elif any(kw in query_lower for kw in ["oil", "energy", "gas", "lng", "hydrocarbon"]):
            scenario_guidance = """SCENARIO TYPES (Energy focused):
- Base Case: Oil prices stable at $70-80/barrel
- Price Collapse: Sustained prices below $50/barrel
- Energy Transition: Accelerated global shift to renewables
- LNG Boom: Asian demand surge doubles LNG prices
- Production Limits: OPEC+ cuts reduce Qatar's output quotas
- Carbon Tax: Global carbon pricing impacts hydrocarbon exports"""
        elif any(kw in query_lower for kw in ["tourism", "hospitality", "visitor", "fifa", "world cup"]):
            scenario_guidance = """SCENARIO TYPES (Tourism focused):
- Base Case: Steady post-World Cup tourism growth
- Regional Hub: Qatar becomes primary GCC transit hub
- Competition: Dubai/Saudi mega-projects divert visitors
- Capacity Strain: Infrastructure limits visitor growth
- Premium Niche: Luxury/business travel dominates
- Health/Safety: Regional instability impacts travel"""
        elif any(kw in query_lower for kw in ["food", "agriculture", "security", "import"]):
            scenario_guidance = """SCENARIO TYPES (Food Security focused):
- Base Case: Current import dependency continues
- Supply Disruption: Major supplier crisis (climate, conflict)
- Local Production: Domestic agriculture scales significantly
- Regional Cooperation: GCC food security alliance forms
- Price Shock: Global food prices spike 50%+
- Technology: Vertical farming/desalination breakthrough"""
        elif any(kw in query_lower for kw in ["digital", "tech", "ai", "innovation", "startup"]):
            scenario_guidance = """SCENARIO TYPES (Digital/Tech focused):
- Base Case: Gradual digital transformation continues
- AI Disruption: Rapid AI adoption transforms economy
- Talent War: Competition for tech talent intensifies
- Cyber Risk: Major infrastructure cyber attack
- Tech Hub: Qatar becomes regional innovation leader
- Regulation: Strict AI/data regulations slow adoption"""
        else:
            scenario_guidance = """SCENARIO TYPES TO CONSIDER:
- Base Case: Current trends continue
- Optimistic: Favorable conditions (high oil prices, low competition, strong growth)
- Pessimistic: Adverse conditions (oil shock, intense competition, recession)
- Disruption: Technology or policy changes the game
- Regional: GCC dynamics shift (Saudi/UAE competition, cooperation, conflict)
- Demographic: Population or labor force changes"""
        
        prompt = f"""You are a scenario planning expert for ministerial intelligence in Qatar.

QUERY: {query}

EXTRACTED FACTS:
{formatted_facts}

YOUR TASK:
Generate 4-6 critical scenarios SPECIFICALLY TAILORED to answer this query. Each scenario must:
1. Directly relate to the query topic (not generic economic scenarios)
2. Modify one major assumption relevant to the question
3. Be plausible and grounded in real trends (not extreme outliers)
4. Test different dimensions of risk and opportunity for THIS specific issue
5. Be specific enough to drive different strategic decisions

{scenario_guidance}

REQUIRED JSON FORMAT:
[
  {{
    "id": "scenario_1",
    "name": "Base Case",
    "description": "Current economic trends continue with moderate oil prices and steady GCC competition",
    "modified_assumptions": {{
      "oil_price_usd_barrel": 75,
      "gcc_competition_level": "moderate",
      "global_growth_rate": 0.03,
      "key_risk": "Incremental erosion of competitive position"
    }}
  }},
  {{
    "id": "scenario_2", 
    "name": "Oil Price Shock",
    "description": "Sustained oil price decline to $45/barrel forces fiscal consolidation and strategic pivot",
    "modified_assumptions": {{
      "oil_price_usd_barrel": 45,
      "fiscal_pressure": "high",
      "diversification_urgency": "critical",
      "key_risk": "Budget deficit forces rapid spending cuts"
    }}
  }},
  {{
    "id": "scenario_3",
    "name": "GCC Competition Intensifies",
    "description": "Saudi Arabia and UAE aggressively compete for same sectors, driving down returns",
    "modified_assumptions": {{
      "gcc_competition_level": "intense",
      "market_saturation_risk": "high",
      "differentiation_requirement": "critical",
      "key_risk": "Race to bottom on incentives and subsidies"
    }}
  }},
  ... (generate 4-6 scenarios total)
]

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON array
- No markdown, no explanations, no text before or after the JSON
- Each scenario must have all 4 required fields: id, name, description, modified_assumptions
- Assumptions should be quantitative where possible
- Scenarios should be mutually exclusive but collectively comprehensive

Generate the scenarios now:"""
        
        return prompt
    
    def _format_facts(self, facts: Dict[str, Any]) -> str:
        """
        Format extracted facts for prompt.
        
        Args:
            facts: Dictionary of extracted facts
            
        Returns:
            Formatted string with top 50 facts
        """
        if not facts:
            return "No facts extracted yet."
        
        lines = []
        count = 0
        
        # Handle both dict and list formats (state uses list)
        if isinstance(facts, dict):
            for key, value in facts.items():
                if count >= 50:
                    break
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
            import re
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
        import re
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
        
        # Validate each scenario
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
        
        logger.info(f"✅ Validated {len(scenarios)} scenarios")

