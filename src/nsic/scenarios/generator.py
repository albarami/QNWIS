"""
NSIC Scenario Generator - External Factors Edition

Generates 6 EXTERNAL FACTOR scenarios from ANY user question:
- 1 Base Case: Current trajectory continues
- 5 External Factor Scenarios: Events that could impact the policy

KEY INSIGHT:
Scenarios are NOT policy variations. They are "what if X happens while 
we implement this policy?" This makes recommendations ROBUST across 
multiple possible futures.

DOMAIN-AGNOSTIC:
The scenarios are generated dynamically by GPT-5 based on the query domain.
Labor policy gets labor-relevant scenarios.
Healthcare gets healthcare-relevant scenarios.
Nothing is hardcoded.

Flow:
1. Agent reads query → identifies domain
2. Agent generates 6 RELEVANT external factors for THAT domain
3. Engine B computes for EACH scenario
4. Engine A debates with cross-scenario results
"""

import logging
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# STAKE SPECIFICITY REQUIREMENTS (Ported from QNWIS)
# =============================================================================

STAKE_SPECIFICATION = """
CRITICAL: STAKE SPECIFICITY
Vague scenarios produce vague analysis. Be BRUTALLY SPECIFIC.

BAD (too vague):
- "Oil prices drop significantly"
- "Competition increases from GCC"

GOOD (specific stakes):
- "Oil drops to $45/barrel for 18+ months, eliminating QR 82B (31%) of revenue"
- "Saudi Arabia announces QR 50B talent fund with 0% income tax, targeting 50,000 professionals"

EVERY scenario MUST include:
1. MAGNITUDE: Exact numbers (QR 82B, 31%, 12,000 jobs)
2. TIMELINE: Precise dates (Q2 2026, 18 months)
3. MECHANISM: Causal chain (A → B → C)
4. STAKEHOLDER IMPACT: Who wins/loses, with numbers
"""


# =============================================================================
# QATAR CONTEXT FOR REALISM VALIDATION
# =============================================================================

QATAR_CONTEXT = """
QATAR REALITY CONSTRAINTS (for realistic scenarios):
- Population: ~2.9M total, ~380K Qatari nationals (~13%)
- Workforce: ~2.1M total, Qataris ~15% of private sector workforce
- Economy: GDP ~$220B USD, 60%+ government revenue from hydrocarbons
- Qatarization: Currently 5-15% private sector, 50-90% government
- Key competitors: UAE (Dubai DIFC), Saudi Arabia (Vision 2030, NEOM)
- Infrastructure: World Cup legacy, Qatar Financial Centre, Hamad Port

MATHEMATICAL CONSTRAINTS:
- Cannot have 60% Qatarization when Qataris are 13% of population
- Training pipelines take 3-5 years minimum for skilled roles
- Major infrastructure projects take 5-10 years
"""


# =============================================================================
# EXTERNAL FACTOR SCENARIO CATEGORIES (Template - Not Hardcoded)
# =============================================================================
# These are EXAMPLES. The actual scenarios are generated dynamically by GPT-5
# based on the query domain. A labor query gets labor-relevant scenarios.
# A healthcare query gets healthcare-relevant scenarios.

SCENARIO_CATEGORY_GUIDANCE = """
Generate 6 external factor scenarios that could impact this policy decision.

Scenario 0: BASE CASE - Current trajectory continues, no major shocks

Scenarios 1-5 should cover these categories (adapted to the domain):

1. ECONOMIC SHOCK
   - Examples: Oil crash, recession, budget crisis, inflation spike
   - How: Affects government revenue, private sector growth, job creation

2. REGIONAL COMPETITION  
   - Examples: Saudi/UAE policy changes, talent war, investment competition
   - How: Changes labor market dynamics, attracts/repels workforce

3. BLACK SWAN
   - Examples: Pandemic, blockade, war, natural disaster, cyber attack
   - How: Major disruption requiring emergency response

4. POSITIVE DISRUPTION
   - Examples: Tech breakthrough, mega investment, new industry boom
   - How: Creates unexpected opportunities or labor demand shifts

5. POLICY/REGULATORY CHANGE
   - Examples: New regulations, GCC coordination, trade agreements
   - How: Changes the rules of the game

For EACH scenario, you MUST provide:
- name: Short identifier (e.g., "oil_crash", "pandemic_2")
- description: What happens (specific, not vague)
- assumptions: Dictionary of variable adjustments:
  {
    "gdp_growth_rate": 0.5,        # Multiplier: 0.5 = 50% of base
    "job_creation_rate": 0.7,      # Multiplier
    "workforce_availability": 1.2, # Multiplier  
    "policy_effectiveness": 0.8,   # Multiplier
    "external_risk": 0.6,          # Multiplier (lower = more risk)
  }
"""


# =============================================================================
# BROAD SCENARIO CATEGORIES (4 Categories × 6 Variations = 24)
# =============================================================================

BROAD_CATEGORIES = {
    "economic": {
        "name": "Economic Variations",
        "parameters": [
            {"id": "oil_low", "param": "oil_price", "value": 50, "unit": "USD/barrel", "description": "Sustained low oil at $50/barrel"},
            {"id": "oil_mid", "param": "oil_price", "value": 80, "unit": "USD/barrel", "description": "Moderate oil at $80/barrel"},
            {"id": "oil_high", "param": "oil_price", "value": 120, "unit": "USD/barrel", "description": "High oil at $120/barrel"},
            {"id": "gdp_high", "param": "gdp_growth", "value": 5.0, "unit": "percent", "description": "Strong GDP growth at 5%"},
            {"id": "gdp_low", "param": "gdp_growth", "value": 1.0, "unit": "percent", "description": "Weak GDP growth at 1%"},
            {"id": "gdp_negative", "param": "gdp_growth", "value": -2.0, "unit": "percent", "description": "Recession with -2% GDP"},
        ]
    },
    "competitive": {
        "name": "Competitive Variations",
        "parameters": [
            {"id": "dubai_aggressive", "param": "competitor", "value": "dubai_expansion", "description": "Dubai aggressively expands with tax incentives"},
            {"id": "saudi_neom", "param": "competitor", "value": "saudi_neom", "description": "Saudi NEOM launches competing zone"},
            {"id": "uae_coalition", "param": "competitor", "value": "uae_unified", "description": "UAE emirates form unified strategy"},
            {"id": "gcc_cooperation", "param": "competitor", "value": "gcc_coop", "description": "GCC countries agree on cooperation"},
            {"id": "singapore_entry", "param": "competitor", "value": "singapore", "description": "Singapore expands GCC presence"},
            {"id": "china_partnership", "param": "competitor", "value": "china", "description": "China establishes major regional partnership"},
        ]
    },
    "policy": {
        "name": "Policy Variations",
        "parameters": [
            {"id": "fast_nationalization", "param": "nationalization", "value": "accelerated", "description": "Accelerated Qatarization with strict quotas"},
            {"id": "slow_nationalization", "param": "nationalization", "value": "gradual", "description": "Gradual Qatarization over 10+ years"},
            {"id": "open_immigration", "param": "immigration", "value": "open", "description": "Liberalized immigration for skilled workers"},
            {"id": "restricted_immigration", "param": "immigration", "value": "restricted", "description": "Restrictive immigration requirements"},
            {"id": "high_subsidies", "param": "subsidies", "value": "high", "description": "High government subsidies and support"},
            {"id": "market_driven", "param": "subsidies", "value": "low", "description": "Market-driven with reduced subsidies"},
        ]
    },
    "timing": {
        "name": "Timing Variations",
        "parameters": [
            {"id": "launch_2026", "param": "launch_year", "value": 2026, "unit": "year", "description": "Aggressive launch target 2026"},
            {"id": "launch_2028", "param": "launch_year", "value": 2028, "unit": "year", "description": "Moderate launch target 2028"},
            {"id": "launch_2030", "param": "launch_year", "value": 2030, "unit": "year", "description": "Conservative launch target 2030"},
            {"id": "phased_5yr", "param": "approach", "value": "phased_5yr", "description": "Phased implementation over 5 years"},
            {"id": "phased_10yr", "param": "approach", "value": "phased_10yr", "description": "Phased implementation over 10 years"},
            {"id": "big_bang", "param": "approach", "value": "big_bang", "description": "Big bang rapid implementation"},
        ]
    },
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GeneratedScenario:
    """A single generated scenario."""
    id: str
    name: str
    type: str  # "base", "deep", "broad"
    category: str  # e.g., "optimistic", "economic", etc.
    description: str
    prompt: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    assigned_engine: str = "engine_b"  # "engine_a" for deep, "engine_b" for broad
    target_turns: int = 25
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "prompt": self.prompt,
            "parameters": self.parameters,
            "assigned_engine": self.assigned_engine,
            "target_turns": self.target_turns,
        }


@dataclass
class ScenarioSet:
    """
    Complete set of 6 EXTERNAL FACTOR scenarios for a user question.
    
    NEW DESIGN:
    - 1 Base Case: Current trajectory
    - 5 External Factors: Events that could impact ANY policy
    
    These are NOT policy variations. They are "what if X happens?"
    """
    original_question: str
    question_context: Dict[str, Any]
    scenarios: List[GeneratedScenario]  # 6 total (base + 5 external factors)
    generated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_count(self) -> int:
        return len(self.scenarios)
    
    @property
    def base_case(self) -> GeneratedScenario:
        """The base case scenario (index 0)."""
        return self.scenarios[0] if self.scenarios else None
    
    @property
    def external_factors(self) -> List[GeneratedScenario]:
        """External factor scenarios (indices 1-5)."""
        return self.scenarios[1:] if len(self.scenarios) > 1 else []
    
    @property
    def all_scenarios(self) -> List[GeneratedScenario]:
        return self.scenarios
    
    @property
    def engine_a_scenarios(self) -> List[GeneratedScenario]:
        """All scenarios go to Engine A for debate (with Engine B compute results)."""
        return self.scenarios
    
    @property
    def engine_b_scenarios(self) -> List[GeneratedScenario]:
        """Legacy - no longer used for DeepSeek LLM runs."""
        return []  # Engine B is now compute, not LLM
    
    def get_scenario_assumptions(self) -> Dict[str, Dict[str, float]]:
        """Get assumptions for each scenario (used by Engine B compute)."""
        return {
            s.id: s.metadata.get("assumptions", {})
            for s in self.scenarios
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_question": self.original_question,
            "question_context": self.question_context,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "total_count": self.total_count,
            "generated_at": self.generated_at.isoformat(),
        }


# =============================================================================
# NSIC SCENARIO GENERATOR
# =============================================================================

class NSICScenarioGenerator:
    """
    Generates 6 EXTERNAL FACTOR scenarios from ANY user question.
    
    Output Structure:
    - 1 Base Case: Current trajectory continues
    - 5 External Factors: Domain-relevant events that could impact policy
    
    Key Features:
    - Scenarios are EXTERNAL FACTORS, not policy variations
    - Generated dynamically by GPT-5 based on query domain
    - Each scenario has assumptions for Engine B compute
    - Makes recommendations ROBUST across multiple futures
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize scenario generator.
        
        Args:
            llm_client: Optional LLM client for scenario generation.
        """
        self._llm_client = llm_client
        logger.info("NSICScenarioGenerator initialized (External Factors Edition)")
    
    @property
    def llm_client(self):
        """Lazy load LLM client."""
        if self._llm_client is None:
            try:
                from src.nsic.integration.llm_client import get_nsic_llm_client
                self._llm_client = get_nsic_llm_client()
            except Exception as e:
                logger.warning(f"LLM client not available: {e}")
        return self._llm_client
    
    async def generate(self, user_question: str) -> ScenarioSet:
        """
        Generate 6 EXTERNAL FACTOR scenarios from user question.
        
        Args:
            user_question: The ministerial policy question
            
        Returns:
            ScenarioSet with 6 scenarios (1 base + 5 external factors)
        """
        logger.info(f"Generating 6 external factor scenarios for: {user_question[:100]}...")
        
        # Step 1: Analyze the question to understand domain
        context = await self._analyze_question(user_question)
        domain = context.get("domain", "general")
        logger.info(f"Question domain: {domain}")
        
        # Step 2: Generate 6 domain-relevant external factor scenarios
        scenarios = await self._generate_external_factor_scenarios(user_question, domain, context)
        
        assert len(scenarios) == 6, f"Expected 6 scenarios, got {len(scenarios)}"
        
        # Step 3: Assemble scenario set
        scenario_set = ScenarioSet(
            original_question=user_question,
            question_context=context,
            scenarios=scenarios,
        )
        
        logger.info(
            f"Generated {scenario_set.total_count} scenarios: "
            f"1 base case + 5 external factors"
        )
        
        return scenario_set
    
    async def _generate_external_factor_scenarios(
        self,
        question: str,
        domain: str,
        context: Dict[str, Any],
    ) -> List[GeneratedScenario]:
        """
        Generate 6 domain-relevant external factor scenarios using GPT-5.
        
        This is NOT hardcoded. GPT-5 generates relevant scenarios based on domain.
        """
        scenarios = []
        
        # Try LLM generation first
        if self.llm_client:
            try:
                llm_scenarios = await self._generate_scenarios_with_llm(question, domain, context)
                if llm_scenarios and len(llm_scenarios) == 6:
                    return llm_scenarios
            except Exception as e:
                logger.warning(f"LLM scenario generation failed, using fallback: {e}")
        
        # Fallback: Generate domain-adapted scenarios
        return self._generate_fallback_scenarios(question, domain, context)
    
    async def _generate_scenarios_with_llm(
        self,
        question: str,
        domain: str,
        context: Dict[str, Any],
    ) -> List[GeneratedScenario]:
        """Generate scenarios using GPT-5 for domain relevance."""
        
        prompt = f"""
{SCENARIO_CATEGORY_GUIDANCE}

DOMAIN: {domain}
QUERY: {question}

Generate 6 external factor scenarios specific to this domain and query.
Each scenario is an event that could happen WHILE the policy is being implemented.

Output as JSON array:
[
  {{
    "id": "base_case",
    "name": "Base Case",
    "category": "base_case",
    "description": "Current trajectory continues with no major shocks",
    "assumptions": {{
      "gdp_growth_rate": 1.0,
      "job_creation_rate": 1.0,
      "workforce_availability": 1.0,
      "policy_effectiveness": 1.0,
      "external_risk": 1.0
    }}
  }},
  ...5 more scenarios
]
"""
        
        response = await self.llm_client.generate(
            prompt=prompt,
            system="You are an expert scenario planner. Generate realistic, domain-specific external factor scenarios.",
            max_tokens=2000,
        )
        
        # Parse JSON from response
        try:
            # Extract JSON from response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                scenario_data = json.loads(json_match.group())
                return [
                    GeneratedScenario(
                        id=s["id"],
                        name=s["name"],
                        category=s.get("category", "external_factor"),
                        description=s["description"],
                        prompt=f"Analyze under scenario: {s['name']}\n{s['description']}\n\nQUESTION: {question}",
                        parameters={},
                        assigned_engine="A",
                        target_turns=150,
                        metadata={"assumptions": s.get("assumptions", {})},
                    )
                    for s in scenario_data
                ]
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM scenario JSON: {e}")
        
        return []
    
    def _generate_fallback_scenarios(
        self,
        question: str,
        domain: str,
        context: Dict[str, Any],
    ) -> List[GeneratedScenario]:
        """Generate fallback scenarios adapted to domain."""
        
        # Domain-specific scenario templates
        domain_scenarios = self._get_domain_scenarios(domain)
        
        scenarios = []
        for i, scenario_template in enumerate(domain_scenarios):
            scenarios.append(GeneratedScenario(
                id=scenario_template["id"],
                name=scenario_template["name"],
                category=scenario_template["category"],
                description=scenario_template["description"],
                prompt=f"""
Analyze under scenario: {scenario_template['name']}
{scenario_template['description']}

QUESTION: {question}

Your analysis MUST account for how this external factor changes the outcome.
""",
                parameters={},
                assigned_engine="A",
                target_turns=150,
                metadata={"assumptions": scenario_template["assumptions"]},
            ))
        
        return scenarios
    
    def _get_domain_scenarios(self, domain: str) -> List[Dict[str, Any]]:
        """Get domain-adapted scenario templates."""
        
        # Base case always first
        base = {
            "id": "base_case",
            "name": "Base Case",
            "category": "base_case",
            "description": "Current trajectory continues with no major external shocks. Existing trends persist.",
            "assumptions": {
                "gdp_growth_rate": 1.0,
                "job_creation_rate": 1.0,
                "workforce_availability": 1.0,
                "policy_effectiveness": 1.0,
                "external_risk": 1.0,
            },
        }
        
        # Domain-specific external factors
        if domain in ["labor", "employment", "workforce", "qatarization"]:
            external_factors = [
                {
                    "id": "oil_crash",
                    "name": "Oil Price Crash",
                    "category": "economic_shock",
                    "description": "Oil drops to $45/barrel for 18+ months. Government revenue falls 30%, budget cuts across sectors.",
                    "assumptions": {"gdp_growth_rate": 0.5, "job_creation_rate": 0.6, "policy_effectiveness": 0.7, "external_risk": 0.5},
                },
                {
                    "id": "saudi_competition",
                    "name": "Saudi Talent War",
                    "category": "regional_competition",
                    "description": "Saudi announces QR 50B talent fund with 0% income tax, targeting 50,000 Gulf professionals.",
                    "assumptions": {"workforce_availability": 0.7, "job_creation_rate": 0.9, "external_risk": 0.6},
                },
                {
                    "id": "pandemic_2",
                    "name": "Pandemic 2.0",
                    "category": "black_swan",
                    "description": "Major health crisis causes expatriate exodus. 15% workforce reduction over 12 months.",
                    "assumptions": {"workforce_availability": 1.3, "job_creation_rate": 0.6, "policy_effectiveness": 0.8, "external_risk": 0.4},
                },
                {
                    "id": "ai_automation",
                    "name": "AI Automation Boom",
                    "category": "positive_disruption",
                    "description": "AI breakthrough reduces labor needs by 20% in admin/support roles, creates new tech sector jobs.",
                    "assumptions": {"job_creation_rate": 0.8, "workforce_availability": 1.1, "policy_effectiveness": 1.2},
                },
                {
                    "id": "gcc_integration",
                    "name": "GCC Labor Mobility",
                    "category": "policy_environment",
                    "description": "GCC announces shared labor mobility agreement. Workers can move freely between member states.",
                    "assumptions": {"workforce_availability": 0.8, "job_creation_rate": 1.0, "policy_effectiveness": 0.7, "external_risk": 0.7},
                },
            ]
        elif domain in ["healthcare", "health", "medical"]:
            external_factors = [
                {
                    "id": "medical_tourism_boom",
                    "name": "Medical Tourism Boom",
                    "category": "positive_disruption",
                    "description": "Regional instability drives medical tourism to Qatar. Hospital capacity stressed.",
                    "assumptions": {"job_creation_rate": 1.4, "workforce_availability": 0.9, "policy_effectiveness": 0.9},
                },
                {
                    "id": "health_crisis",
                    "name": "Regional Health Crisis",
                    "category": "black_swan",
                    "description": "Major disease outbreak in region. Qatar's healthcare system under pressure.",
                    "assumptions": {"workforce_availability": 0.8, "policy_effectiveness": 0.6, "external_risk": 0.4},
                },
                {
                    "id": "brain_drain",
                    "name": "Healthcare Brain Drain",
                    "category": "regional_competition",
                    "description": "UAE/Saudi offer 50% higher salaries for medical professionals. Qatar loses 15% of doctors.",
                    "assumptions": {"workforce_availability": 0.7, "policy_effectiveness": 0.8, "external_risk": 0.6},
                },
                {
                    "id": "insurance_reform",
                    "name": "Insurance System Reform",
                    "category": "policy_environment",
                    "description": "Mandatory universal health insurance implemented. Changes provider economics.",
                    "assumptions": {"job_creation_rate": 1.1, "policy_effectiveness": 1.2, "external_risk": 0.9},
                },
                {
                    "id": "telemedicine_breakthrough",
                    "name": "Telemedicine Revolution",
                    "category": "positive_disruption",
                    "description": "AI diagnostics and telemedicine reduce need for in-person care by 25%.",
                    "assumptions": {"job_creation_rate": 0.8, "workforce_availability": 1.2, "policy_effectiveness": 1.3},
                },
            ]
        else:
            # Generic external factors for any domain
            external_factors = [
                {
                    "id": "economic_shock",
                    "name": "Economic Recession",
                    "category": "economic_shock",
                    "description": "Global recession reduces Qatar's GDP growth. Budget constraints affect all sectors.",
                    "assumptions": {"gdp_growth_rate": 0.6, "job_creation_rate": 0.7, "policy_effectiveness": 0.8, "external_risk": 0.5},
                },
                {
                    "id": "regional_competition",
                    "name": "Regional Competition Intensifies",
                    "category": "regional_competition",
                    "description": "UAE and Saudi make aggressive moves in Qatar's key sectors.",
                    "assumptions": {"workforce_availability": 0.8, "job_creation_rate": 0.9, "external_risk": 0.6},
                },
                {
                    "id": "black_swan",
                    "name": "Major Disruption",
                    "category": "black_swan",
                    "description": "Unexpected crisis (geopolitical, environmental, or technological) disrupts normal operations.",
                    "assumptions": {"policy_effectiveness": 0.6, "external_risk": 0.4, "job_creation_rate": 0.7},
                },
                {
                    "id": "positive_disruption",
                    "name": "Breakthrough Opportunity",
                    "category": "positive_disruption",
                    "description": "Major positive development creates unexpected opportunities.",
                    "assumptions": {"job_creation_rate": 1.3, "policy_effectiveness": 1.2, "external_risk": 1.1},
                },
                {
                    "id": "policy_change",
                    "name": "Policy Environment Shift",
                    "category": "policy_environment",
                    "description": "New regulations or international agreements change the operating environment.",
                    "assumptions": {"policy_effectiveness": 0.8, "external_risk": 0.8},
                },
            ]
        
        return [base] + external_factors
    
    def generate_sync(self, user_question: str) -> ScenarioSet:
        """Synchronous wrapper for generate."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.generate(user_question))
    
    async def _analyze_question(self, question: str) -> Dict[str, Any]:
        """
        Analyze user question to understand domain and context.
        
        Uses rule-based analysis with optional LLM enhancement.
        
        Args:
            question: User's policy question
            
        Returns:
            Context dict with domain, options, stakeholders, etc.
        """
        question_lower = question.lower()
        
        # Rule-based domain detection
        domain = self._detect_domain(question_lower)
        
        # Extract options (if comparative question)
        options = self._extract_options(question)
        
        # Identify stakeholders
        stakeholders = self._identify_stakeholders(question_lower, domain)
        
        # Determine time horizon
        time_horizon = self._detect_time_horizon(question_lower)
        
        # Identify key variables
        key_variables = self._identify_key_variables(domain)
        
        context = {
            "domain": domain,
            "options": options,
            "stakeholders": stakeholders,
            "time_horizon": time_horizon,
            "key_variables": key_variables,
            "is_comparative": len(options) > 1,
        }
        
        # Optional LLM enhancement
        if self.llm_client:
            try:
                enhanced = await self._enhance_context_with_llm(question, context)
                context.update(enhanced)
            except Exception as e:
                logger.warning(f"LLM context enhancement failed: {e}")
        
        return context
    
    def _detect_domain(self, question_lower: str) -> str:
        """Detect primary domain from question keywords."""
        domain_keywords = {
            "finance": ["financial", "finance", "banking", "investment", "capital", "qfc", "difc"],
            "logistics": ["logistics", "port", "shipping", "trade", "supply chain", "freight", "cargo"],
            "energy": ["oil", "gas", "lng", "energy", "hydrocarbon", "petroleum"],
            "labor": ["labor", "workforce", "employment", "qatarization", "nationalization", "jobs", "hiring"],
            "tourism": ["tourism", "hospitality", "visitor", "hotel", "travel"],
            "technology": ["digital", "tech", "ai", "innovation", "startup", "fintech"],
            "infrastructure": ["infrastructure", "construction", "development", "metro", "rail"],
            "education": ["education", "training", "university", "skills", "curriculum"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in question_lower for kw in keywords):
                return domain
        
        return "economic"  # Default domain
    
    def _extract_options(self, question: str) -> List[str]:
        """Extract options being compared in the question."""
        options = []
        
        # Pattern: "X or Y"
        or_match = re.search(r"(?:prioritize|choose|prefer|focus on)\s+(.+?)\s+or\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
        if or_match:
            options = [or_match.group(1).strip(), or_match.group(2).strip()]
        
        # Pattern: "between X and Y"
        between_match = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
        if between_match:
            options = [between_match.group(1).strip(), between_match.group(2).strip()]
        
        # Clean options
        options = [opt.rstrip("?.,") for opt in options]
        
        return options if options else [question.split("?")[0].strip()]
    
    def _identify_stakeholders(self, question_lower: str, domain: str) -> List[str]:
        """Identify key stakeholders based on question and domain."""
        stakeholders = ["government", "private_sector"]
        
        if domain in ["labor", "education"]:
            stakeholders.extend(["qatari_workforce", "expatriate_workforce"])
        if domain in ["finance", "logistics"]:
            stakeholders.extend(["international_investors", "multinational_corporations"])
        if "qatarization" in question_lower:
            stakeholders.extend(["qatari_youth", "training_institutions"])
        
        return list(set(stakeholders))
    
    def _detect_time_horizon(self, question_lower: str) -> str:
        """Detect implied time horizon."""
        if any(kw in question_lower for kw in ["2030", "long-term", "decade", "vision"]):
            return "long_term"  # 5+ years
        elif any(kw in question_lower for kw in ["2026", "2027", "short-term", "immediate"]):
            return "short_term"  # < 2 years
        else:
            return "medium_term"  # 2-5 years
    
    def _identify_key_variables(self, domain: str) -> List[str]:
        """Identify key variables for scenario generation based on domain."""
        common = ["oil_price", "gdp_growth", "regional_competition"]
        
        domain_specific = {
            "finance": ["regulatory_environment", "talent_availability", "technology_adoption"],
            "logistics": ["trade_volume", "port_capacity", "shipping_routes"],
            "energy": ["oil_demand", "renewable_transition", "production_quota"],
            "labor": ["qatarization_rate", "wage_levels", "training_capacity"],
            "tourism": ["visitor_numbers", "hotel_capacity", "event_calendar"],
            "technology": ["digital_adoption", "startup_ecosystem", "tech_talent"],
        }
        
        return common + domain_specific.get(domain, [])
    
    async def _enhance_context_with_llm(self, question: str, base_context: Dict) -> Dict:
        """Optional LLM enhancement for context analysis."""
        # Placeholder for LLM-based enhancement
        # Can be implemented to get more nuanced understanding
        return {}
    
    def _create_base_case(self, question: str, context: Dict[str, Any]) -> GeneratedScenario:
        """
        Create base case scenario (current conditions).
        
        Args:
            question: User's question
            context: Analyzed question context
            
        Returns:
            GeneratedScenario for base case
        """
        prompt = f"""BASE CASE: CURRENT CONDITIONS ANALYSIS
{STAKE_SPECIFICATION}

{QATAR_CONTEXT}

Analyze under CURRENT conditions with no assumed changes:
- Current oil prices (~$75-85/barrel)
- Current Qatarization levels
- Current competitive landscape
- Current infrastructure and capacity

QUESTION: {question}

Provide a comprehensive analysis of the question under today's conditions.
This serves as the baseline for comparison with other scenarios.
"""
        
        return GeneratedScenario(
            id="base_case",
            name="Base Case - Current Conditions",
            type="base",
            category="baseline",
            description="Analysis under current Qatar conditions without assumed changes",
            prompt=prompt,
            parameters={},
            assigned_engine="engine_a",  # Base case gets deep analysis
            target_turns=100,
        )
    
    async def _create_deep_scenarios(
        self, question: str, context: Dict[str, Any]
    ) -> List[GeneratedScenario]:
        """
        Create 5 deep strategic scenarios.
        
        Args:
            question: User's question
            context: Analyzed question context
            
        Returns:
            List of 5 GeneratedScenario objects
        """
        scenarios = []
        
        for scenario_type in DEEP_SCENARIO_TYPES:
            # Customize prompt based on question context
            base_prompt = scenario_type["prompt_template"].format(question=question)
            
            # Add stake specification and Qatar context
            full_prompt = f"""{STAKE_SPECIFICATION}

{QATAR_CONTEXT}

DOMAIN CONTEXT: This question relates to {context['domain']}.
KEY VARIABLES TO CONSIDER: {', '.join(context['key_variables'])}
STAKEHOLDERS: {', '.join(context['stakeholders'])}

{base_prompt}
"""
            
            scenario = GeneratedScenario(
                id=f"deep_{scenario_type['id']}",
                name=scenario_type["name"],
                type="deep",
                category=scenario_type["id"],
                description=scenario_type["description"],
                prompt=full_prompt,
                parameters={"scenario_type": scenario_type["id"]},
                assigned_engine="engine_a",  # Deep scenarios → Engine A
                target_turns=100,  # 100 turns for deep analysis
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def _create_broad_scenarios(
        self, question: str, context: Dict[str, Any]
    ) -> List[GeneratedScenario]:
        """
        Create 24 broad parametric scenarios.
        
        4 categories × 6 variations = 24 scenarios
        
        Args:
            question: User's question
            context: Analyzed question context
            
        Returns:
            List of 24 GeneratedScenario objects
        """
        scenarios = []
        
        for category_id, category in BROAD_CATEGORIES.items():
            for param_def in category["parameters"]:
                # Build scenario-specific prompt
                prompt = self._build_broad_prompt(question, context, category_id, param_def)
                
                scenario = GeneratedScenario(
                    id=f"broad_{category_id}_{param_def['id']}",
                    name=f"{category['name']}: {param_def['description']}",
                    type="broad",
                    category=category_id,
                    description=param_def["description"],
                    prompt=prompt,
                    parameters={
                        "category": category_id,
                        "parameter": param_def["param"],
                        "value": param_def["value"],
                        "unit": param_def.get("unit", ""),
                    },
                    assigned_engine="engine_b",  # Broad scenarios → Engine B
                    target_turns=25,  # 25 turns for broad exploration
                )
                scenarios.append(scenario)
        
        return scenarios
    
    def _build_broad_prompt(
        self,
        question: str,
        context: Dict[str, Any],
        category_id: str,
        param_def: Dict[str, Any],
    ) -> str:
        """Build prompt for a broad parametric scenario."""
        
        # Parameter-specific context
        param_context = self._get_parameter_context(category_id, param_def)
        
        prompt = f"""PARAMETRIC SCENARIO: {param_def['description']}

ASSUMPTION: {param_context}

{STAKE_SPECIFICATION}

QUESTION: {question}

Analyze how this specific parameter change affects the answer to the question.
Focus on:
1. Direct impact of this parameter
2. Second-order effects
3. How it changes the relative attractiveness of options
4. Key risks and opportunities under this condition

Keep analysis focused - this is one of 24 parametric variations.
"""
        
        return prompt
    
    def _get_parameter_context(self, category_id: str, param_def: Dict[str, Any]) -> str:
        """Get contextual description for parameter."""
        value = param_def["value"]
        unit = param_def.get("unit", "")
        
        if category_id == "economic":
            if "oil" in param_def["param"]:
                return f"Oil prices stabilize at ${value}/barrel for the next 3+ years"
            elif "gdp" in param_def["param"]:
                return f"Qatar GDP growth averages {value}% annually"
        
        elif category_id == "competitive":
            competitor_contexts = {
                "dubai_expansion": "Dubai announces aggressive expansion with major tax incentives and talent programs",
                "saudi_neom": "Saudi Arabia's NEOM launches as a competing financial/logistics zone with $100B+ investment",
                "uae_unified": "UAE emirates form unified economic strategy to dominate regional markets",
                "gcc_coop": "GCC countries agree on regional cooperation framework, reducing internal competition",
                "singapore": "Singapore financial institutions establish major GCC presence",
                "china": "China establishes strategic partnership with regional competitor, shifting trade flows",
            }
            return competitor_contexts.get(value, f"Competitive scenario: {value}")
        
        elif category_id == "policy":
            policy_contexts = {
                "accelerated": "Government mandates accelerated Qatarization with strict quotas and penalties",
                "gradual": "Government pursues gradual Qatarization over 10+ years with incentives",
                "open": "Immigration policy liberalized for skilled workers, easing talent acquisition",
                "restricted": "Immigration requirements tightened, limiting available talent pool",
                "high": "Government provides substantial subsidies and incentives for target sector",
                "low": "Market-driven approach with reduced government subsidies",
            }
            return policy_contexts.get(value, f"Policy scenario: {value}")
        
        elif category_id == "timing":
            if "launch" in param_def["param"]:
                return f"Target launch/implementation date set for {value}"
            else:
                timing_contexts = {
                    "phased_5yr": "Phased implementation over 5 years with milestone reviews",
                    "phased_10yr": "Long-term phased implementation over 10 years",
                    "big_bang": "Rapid 'big bang' implementation with concentrated investment",
                }
                return timing_contexts.get(value, f"Timing: {value}")
        
        return param_def["description"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            "deep_scenario_count": len(DEEP_SCENARIO_TYPES),
            "broad_categories": list(BROAD_CATEGORIES.keys()),
            "broad_scenarios_per_category": 6,
            "total_broad_scenarios": 24,
            "total_scenarios": 30,
            "structure": "1 base + 5 deep + 24 broad",
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_scenario_generator(llm_client=None) -> NSICScenarioGenerator:
    """Factory function to create NSICScenarioGenerator."""
    return NSICScenarioGenerator(llm_client=llm_client)
