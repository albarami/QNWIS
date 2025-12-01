"""
NSIC Scenario Generator

Generates 30 scenarios from ANY user question:
- 1 Base Case: Current conditions analysis
- 5 Deep Scenarios: Strategic variations (Engine A, 100 turns)
- 24 Broad Scenarios: Parametric variations (Engine B, 25 turns)

Key Features:
- Scenarios are DERIVED from user question (not generic)
- Stake-prompting for specificity (ported from QNWIS)
- Qatar context validation for realism
- Fixed 1+5+24 structure for consistent analysis
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
# DEEP SCENARIO TYPES (5 Fixed Strategic Types)
# =============================================================================

DEEP_SCENARIO_TYPES = [
    {
        "id": "optimistic",
        "name": "Optimistic Scenario",
        "description": "Best realistic case - favorable conditions align",
        "prompt_template": """
SCENARIO: OPTIMISTIC
Analyze under favorable but REALISTIC conditions:
- Strong oil prices and stable revenue
- Regional cooperation rather than competition
- Talent availability meets demand
- No major disruptions

Be specific: What exact conditions would make this succeed?
What are the realistic upper bounds given Qatar's constraints?

QUESTION TO ANALYZE: {question}
"""
    },
    {
        "id": "pessimistic",
        "name": "Pessimistic Scenario",
        "description": "Worst realistic case - challenges compound",
        "prompt_template": """
SCENARIO: PESSIMISTIC
Analyze under challenging but REALISTIC conditions:
- Oil price volatility or sustained low prices
- Intensified regional competition
- Talent shortage or brain drain
- Economic headwinds

Be specific: What exact challenges could derail this?
What are realistic downside scenarios (not apocalyptic)?

QUESTION TO ANALYZE: {question}
"""
    },
    {
        "id": "competitive_shock",
        "name": "Competitive Shock Scenario",
        "description": "Major competitor makes aggressive move",
        "prompt_template": """
SCENARIO: COMPETITIVE SHOCK
Analyze if a major competitor takes aggressive action:
- Dubai announces major expansion with tax incentives
- Saudi launches competing initiative with massive investment
- Singapore/Hong Kong expands GCC presence
- Regional cooperation excludes Qatar

Be specific: Which competitor? What exact move? What impact on Qatar?

QUESTION TO ANALYZE: {question}
"""
    },
    {
        "id": "policy_shift",
        "name": "Policy Shift Scenario",
        "description": "Government significantly changes approach",
        "prompt_template": """
SCENARIO: POLICY SHIFT
Analyze if Qatar government changes policy direction:
- Accelerated vs gradual nationalization
- Changed investment priorities
- New regulatory framework
- Shifted diplomatic/trade relationships

Be specific: Which policy? What change? Timeline? Impact on each option?

QUESTION TO ANALYZE: {question}
"""
    },
    {
        "id": "black_swan",
        "name": "Black Swan Scenario",
        "description": "Low-probability, high-impact disruption",
        "prompt_template": """
SCENARIO: BLACK SWAN
Analyze under unexpected major disruption:
- Regional geopolitical crisis
- Global financial system shock
- Technology disruption (AI displaces key industries)
- Climate/environmental crisis affecting Gulf

Be specific: What disruption is Qatar uniquely vulnerable to?
What would be the mechanism and timeline of impact?

QUESTION TO ANALYZE: {question}
"""
    },
]


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
    """Complete set of 30 scenarios for a user question."""
    original_question: str
    question_context: Dict[str, Any]
    base_case: GeneratedScenario
    deep_scenarios: List[GeneratedScenario]  # 5
    broad_scenarios: List[GeneratedScenario]  # 24
    generated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_count(self) -> int:
        return 1 + len(self.deep_scenarios) + len(self.broad_scenarios)
    
    @property
    def all_scenarios(self) -> List[GeneratedScenario]:
        return [self.base_case] + self.deep_scenarios + self.broad_scenarios
    
    @property
    def engine_a_scenarios(self) -> List[GeneratedScenario]:
        """Scenarios for Engine A (deep analysis, 100 turns)."""
        return [self.base_case] + self.deep_scenarios
    
    @property
    def engine_b_scenarios(self) -> List[GeneratedScenario]:
        """Scenarios for Engine B (broad exploration, 25 turns)."""
        return self.broad_scenarios
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_question": self.original_question,
            "question_context": self.question_context,
            "base_case": self.base_case.to_dict(),
            "deep_scenarios": [s.to_dict() for s in self.deep_scenarios],
            "broad_scenarios": [s.to_dict() for s in self.broad_scenarios],
            "total_count": self.total_count,
            "engine_a_count": len(self.engine_a_scenarios),
            "engine_b_count": len(self.engine_b_scenarios),
            "generated_at": self.generated_at.isoformat(),
        }


# =============================================================================
# NSIC SCENARIO GENERATOR
# =============================================================================

class NSICScenarioGenerator:
    """
    Generates 30 scenarios from ANY user question.
    
    Output Structure:
    - 1 Base Case: Analyze under current conditions
    - 5 Deep Scenarios: Strategic variations (Engine A, 100 turns each)
    - 24 Broad Scenarios: Parametric variations (Engine B, 25 turns each)
    
    Key Features:
    - Scenarios are DERIVED from user question
    - Stake-prompting ensures specificity
    - Qatar context validation for realism
    - Fixed structure for consistent analysis
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize scenario generator.
        
        Args:
            llm_client: Optional LLM client for enhanced question analysis.
                       If None, uses rule-based analysis.
        """
        self._llm_client = llm_client
        logger.info("NSICScenarioGenerator initialized")
    
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
        Generate 30 scenarios from user question.
        
        Args:
            user_question: The ministerial policy question
            
        Returns:
            ScenarioSet with 1 base + 5 deep + 24 broad scenarios
        """
        logger.info(f"Generating scenarios for: {user_question[:100]}...")
        
        # Step 1: Analyze the question to understand context
        context = await self._analyze_question(user_question)
        logger.info(f"Question context: domain={context.get('domain')}, options={context.get('options')}")
        
        # Step 2: Create base case
        base_case = self._create_base_case(user_question, context)
        
        # Step 3: Create 5 deep scenarios (strategic)
        deep_scenarios = await self._create_deep_scenarios(user_question, context)
        assert len(deep_scenarios) == 5, f"Expected 5 deep scenarios, got {len(deep_scenarios)}"
        
        # Step 4: Create 24 broad scenarios (parametric)
        broad_scenarios = self._create_broad_scenarios(user_question, context)
        assert len(broad_scenarios) == 24, f"Expected 24 broad scenarios, got {len(broad_scenarios)}"
        
        # Step 5: Assemble scenario set
        scenario_set = ScenarioSet(
            original_question=user_question,
            question_context=context,
            base_case=base_case,
            deep_scenarios=deep_scenarios,
            broad_scenarios=broad_scenarios,
        )
        
        logger.info(
            f"Generated {scenario_set.total_count} scenarios: "
            f"1 base + {len(deep_scenarios)} deep + {len(broad_scenarios)} broad"
        )
        
        return scenario_set
    
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
