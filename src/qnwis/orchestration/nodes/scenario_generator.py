"""
Scenario Generator for Multi-Agent Parallel Analysis.

Generates 4-6 plausible scenarios with different assumptions for parallel testing.
Uses Claude Sonnet 4.5 with rate limiting to prevent API errors.
"""

import logging
import json
from typing import List, Dict, Any
from langchain_anthropic import ChatAnthropic

from ..llm_wrapper import call_llm_with_rate_limit

logger = logging.getLogger(__name__)


class ScenarioGenerator:
    """
    Generate multiple scenarios for parallel analysis.
    
    Each scenario tests different assumptions (oil prices, competition, etc.)
    to identify robust recommendations that work across uncertainty.
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize scenario generator.
        
        Args:
            model: Claude model to use. Defaults to Sonnet 4.
        """
        self.llm = ChatAnthropic(
            model=model,
            temperature=0.3,  # Consistent but creative scenarios
            max_tokens=4000
        )
        logger.info(f"Scenario generator initialized with {model}")
    
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
        try:
            # Build prompt
            prompt = self._build_scenario_prompt(query, extracted_facts)
            
            # Call LLM with rate limiting
            logger.info("Generating scenarios with Claude Sonnet 4.5...")
            response = await call_llm_with_rate_limit(self.llm, prompt)
            
            # Parse JSON response
            scenarios = self._parse_scenarios(response.content)
            
            # Validate scenarios
            self._validate_scenarios(scenarios)
            
            logger.info(f"✅ Generated {len(scenarios)} scenarios for parallel analysis")
            return scenarios
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse scenario JSON: {e}")
            logger.error(f"Raw response: {response.content[:500]}")
            raise ValueError(f"Invalid JSON in scenario response: {e}")
        except Exception as e:
            logger.error(f"Scenario generation failed: {e}")
            raise RuntimeError(f"Scenario generation error: {e}")
    
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
        
        prompt = f"""You are a scenario planning expert for ministerial intelligence in Qatar.

QUERY: {query}

EXTRACTED FACTS:
{formatted_facts}

YOUR TASK:
Generate 4-6 critical scenarios that test different assumptions. Each scenario must:
1. Modify one major assumption (oil prices, regional competition, technology disruption, demographic shifts, policy changes, etc.)
2. Be plausible and grounded in real trends (not extreme outliers)
3. Test different dimensions of risk and opportunity
4. Be specific enough to drive different strategic decisions

SCENARIO TYPES TO CONSIDER:
- Base Case: Current trends continue
- Optimistic: Favorable conditions (high oil prices, low competition, strong growth)
- Pessimistic: Adverse conditions (oil shock, intense competition, recession)
- Disruption: Technology or policy changes the game
- Regional: GCC dynamics shift (Saudi/UAE competition, cooperation, conflict)
- Demographic: Population or labor force changes

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
        Parse scenarios from LLM response.
        
        Args:
            response_content: Raw LLM response
            
        Returns:
            List of parsed scenario dictionaries
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Clean response (remove markdown if present)
        content = response_content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            # Find the JSON array
            lines = content.split("\n")
            content = "\n".join([
                line for line in lines 
                if not line.strip().startswith("```")
            ])
        
        # Parse JSON
        scenarios = json.loads(content)
        
        # Ensure it's a list
        if not isinstance(scenarios, list):
            raise ValueError(f"Expected list of scenarios, got {type(scenarios)}")
        
        return scenarios
    
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

