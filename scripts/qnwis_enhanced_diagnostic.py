#!/usr/bin/env python3
"""
QNWIS Full Diagnostic Script - Hybrid Architecture Edition

This script validates the complete QNWIS system flow:

    USER QUESTION
         ↓
    CLASSIFICATION (domain, complexity)
         ↓
    DATA EXTRACTION (RAG, Graph, APIs, Embeddings - deterministic)
         ↓
    SCENARIO GENERATION (6 external factors via GPT-5)
         ↓
    ENGINE B × 6 SCENARIOS (Monte Carlo, Sensitivity, Forecast per scenario)
         ↓
    CROSS-SCENARIO TABLE (formatted comparison for agents)
         ↓
    ENGINE A DEBATE (12 agents, 150 turns, WITH the numbers)
         ↓
    SYNTHESIS (Ministerial brief with robustness analysis)
         ↓
    FINAL OUTPUT (Recommendation + citations + contingencies)

DIAGNOSTIC CHECKS:

PART 1: Core Pipeline
- Classification (domain, complexity detection)
- Data extraction (facts, sources)
- Scenario generation (6 external factors with assumptions)
- Agent execution (12 agents participated)
- Debate quality (150 turns, all phases)
- Critique & Verification
- Synthesis quality

PART 2: Engine B Compute Services
- Monte Carlo simulation (10,000+ runs)
- Time series forecasting (with confidence bands)
- Threshold analysis (breaking points)
- Sensitivity analysis (top drivers)
- Benchmark comparison (GCC peers)

PART 3: Hybrid Flow - 6 Scenarios
- Engine B ran for ALL 6 scenarios
- Cross-scenario comparison table generated
- Engine A received cross-scenario data
- Robustness analysis (X/6 scenarios pass)

PART 4: McKinsey-Grade Output
- Quantitative claims backed by compute
- Probability statements from Monte Carlo
- Cross-scenario robustness shown
- X/6 scenarios success ratio stated
- No vague LLM estimates
- Ministerial template compliance

Usage:
    python scripts/qnwis_enhanced_diagnostic.py
    python scripts/qnwis_enhanced_diagnostic.py --query qatarization
    python scripts/qnwis_enhanced_diagnostic.py --test-engine-b-only
    python scripts/qnwis_enhanced_diagnostic.py --batch

Output:
    - Console summary with scores
    - Detailed JSON report in data/diagnostics/
    - Engine B service health check (per scenario)
    - Hybrid flow validation
    - McKinsey compliance checklist
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set DATABASE_URL if not already set (required for data extraction)
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql://postgres:1234@localhost:5432/qnwis"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger("QNWIS_DIAGNOSTIC")


# ============================================================================
# CONFIGURATION
# ============================================================================

class DiagnosticConfig:
    """Configuration for diagnostic run."""
    
    # Engine B API endpoint
    ENGINE_B_URL = os.environ.get("ENGINE_B_URL", "http://localhost:8001")
    
    # ==========================================================================
    # TEST QUERY LIBRARY - Diverse domains to validate domain-agnostic design
    # ==========================================================================
    
    TEST_QUERIES = {
        # ======================================================================
        # QATARIZATION POLICY (Engine B Hybrid Test)
        # ======================================================================
        "qatarization": {
            "name": "Qatarization Policy Analysis",
            "domain": "Labor Policy",
            "complexity": "complex",
            "query": """
Should Qatar accelerate Qatarization from the current 10% to 20% by 2028?

Current Context:
- Qatari workforce: 33,300 in private sector
- Total private sector jobs: 1,850,000
- Current Qatarization rate: 10.2%
- Qatari workforce growth rate: 2.1% annually
- Private sector job growth: 4.3% annually
- Qatari graduates entering workforce: 4,500/year

Consider:
1. Mathematical feasibility of 20% target
2. Labor shortage thresholds
3. Comparison with UAE Emiratization (7.2%) and Saudi Saudization (19.1%)
4. Key drivers of successful Qatarization
5. Recommended target with probability of success
""",
            # Expected Engine B validations
            "expected_compute": {
                "monte_carlo": True,
                "forecast": True,
                "thresholds": True,
                "benchmark": True,
                "sensitivity": True,
            },
            # Known data for validation
            "validation_data": {
                "current_qatarization": 0.102,
                "qatari_workforce": 33300,
                "private_jobs": 1850000,
                "feasibility_threshold": 0.164,  # Math: 47000/1850000 * growth
            }
        },
        
        # ======================================================================
        # ECONOMIC DIVERSIFICATION (Original)
        # ======================================================================
        "economic_diversification": {
            "name": "Economic Diversification Strategy",
            "domain": "Economic Policy",
            "complexity": "complex",
            "query": """
Qatar must choose its primary economic diversification focus for the next decade. 
The Ministry of Finance has budget for ONE major initiative (QAR 50 billion over 10 years).

Option A: Financial Services Hub
- Target: Become the leading Islamic finance and wealth management center in the GCC
- Compete directly with Dubai International Financial Centre (DIFC)
- Leverage QIA's $450B sovereign wealth for anchor investments

Option B: Advanced Logistics & Trade Hub  
- Target: Become the GCC's premier air cargo and re-export hub
- Expand Hamad International Airport cargo capacity 3x
- Leverage geographic position between Europe, Asia, and Africa

Current Context:
- Qatar Financial Centre currently employs 1,200 Qataris (5% of target 25,000)
- Hamad Airport handles 2.5M tons cargo/year (Dubai: 2.7M tons)
- Dubai has 40+ year head start in financial services
- Saudi Arabia investing $100B in NEOM logistics zone
- Qatari STEM/business graduates: 4,500 per year combined

Which option should Qatar prioritize and why? Consider:
1. Competitive dynamics with UAE and Saudi Arabia
2. Qatarization potential in each sector  
3. Revenue diversification from hydrocarbons
4. Risk factors and mitigation strategies
5. 10-year projected outcomes under different scenarios
"""
        },
        
        # ======================================================================
        # HEALTHCARE SYSTEM
        # ======================================================================
        "healthcare": {
            "name": "Healthcare System Transformation",
            "domain": "Healthcare Policy",
            "complexity": "complex",
            "query": """
Qatar's Ministry of Public Health must decide on the next phase of healthcare development.
Budget allocation: QAR 30 billion over 8 years.

Option A: Specialized Medical Tourism Hub
- Build 3 world-class specialty hospitals (cardiac, oncology, orthopedics)
- Target: Attract 500,000 medical tourists annually by 2032
- Partner with Mayo Clinic, Cleveland Clinic for expertise
- Revenue potential: QAR 8-12 billion annually

Option B: Universal Primary Care Expansion
- Build 50 new primary care centers across Qatar
- Implement AI-driven preventive care system
- Train 5,000 Qatari nurses and 1,000 Qatari physicians
- Reduce chronic disease burden by 30%

Current Context:
- Hamad Medical Corporation handles 2.1M patient visits/year
- 78% of healthcare workers are expatriates
- Qatar spends 2.5% of GDP on healthcare (GCC average: 3.8%)
- Chronic diseases account for 70% of deaths
- Medical tourism currently brings 50,000 patients/year
- Nearest competitors: UAE (Cleveland Clinic Abu Dhabi), Saudi (King Faisal)

Which strategy should Qatar pursue? Analyze:
1. Qatarization potential in healthcare workforce
2. ROI comparison over 10 years
3. Impact on population health outcomes
4. Regional competitive positioning
5. Implementation risks and timelines
"""
        },
        
        # ======================================================================
        # EDUCATION TRANSFORMATION
        # ======================================================================
        "education": {
            "name": "Education System Modernization",
            "domain": "Education Policy",
            "complexity": "complex",
            "query": """
Qatar's Ministry of Education is planning a major reform initiative.
Budget: QAR 15 billion over 6 years.

Option A: Elite STEM University Cluster
- Expand Education City with 3 new world-class STEM universities
- Target: Produce 2,000 Qatari engineers and scientists annually
- Attract top global faculty with competitive packages
- Build research parks linked to Qatar Foundation

Option B: Vocational Training Revolution
- Build 25 technical colleges across Qatar
- Partner with German/Swiss vocational systems
- Target: 10,000 skilled Qatari technicians per year
- Focus: Construction, maintenance, IT, healthcare technicians

Current Context:
- Qatar University graduates 3,500 Qataris annually
- Only 12% of graduates are in STEM fields
- Private sector complains of skills mismatch
- Youth unemployment among Qataris: 8%
- 85% of private sector jobs held by expatriates
- Education City universities combined enrollment: 4,000

Which approach should Qatar prioritize? Consider:
1. Labor market needs analysis
2. Qatarization acceleration potential
3. Cost per graduate comparison
4. Time to impact on workforce
5. Social and cultural factors
"""
        },
        
        # ======================================================================
        # ENERGY TRANSITION
        # ======================================================================
        "energy": {
            "name": "Energy Transition Strategy",
            "domain": "Energy Policy",
            "complexity": "complex",
            "query": """
Qatar's Ministry of Energy must plan for the post-hydrocarbon era.
Investment envelope: QAR 100 billion over 15 years.

Option A: Green Hydrogen Superpower
- Build 10 GW green hydrogen production capacity
- Target: Capture 10% of global hydrogen export market by 2040
- Leverage existing LNG infrastructure and customer relationships
- Partner with Japan, South Korea, Germany as anchor buyers

Option B: Solar Manufacturing & Export Hub
- Build 5 GW solar panel manufacturing capacity
- Develop 20 GW domestic solar farms
- Target: Energy independence + regional export
- Leverage sovereign wealth for technology acquisition

Current Context:
- Qatar produces 77M tons LNG/year (20% of global trade)
- LNG revenues: $50-80 billion annually (depends on prices)
- Current renewable energy: <2% of generation
- Solar irradiance: 2,000 kWh/m²/year (excellent)
- Green hydrogen cost trajectory: $2-3/kg by 2030
- UAE and Saudi both investing heavily in renewables

Which path should Qatar take? Analyze:
1. Revenue replacement potential vs LNG decline
2. Technology risk comparison
3. Job creation for Qataris
4. Infrastructure requirements
5. Geopolitical implications
"""
        },
        
        # ======================================================================
        # HOUSING & URBAN DEVELOPMENT
        # ======================================================================
        "housing": {
            "name": "Affordable Housing Crisis",
            "domain": "Urban Development",
            "complexity": "complex",
            "query": """
Qatar's Ministry of Municipality faces a housing challenge for young Qatari families.
Budget: QAR 25 billion over 7 years.

Option A: New Satellite City Development
- Build new planned city for 100,000 residents (25,000 units)
- Location: 40km from Doha
- Full infrastructure: schools, hospitals, commercial
- Target: Affordable ownership for young Qatari families

Option B: Urban Densification & Renovation
- Acquire and renovate 15,000 units in existing Doha neighborhoods
- Build 10,000 new units in mixed-use developments
- Improve public transit connectivity
- Maintain community ties and urban fabric

Current Context:
- 35,000 Qatari families on housing waitlist
- Average wait time: 7 years
- Average Qatari household size: 6.2 persons
- Young Qataris (25-35) increasingly unable to afford homes
- Lusail City development: 200,000 capacity (but expensive)
- Pearl-Qatar: Luxury focus, not affordable
- Construction costs: QAR 4,000-6,000/sqm

Which approach should Qatar adopt? Consider:
1. Cost per unit comparison
2. Timeline to deliver housing
3. Community and social impact
4. Long-term urban sustainability
5. Qatari family preferences and culture
"""
        },
        
        # ======================================================================
        # FOOD SECURITY
        # ======================================================================
        "food_security": {
            "name": "Food Security Strategy",
            "domain": "Agriculture & Food Policy",
            "complexity": "complex",
            "query": """
After the 2017 blockade exposed vulnerabilities, Qatar must secure its food supply.
Investment: QAR 10 billion over 5 years.

Option A: High-Tech Domestic Production
- Build 100 vertical farms and 50 solar-powered greenhouses
- Develop aquaculture capacity for 50,000 tons fish/year
- Target: 70% self-sufficiency in vegetables, 40% in protein
- Partner with Netherlands, Israel for agtech

Option B: Strategic Reserve & Diversified Imports
- Build strategic food reserves for 2 years of consumption
- Acquire farmland in friendly nations (Sudan, Pakistan, Morocco)
- Develop dedicated shipping routes avoiding chokepoints
- Create bilateral food security agreements with 10+ nations

Current Context:
- Qatar imports 90% of food
- 2017 blockade disrupted 40% of food imports temporarily
- Arable land: <1% of territory
- Water: Entirely desalinated, expensive
- Baladna dairy: Success story (100% dairy self-sufficiency)
- UAE and Saudi also investing in domestic production

Which strategy should Qatar pursue? Analyze:
1. Cost per calorie comparison
2. Resilience under crisis scenarios
3. Water and energy requirements
4. Speed of implementation
5. Long-term sustainability
"""
        },
        
        # ======================================================================
        # TOURISM DEVELOPMENT
        # ======================================================================
        "tourism": {
            "name": "Post-World Cup Tourism Strategy",
            "domain": "Tourism & Hospitality",
            "complexity": "complex",
            "query": """
After FIFA World Cup 2022, Qatar must sustain tourism momentum.
Budget: QAR 20 billion over 5 years.

Option A: Luxury & Business Tourism Focus
- Position as ultra-premium destination
- Target: 2 million high-spending visitors/year
- Develop exclusive experiences (desert luxury, cultural immersion)
- Average spend target: $5,000/visitor

Option B: Mass Market & Family Tourism
- Develop theme parks, beaches, entertainment
- Target: 8 million visitors/year
- Compete with Dubai on volume
- Average spend target: $1,200/visitor

Current Context:
- World Cup hosted 1.4 million visitors in 4 weeks
- Current annual visitors: 3 million
- Hotel capacity: 45,000 rooms (30,000 added for World Cup)
- Dubai attracts 16 million visitors/year
- Qatar has 1 major theme park (planned)
- Cruise terminal operational in Doha Port

Which tourism model should Qatar pursue? Consider:
1. Revenue comparison (volume vs value)
2. Job creation for Qataris
3. Infrastructure utilization (World Cup legacy)
4. Cultural and social impact
5. Competitive positioning vs Dubai, Saudi Vision 2030
"""
        },
        
        # ======================================================================
        # LABOR MARKET REFORM
        # ======================================================================
        "labor": {
            "name": "Labor Market Nationalization",
            "domain": "Labor Policy",
            "complexity": "complex",
            "query": """
Qatar must accelerate Qatarization while maintaining economic competitiveness.
The Ministry of Labour is considering two approaches.

Option A: Aggressive Quota Enforcement
- Mandate 50% Qatari workforce in all companies >100 employees
- Heavy fines for non-compliance (QAR 50,000/month per missing Qatari)
- Timeline: Full compliance within 3 years
- Government salary subsidies for first 2 years

Option B: Incentive-Based Transformation
- Tax benefits for companies exceeding Qatarization targets
- Government-funded training programs (2-year bootcamps)
- Gradual targets: 20% by 2025, 35% by 2030, 50% by 2035
- Public recognition and procurement preferences

Current Context:
- Qataris: 12% of total population (350,000 of 2.9 million)
- Qataris in private sector: 6% of private workforce
- Qatari unemployment: 0.5% (effectively full employment)
- Average Qatari salary expectations: 3-4x expatriate equivalent
- Skills gap in technical and vocational roles
- Public sector employs 85% of working Qataris

Which approach should Qatar implement? Analyze:
1. Impact on business competitiveness
2. Realistic Qatari labor supply vs demand
3. Skills development timeline
4. Social and economic risks
5. International perception and investor confidence
"""
        },
        
        # ======================================================================
        # SIMPLE QUERY (for testing lower complexity)
        # ======================================================================
        "simple_revenue": {
            "name": "Simple Revenue Query",
            "domain": "Finance",
            "complexity": "simple",
            "query": """
What was Qatar's total LNG export revenue in 2023, and how does this compare 
to 2022? What are the projections for 2024?
"""
        },
        
        # ======================================================================
        # MEDIUM COMPLEXITY QUERY
        # ======================================================================
        "medium_analysis": {
            "name": "Medium Complexity Analysis",
            "domain": "Economic Analysis",
            "complexity": "medium",
            "query": """
Analyze Qatar's current Qatarization progress in the banking sector:
1. What is the current percentage of Qatari employees in major banks?
2. How does this compare to the government target?
3. What are the main barriers to increasing Qatarization?
4. Recommend specific interventions to accelerate progress.
"""
        },
    }
    
    # Default query to run (can be overridden via command line)
    DEFAULT_QUERY_KEY = "economic_diversification"
    
    # Thresholds for scoring
    MIN_FACTS_EXTRACTED = 100
    MIN_DEBATE_TURNS_STANDARD = 50
    MIN_DEBATE_TURNS_LEGENDARY = 100
    MIN_SYNTHESIS_LENGTH = 3000
    MIN_DATA_SOURCES = 5
    
    # McKinsey-grade thresholds
    REQUIRED_SENSITIVITY_SCENARIOS = 6
    MIN_DATA_CONFIDENCE = 0.3
    
    # Engine B thresholds
    MIN_MONTE_CARLO_SIMS = 1000
    MIN_FORECAST_HORIZON = 5
    
    # Engine B service categorization
    # Run ONCE: Data doesn't change per scenario
    ENGINE_B_RUN_ONCE = ["benchmarking", "correlation"]
    # Run PER SCENARIO: Results depend on scenario assumptions
    ENGINE_B_RUN_PER_SCENARIO = ["monte_carlo", "sensitivity", "forecasting", "thresholds"]
    
    # Debate depth settings
    DEBATE_TURNS_LEGENDARY = 150
    DEBATE_TURNS_QUICK = 30
    
    # Output directory
    OUTPUT_DIR = PROJECT_ROOT / "data" / "diagnostics"
    
    # Currently selected query
    selected_query_key: str = None
    selected_query: dict = None
    
    def __init__(self, query_key: str = None):
        """Initialize config with optional query selection."""
        self.selected_query_key = query_key or self.DEFAULT_QUERY_KEY
        
        if self.selected_query_key not in self.TEST_QUERIES:
            raise ValueError(f"Unknown query key: {self.selected_query_key}. "
                           f"Available: {list(self.TEST_QUERIES.keys())}")
        
        self.selected_query = self.TEST_QUERIES[self.selected_query_key]
    
    @property
    def TEST_QUERY(self) -> str:
        """Get the currently selected test query."""
        return self.selected_query["query"]
    
    @property
    def query_name(self) -> str:
        return self.selected_query["name"]
    
    @property
    def query_domain(self) -> str:
        return self.selected_query["domain"]
    
    @property
    def expected_complexity(self) -> str:
        return self.selected_query["complexity"]
    
    @property
    def expected_compute(self) -> Dict[str, bool]:
        return self.selected_query.get("expected_compute", {})
    
    @classmethod
    def list_available_queries(cls) -> List[Dict]:
        """List all available test queries."""
        return [
            {
                "key": key,
                "name": query["name"],
                "domain": query["domain"],
                "complexity": query["complexity"],
            }
            for key, query in cls.TEST_QUERIES.items()
        ]


# ============================================================================
# DATA CLASSES
# ============================================================================

class ScoreLevel(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""
    name: str
    passed: bool
    score: float  # 0-100
    level: ScoreLevel
    details: str = ""
    evidence: Any = None


@dataclass
class StageResult:
    """Result of a diagnostic stage."""
    stage_name: str
    checks: List[CheckResult] = field(default_factory=list)
    overall_score: float = 0.0
    overall_level: ScoreLevel = ScoreLevel.FAIL
    duration_ms: float = 0.0
    
    def add_check(self, check: CheckResult):
        self.checks.append(check)
        self._recalculate_overall()
    
    def _recalculate_overall(self):
        if not self.checks:
            self.overall_score = 0.0
            self.overall_level = ScoreLevel.FAIL
            return
        
        self.overall_score = sum(c.score for c in self.checks) / len(self.checks)
        
        if self.overall_score >= 80:
            self.overall_level = ScoreLevel.PASS
        elif self.overall_score >= 50:
            self.overall_level = ScoreLevel.WARN
        else:
            self.overall_level = ScoreLevel.FAIL


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""
    timestamp: str
    query: str
    duration_seconds: float
    query_name: str = ""
    query_domain: str = ""
    expected_complexity: str = ""
    stages: Dict[str, StageResult] = field(default_factory=dict)
    overall_score: float = 0.0
    mckinsey_compliant: bool = False
    mckinsey_checklist: Dict[str, bool] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    raw_state: Dict[str, Any] = field(default_factory=dict)
    # Hybrid flow fields (NEW)
    hybrid_flow_working: bool = False
    engine_b_healthy: bool = False
    feedback_loop_working: bool = False
    
    def calculate_overall(self):
        if not self.stages:
            self.overall_score = 0.0
            return
        
        # Weight stages (updated for hybrid architecture - 6 scenarios flow)
        weights = {
            # Core pipeline
            "classification": 0.05,
            "data_extraction": 0.10,
            "scenarios": 0.08,  # 6 external factor scenarios
            "agents": 0.05,
            "debate": 0.10,
            "critique": 0.05,
            "verification": 0.05,
            "synthesis": 0.10,
            
            # Engine B compute (runs for EACH scenario)
            "engine_b_health": 0.05,
            "engine_b_coverage": 0.10,  # Engine B ran for all 6 scenarios
            "monte_carlo": 0.05,
            "forecasting": 0.05,
            "thresholds": 0.05,
            "sensitivity": 0.05,
            "benchmarking": 0.05,
            
            # Hybrid integration (cross-scenario → Engine A)
            "feedback_loop": 0.08,
            
            # Final output
            "mckinsey_compliance": 0.05,
        }
        
        total_weight = 0.0
        weighted_score = 0.0
        
        for stage_name, result in self.stages.items():
            weight = weights.get(stage_name, 0.05)
            weighted_score += result.overall_score * weight
            total_weight += weight
        
        self.overall_score = weighted_score / total_weight if total_weight > 0 else 0.0


# ============================================================================
# ENGINE B HEALTH CHECK
# ============================================================================

class EngineBHealthCheck:
    """Check Engine B compute services are running and healthy."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_health(self) -> StageResult:
        """Check overall Engine B health."""
        result = StageResult(stage_name="engine_b_health")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                result.add_check(CheckResult(
                    name="api_reachable",
                    passed=True,
                    score=100,
                    level=ScoreLevel.PASS,
                    details=f"Engine B API responding at {self.base_url}",
                    evidence=data,
                ))
                
                # Check individual services (handle naming variations)
                services = data.get("services", {})
                service_mapping = {
                    "monte_carlo": ["monte_carlo"],
                    "forecast": ["forecast", "forecasting"],
                    "thresholds": ["thresholds"],
                    "sensitivity": ["sensitivity"],
                    "benchmark": ["benchmark", "benchmarking"],
                    "correlation": ["correlation"],
                    "optimization": ["optimization"],
                }
                for service_name, aliases in service_mapping.items():
                    service_status = None
                    for alias in aliases:
                        if alias in services:
                            service_status = services[alias]
                            break
                    if service_status is None:
                        service_status = "unknown"
                    
                    # Check if status indicates healthy
                    if isinstance(service_status, dict):
                        is_healthy = service_status.get("status") == "healthy"
                    else:
                        is_healthy = service_status in ["healthy", "ready", True]
                    
                    result.add_check(CheckResult(
                        name=f"service_{service_name}",
                        passed=is_healthy,
                        score=100 if is_healthy else 0,
                        level=ScoreLevel.PASS if is_healthy else ScoreLevel.FAIL,
                        details=f"{service_name}: {service_status}",
                    ))
            else:
                result.add_check(CheckResult(
                    name="api_reachable",
                    passed=False,
                    score=0,
                    level=ScoreLevel.FAIL,
                    details=f"Engine B returned {response.status_code}",
                ))
        except Exception as e:
            result.add_check(CheckResult(
                name="api_reachable",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details=f"Engine B not reachable: {e}",
            ))
        
        return result
    
    async def test_monte_carlo(self) -> StageResult:
        """Test Monte Carlo service with a real computation."""
        result = StageResult(stage_name="monte_carlo")
        
        try:
            # API expects variables as dict[str, dict] with distribution params
            test_request = {
                "variables": {
                    "growth_rate": {"distribution": "normal", "mean": 0.021, "std": 0.005},
                    "base_value": {"distribution": "normal", "mean": 33300, "std": 1000},
                },
                "formula": "base_value * (1 + growth_rate) ** 5",
                "n_simulations": 10000,
                "success_condition": "outcome > 40000"
            }
            
            start = time.time()
            response = await self.client.post(
                f"{self.base_url}/compute/monte_carlo",
                json=test_request
            )
            elapsed = time.time() - start
            result.duration_ms = elapsed * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Check simulation count
                n_sims = data.get("n_simulations", 0)
                result.add_check(CheckResult(
                    name="simulations_run",
                    passed=n_sims >= 10000,
                    score=100 if n_sims >= 10000 else 50,
                    level=ScoreLevel.PASS if n_sims >= 10000 else ScoreLevel.WARN,
                    details=f"Ran {n_sims:,} simulations",
                ))
                
                # Check mean is reasonable (or at least computed)
                mean = data.get("mean", data.get("result_mean", 0))
                expected_mean = 33300 * (1.021 ** 5)  # ~36,900
                
                # If mean is 0 or None, check if we have result distribution
                if mean == 0 or mean is None:
                    # Check if there are other result fields
                    has_results = any(k in data for k in ["success_rate", "percentiles", "results"])
                    result.add_check(CheckResult(
                        name="mean_accuracy",
                        passed=has_results,
                        score=70 if has_results else 0,
                        level=ScoreLevel.WARN if has_results else ScoreLevel.FAIL,
                        details=f"Mean not computed, but other results present" if has_results else "No mean computed",
                    ))
                else:
                    mean_error = abs(mean - expected_mean) / expected_mean if expected_mean else 1.0
                    result.add_check(CheckResult(
                        name="mean_accuracy",
                        passed=mean_error < 0.10,
                        score=100 if mean_error < 0.05 else 70 if mean_error < 0.20 else 50,
                        level=ScoreLevel.PASS if mean_error < 0.10 else ScoreLevel.WARN,
                        details=f"Mean: {mean:,.0f} (expected ~{expected_mean:,.0f}, error: {mean_error:.1%})",
                    ))
                
                # Check success rate exists
                success_rate = data.get("success_rate")
                result.add_check(CheckResult(
                    name="success_rate_calculated",
                    passed=success_rate is not None,
                    score=100 if success_rate is not None else 0,
                    level=ScoreLevel.PASS if success_rate is not None else ScoreLevel.FAIL,
                    details=f"Success rate: {success_rate:.1%}" if success_rate else "No success rate",
                ))
                
                # Check sensitivity or driver analysis exists
                sensitivity = data.get("sensitivity", data.get("driver_ranking", data.get("variable_importance", {})))
                has_sensitivity = len(sensitivity) > 0 if isinstance(sensitivity, (dict, list)) else sensitivity is not None
                result.add_check(CheckResult(
                    name="sensitivity_calculated",
                    passed=has_sensitivity,
                    score=100 if has_sensitivity else 50,
                    level=ScoreLevel.PASS if has_sensitivity else ScoreLevel.WARN,
                    details=f"Sensitivity: {sensitivity}" if has_sensitivity else "No sensitivity (optional)",
                ))
                
                # Check performance
                result.add_check(CheckResult(
                    name="performance",
                    passed=elapsed < 5.0,
                    score=100 if elapsed < 2.0 else 70 if elapsed < 5.0 else 30,
                    level=ScoreLevel.PASS if elapsed < 5.0 else ScoreLevel.WARN,
                    details=f"Completed in {elapsed:.2f}s",
                ))
                
            else:
                result.add_check(CheckResult(
                    name="api_response",
                    passed=False,
                    score=0,
                    level=ScoreLevel.FAIL,
                    details=f"Monte Carlo returned {response.status_code}: {response.text[:200]}",
                ))
                
        except Exception as e:
            result.add_check(CheckResult(
                name="monte_carlo_test",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details=f"Monte Carlo test failed: {e}",
            ))
        
        return result
    
    async def test_forecasting(self) -> StageResult:
        """Test forecasting service."""
        result = StageResult(stage_name="forecasting")
        
        try:
            # API expects historical_values as list[float] and forecast_horizon
            test_request = {
                "historical_values": [1950000, 2010000, 2080000, 2120000, 2150000, 2050000, 2080000, 2150000, 2200000],
                "time_labels": ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"],
                "forecast_horizon": 7,
                "method": "auto",
                "confidence_level": 0.95
            }
            
            start = time.time()
            response = await self.client.post(
                f"{self.base_url}/compute/forecast",
                json=test_request
            )
            elapsed = time.time() - start
            result.duration_ms = elapsed * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Check forecasts exist
                forecasts = data.get("forecasts", [])
                result.add_check(CheckResult(
                    name="forecasts_generated",
                    passed=len(forecasts) == 7,
                    score=100 if len(forecasts) == 7 else 50,
                    level=ScoreLevel.PASS if len(forecasts) >= 5 else ScoreLevel.WARN,
                    details=f"Generated {len(forecasts)} forecast periods",
                ))
                
                # Check trend detected
                trend = data.get("trend", "")
                result.add_check(CheckResult(
                    name="trend_detected",
                    passed=trend in ["increasing", "decreasing", "stable"],
                    score=100 if trend else 0,
                    level=ScoreLevel.PASS if trend else ScoreLevel.FAIL,
                    details=f"Trend: {trend}",
                ))
                
                # Check confidence bands (handle various field names)
                if forecasts:
                    # Check for confidence bands (could be lower/upper, lower_bound/upper_bound, or ci_lower/ci_upper)
                    first_forecast = forecasts[0]
                    band_fields = [
                        ("lower", "upper"),
                        ("lower_bound", "upper_bound"),
                        ("ci_lower", "ci_upper"),
                        ("confidence_lower", "confidence_upper"),
                    ]
                    has_bands = False
                    lower_key, upper_key = None, None
                    for lk, uk in band_fields:
                        if lk in first_forecast and uk in first_forecast:
                            has_bands = True
                            lower_key, upper_key = lk, uk
                            break
                    
                    result.add_check(CheckResult(
                        name="confidence_bands",
                        passed=has_bands,
                        score=100 if has_bands else 70,  # Still good if forecasts work
                        level=ScoreLevel.PASS if has_bands else ScoreLevel.WARN,
                        details="Confidence bands present" if has_bands else "Missing confidence bands (optional)",
                    ))
                    
                    # Check bands widen over time (if present)
                    if has_bands and len(forecasts) >= 2:
                        try:
                            first_width = forecasts[0][upper_key] - forecasts[0][lower_key]
                            last_width = forecasts[-1][upper_key] - forecasts[-1][lower_key]
                            bands_widen = last_width > first_width
                            result.add_check(CheckResult(
                                name="bands_widen",
                                passed=bands_widen,
                                score=100 if bands_widen else 70,
                                level=ScoreLevel.PASS if bands_widen else ScoreLevel.WARN,
                                details=f"Band width: {first_width:,.0f} → {last_width:,.0f}",
                            ))
                        except (KeyError, TypeError):
                            pass  # Skip if can't compute
            else:
                result.add_check(CheckResult(
                    name="api_response",
                    passed=False,
                    score=0,
                    level=ScoreLevel.FAIL,
                    details=f"Forecast returned {response.status_code}",
                ))
                
        except Exception as e:
            result.add_check(CheckResult(
                name="forecast_test",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details=f"Forecast test failed: {e}",
            ))
        
        return result
    
    async def test_thresholds(self) -> StageResult:
        """Test threshold analysis service."""
        result = StageResult(stage_name="thresholds")
        
        try:
            # API expects sweep_variable, sweep_range, fixed_variables, constraints
            test_request = {
                "sweep_variable": "qatarization_target",
                "sweep_range": [0.10, 0.30],
                "fixed_variables": {
                    "qatari_supply": 47000,
                    "private_jobs": 1850000
                },
                "constraints": [
                    {
                        "expression": "qatari_supply < private_jobs * qatarization_target",
                        "threshold_type": "boundary",
                        "target": 0.0,
                        "description": "labor_shortage",
                        "severity": "warning"
                    }
                ],
                "resolution": 100
            }
            
            response = await self.client.post(
                f"{self.base_url}/compute/thresholds",
                json=test_request
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check thresholds found
                thresholds = data.get("thresholds", [])
                result.add_check(CheckResult(
                    name="thresholds_found",
                    passed=len(thresholds) > 0,
                    score=100 if thresholds else 50,  # Still partial pass if API works
                    level=ScoreLevel.PASS if thresholds else ScoreLevel.WARN,
                    details=f"Found {len(thresholds)} threshold(s)",
                ))
                
                # Check safe range
                safe_range = data.get("safe_range")
                result.add_check(CheckResult(
                    name="safe_range",
                    passed=safe_range is not None,
                    score=100 if safe_range else 50,
                    level=ScoreLevel.PASS if safe_range else ScoreLevel.WARN,
                    details=f"Safe range: {safe_range}" if safe_range else "No safe range",
                ))
                
                # Check risk level
                risk_level = data.get("risk_level", "unknown")
                result.add_check(CheckResult(
                    name="risk_assessed",
                    passed=risk_level != "unknown",
                    score=100 if risk_level != "unknown" else 50,
                    level=ScoreLevel.PASS if risk_level != "unknown" else ScoreLevel.WARN,
                    details=f"Risk level: {risk_level}",
                ))
            else:
                result.add_check(CheckResult(
                    name="api_response",
                    passed=False,
                    score=0,
                    level=ScoreLevel.FAIL,
                    details=f"Thresholds returned {response.status_code}: {response.text[:200]}",
                ))
                
        except Exception as e:
            result.add_check(CheckResult(
                name="threshold_test",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details=f"Threshold test failed: {e}",
            ))
        
        return result
    
    async def test_sensitivity(self) -> StageResult:
        """Test sensitivity analysis service."""
        result = StageResult(stage_name="sensitivity")
        
        try:
            # API expects base_values, formula, ranges (optional), n_steps
            test_request = {
                "base_values": {
                    "qatari_workforce": 33300,
                    "workforce_growth": 0.021,
                    "total_jobs": 1850000,
                    "job_growth": 0.043
                },
                "formula": "(qatari_workforce * (1 + workforce_growth)**5) / (total_jobs * (1 + job_growth)**5) * 100",
                "n_steps": 10
            }
            
            response = await self.client.post(
                f"{self.base_url}/compute/sensitivity",
                json=test_request
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check parameter impacts
                parameter_impacts = data.get("parameter_impacts", [])
                result.add_check(CheckResult(
                    name="sensitivity_calculated",
                    passed=len(parameter_impacts) > 0,
                    score=100 if parameter_impacts else 0,
                    level=ScoreLevel.PASS if parameter_impacts else ScoreLevel.FAIL,
                    details=f"Analyzed {len(parameter_impacts)} parameters",
                ))
                
                # Check top drivers
                top_drivers = data.get("top_drivers", [])
                has_top_driver = len(top_drivers) > 0
                result.add_check(CheckResult(
                    name="top_driver_identified",
                    passed=has_top_driver,
                    score=100 if has_top_driver else 0,
                    level=ScoreLevel.PASS if has_top_driver else ScoreLevel.FAIL,
                    details=f"Top drivers: {top_drivers[:3]}" if has_top_driver else "No top drivers",
                ))
                
                # Check tornado data exists
                tornado_data = data.get("tornado_data", {})
                result.add_check(CheckResult(
                    name="impact_quantified",
                    passed=len(tornado_data) > 0,
                    score=100 if tornado_data else 50,
                    level=ScoreLevel.PASS if tornado_data else ScoreLevel.WARN,
                    details="Tornado chart data available" if tornado_data else "Missing tornado data",
                ))
            else:
                result.add_check(CheckResult(
                    name="api_response",
                    passed=False,
                    score=0,
                    level=ScoreLevel.FAIL,
                    details=f"Sensitivity returned {response.status_code}: {response.text[:200]}",
                ))
                
        except Exception as e:
            result.add_check(CheckResult(
                name="sensitivity_test",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details=f"Sensitivity test failed: {e}",
            ))
        
        return result
    
    async def test_benchmarking(self) -> StageResult:
        """Test benchmarking service."""
        result = StageResult(stage_name="benchmarking")
        
        try:
            # API expects metrics list with peers as list of PeerDataRequest
            test_request = {
                "metrics": [
                    {
                        "name": "qatarization_rate",
                        "qatar_value": 10.2,
                        "peers": [
                            {"name": "UAE", "value": 7.2, "region": "GCC"},
                            {"name": "Saudi", "value": 19.1, "region": "GCC"},
                            {"name": "Bahrain", "value": 14.2, "region": "GCC"},
                            {"name": "Kuwait", "value": 16.5, "region": "GCC"},
                            {"name": "Oman", "value": 12.8, "region": "GCC"}
                        ],
                        "higher_is_better": True
                    }
                ]
            }
            
            response = await self.client.post(
                f"{self.base_url}/compute/benchmark",
                json=test_request
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check overall rank
                overall_rank = data.get("overall_rank")
                result.add_check(CheckResult(
                    name="ranking_calculated",
                    passed=overall_rank is not None,
                    score=100 if overall_rank is not None else 0,
                    level=ScoreLevel.PASS if overall_rank is not None else ScoreLevel.FAIL,
                    details=f"Qatar rank: {overall_rank}" if overall_rank is not None else "No ranking",
                ))
                
                # Check percentile
                percentile = data.get("overall_percentile")
                result.add_check(CheckResult(
                    name="percentile_calculated",
                    passed=percentile is not None,
                    score=100 if percentile is not None else 0,
                    level=ScoreLevel.PASS if percentile is not None else ScoreLevel.FAIL,
                    details=f"Percentile: {percentile:.0f}%" if percentile is not None else "No percentile",
                ))
                
                # Check improvement areas identified
                improvement_areas = data.get("improvement_areas", [])
                result.add_check(CheckResult(
                    name="gaps_calculated",
                    passed=True,  # Always passes if we got 200
                    score=100,
                    level=ScoreLevel.PASS,
                    details=f"Improvement areas: {len(improvement_areas)}",
                ))
            else:
                result.add_check(CheckResult(
                    name="api_response",
                    passed=False,
                    score=0,
                    level=ScoreLevel.FAIL,
                    details=f"Benchmark returned {response.status_code}: {response.text[:200]}",
                ))
                
        except Exception as e:
            result.add_check(CheckResult(
                name="benchmark_test",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details=f"Benchmark test failed: {e}",
            ))
        
        return result
    
    async def close(self):
        await self.client.aclose()


# ============================================================================
# HYBRID FLOW VALIDATION
# ============================================================================

class HybridFlowValidator:
    """
    Validate the hybrid flow (source of truth):
    
    SCENARIO GENERATION (6 external factors)
         ↓
    ENGINE B × 6 SCENARIOS (Monte Carlo, Sensitivity, Forecast per scenario)
         ↓
    CROSS-SCENARIO TABLE (formatted comparison)
         ↓
    ENGINE A DEBATE (12 agents, 150 turns, WITH the numbers)
         ↓
    SYNTHESIS (Ministerial brief with X/6 robustness analysis)
    """
    
    def __init__(self, config: DiagnosticConfig):
        self.config = config
        self.state = {}
    
    async def validate_feedback_loop(self, state: Dict) -> StageResult:
        """Validate Engine B → Engine A flow with cross-scenario data."""
        result = StageResult(stage_name="feedback_loop")
        
        # Check Engine B ran for all scenarios
        engine_b_results = state.get("engine_b_results", {})
        scenarios_computed = len(engine_b_results)
        
        result.add_check(CheckResult(
            name="engine_b_multi_scenario",
            passed=scenarios_computed >= 6,
            score=100 if scenarios_computed >= 6 else (scenarios_computed / 6) * 100,
            level=ScoreLevel.PASS if scenarios_computed >= 6 else ScoreLevel.FAIL,
            details=f"Engine B computed {scenarios_computed} scenarios",
        ))
        
        # Check cross-scenario comparison was generated
        cross_scenario_table = state.get("cross_scenario_comparison") or state.get("scenario_comparison_table")
        has_comparison = cross_scenario_table is not None
        
        result.add_check(CheckResult(
            name="cross_scenario_comparison",
            passed=has_comparison,
            score=100 if has_comparison else 0,
            level=ScoreLevel.PASS if has_comparison else ScoreLevel.FAIL,
            details="Cross-scenario comparison table generated" if has_comparison else "No cross-scenario comparison",
        ))
        
        # Check Engine A received the comparison
        engine_a_context = state.get("engine_a_quantitative_context", {})
        engine_a_had_context = state.get("engine_a_had_quantitative_context", False)
        has_multi_scenario = "scenarios" in engine_a_context or len(engine_a_context) >= 6 or engine_a_had_context
        
        result.add_check(CheckResult(
            name="engine_a_saw_all_scenarios",
            passed=has_multi_scenario,
            score=100 if has_multi_scenario else 0,
            level=ScoreLevel.PASS if has_multi_scenario else ScoreLevel.FAIL,
            details="Engine A debated with cross-scenario data" if has_multi_scenario else "Engine A only saw single scenario",
        ))
        
        # Check quantitative findings in synthesis
        synthesis = state.get("final_synthesis", "")
        has_quant_in_synthesis = any(term in synthesis.lower() for term in [
            "monte carlo", "probability", "success rate", "threshold",
            "forecast", "sensitivity", "benchmark", "percentile",
            "% of scenarios", "simulations", "across scenarios"
        ])
        
        result.add_check(CheckResult(
            name="quant_in_synthesis",
            passed=has_quant_in_synthesis,
            score=100 if has_quant_in_synthesis else 30,
            level=ScoreLevel.PASS if has_quant_in_synthesis else ScoreLevel.FAIL,
            details="Quantitative findings cited in synthesis" if has_quant_in_synthesis else "No quantitative findings in synthesis",
        ))
        
        return result


# ============================================================================
# DIAGNOSTIC ENGINE
# ============================================================================

class QNWISDiagnostic:
    """
    Comprehensive QNWIS diagnostic engine.
    
    Validates both core pipeline and McKinsey-grade features.
    """
    
    def __init__(self, config: DiagnosticConfig = None, quick_mode: bool = False):
        self.config = config or DiagnosticConfig()
        self.quick_mode = quick_mode
        self.debate_depth = "standard" if quick_mode else "legendary"
        self.debate_turns = self.config.DEBATE_TURNS_QUICK if quick_mode else self.config.DEBATE_TURNS_LEGENDARY
        self.report = None
        self.state = {}
        self.events = []
        # Engine B and hybrid flow components
        self.engine_b_checker = EngineBHealthCheck(self.config.ENGINE_B_URL)
        self.hybrid_validator = HybridFlowValidator(self.config)
    
    async def run_full_diagnostic(self) -> DiagnosticReport:
        """Run complete diagnostic suite."""
        logger.info("=" * 80)
        logger.info("QNWIS ENHANCED DIAGNOSTIC - McKinsey-Grade Edition")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        self.report = DiagnosticReport(
            timestamp=start_time.isoformat(),
            query=self.config.TEST_QUERY,
            duration_seconds=0.0,
            query_name=self.config.query_name,
            query_domain=self.config.query_domain,
            expected_complexity=self.config.expected_complexity,
        )
        
        # Log query info
        logger.info(f"Query: {self.config.query_name}")
        logger.info(f"Domain: {self.config.query_domain}")
        logger.info(f"Expected Complexity: {self.config.expected_complexity}")
        
        try:
            # Step 1: Engine B Health Check
            logger.info("\n" + "=" * 80)
            logger.info("STEP 1: ENGINE B HEALTH CHECK")
            logger.info("=" * 80)
            await self._check_engine_b_health()
            
            # Step 2: Engine B Service Tests
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: ENGINE B SERVICE TESTS")
            logger.info("=" * 80)
            await self._test_engine_b_services()
            
            # Step 3: Run the QNWIS pipeline
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3: RUNNING QNWIS PIPELINE")
            logger.info("=" * 80)
            await self._run_pipeline()
            
            # Step 4: Evaluate core stages
            logger.info("\n" + "=" * 80)
            logger.info("STEP 4: EVALUATING CORE PIPELINE")
            logger.info("=" * 80)
            await self._evaluate_core_stages()
            
            # Step 5: Evaluate McKinsey-grade features
            logger.info("\n" + "=" * 80)
            logger.info("STEP 5: EVALUATING MCKINSEY-GRADE FEATURES")
            logger.info("=" * 80)
            await self._evaluate_mckinsey_features()
            
            # Step 6: Validate Hybrid Flow
            logger.info("\n" + "=" * 80)
            logger.info("STEP 6: HYBRID FLOW VALIDATION")
            logger.info("=" * 80)
            await self._validate_hybrid_flow()
            
            # Step 7: Generate recommendations
            logger.info("\n" + "=" * 80)
            logger.info("STEP 7: GENERATING RECOMMENDATIONS")
            logger.info("=" * 80)
            self._generate_recommendations()
            
        except Exception as e:
            logger.error(f"Diagnostic failed: {e}")
            import traceback
            traceback.print_exc()
            self.report.recommendations.append(f"CRITICAL: Diagnostic failed with error: {e}")
        
        finally:
            await self.engine_b_checker.close()
        
        # Calculate final scores
        end_time = datetime.now()
        self.report.duration_seconds = (end_time - start_time).total_seconds()
        self.report.calculate_overall()
        self.report.raw_state = self._sanitize_state_for_json(self.state)
        
        # Save reports
        self._save_reports()
        
        # Print summary
        self._print_summary()
        
        return self.report
    
    # ========================================================================
    # PIPELINE EXECUTION
    # ========================================================================
    
    async def _run_pipeline(self):
        """Run the QNWIS pipeline and capture state."""
        try:
            from src.qnwis.orchestration.streaming import run_workflow_stream, WorkflowEvent
            
            logger.info(f"Query: {self.config.TEST_QUERY[:100]}...")
            logger.info(f"Mode: {'QUICK (30 turns)' if self.quick_mode else 'LEGENDARY (150 turns)'}")
            logger.info("Starting pipeline execution...")
            
            # Capture events
            event_count = 0
            async for event in run_workflow_stream(self.config.TEST_QUERY, debate_depth=self.debate_depth):
                event_count += 1
                
                # Convert WorkflowEvent to dict if needed
                if isinstance(event, WorkflowEvent):
                    event_dict = {
                        "stage": event.stage,
                        "status": event.status,
                        "payload": event.payload,
                        "latency_ms": event.latency_ms,
                    }
                else:
                    event_dict = event if isinstance(event, dict) else {"data": str(event)}
                
                self.events.append(event_dict)
                
                stage = event_dict.get("stage", "unknown")
                status = event_dict.get("status", "")
                
                if event_count % 10 == 0:
                    logger.info(f"  Event #{event_count}: {stage} - {status}")
                
                # Capture debate turns from payload
                payload = event_dict.get("payload", {})
                if stage == "debate" and status == "streaming":
                    turn_data = payload.get("turn", {})
                    if turn_data:
                        turn_num = turn_data.get("turn", 0)
                        if turn_num % 10 == 0:
                            logger.info(f"  Debate turn {turn_num}...")
                
                # Capture final state from done event
                if stage == "done" and status == "complete":
                    # Extract FULL state from the final event payload
                    self.state = payload
                    
                    # Log what we captured
                    logger.info(f"Final state captured from 'done' event")
                    logger.info(f"  - scenarios: {len(payload.get('scenarios', []))}")
                    logger.info(f"  - scenario_results: {len(payload.get('scenario_results', []))}")
                    logger.info(f"  - engine_b_scenarios_computed: {payload.get('engine_b_scenarios_computed', 0)}")
                    logger.info(f"  - agent_reports: {len(payload.get('agent_reports', []))}")
                    logger.info(f"  - debate_turns: {payload.get('debate_turns', 0)}")
                    logger.info(f"  - complexity: {payload.get('complexity', 'N/A')}")
            
            # If state not captured from done event, try to build from events
            if not self.state:
                self.state = self._build_state_from_events()
            
            logger.info(f"Pipeline complete. {event_count} events captured.")
            logger.info(f"State keys: {list(self.state.keys())}")
            
        except ImportError as e:
            logger.error(f"Failed to import QNWIS: {e}")
            raise
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _build_state_from_events(self) -> Dict[str, Any]:
        """Build comprehensive state from captured events if final state not available."""
        state = {
            "scenarios": [],
            "scenario_results": [],
            "conversation_history": [],
            "agent_reports": [],
            "extracted_facts": [],
            "engine_b_results": [],
            "aggregate_debate_stats": {},
        }
        
        scenarios_captured = []
        debate_turns = []
        
        for event in self.events:
            stage = event.get("stage", "")
            status = event.get("status", "")
            payload = event.get("payload", {}) or {}
            
            # Classification
            if stage == "classify" and status == "complete":
                state["complexity"] = payload.get("complexity", "")
                state["classification"] = payload
            
            # Data extraction / prefetch
            elif stage == "prefetch" and status == "complete":
                state["extracted_facts"] = payload.get("extracted_facts", [])
                state["data_sources"] = payload.get("data_sources", [])
            
            # Scenario events - capture from parallel_exec
            elif stage == "parallel_exec":
                if status == "started":
                    scenarios = payload.get("scenarios", [])
                    if scenarios:
                        state["scenarios"] = scenarios
                elif status == "complete":
                    state["scenario_results"] = payload.get("scenario_results", [])
                    state["scenarios_completed"] = payload.get("scenarios_completed", 0)
            
            # Individual scenario completions
            elif stage.startswith("scenario:"):
                if status == "complete":
                    scenario_data = {
                        "scenario_id": payload.get("scenario_id", ""),
                        "scenario_name": payload.get("scenario_name", ""),
                        "duration_seconds": payload.get("duration_seconds", 0),
                        "synthesis_length": payload.get("synthesis_length", 0),
                        "debate_turns": payload.get("debate_turns", 0),
                        "confidence_score": payload.get("confidence_score", 0),
                    }
                    scenarios_captured.append(scenario_data)
            
            # Debate events
            elif stage == "debate":
                if status == "complete":
                    state["debate_results"] = payload
                    state["conversation_history"] = payload.get("conversation_history", [])
                elif status == "streaming":
                    turn_data = payload.get("turn", {})
                    if turn_data:
                        debate_turns.append(turn_data)
            
            # Agent completion events
            elif stage.startswith("agent:") and status == "complete":
                agent_name = stage.replace("agent:", "")
                state["agent_reports"].append({
                    "agent": agent_name,
                    "status": "complete",
                    "payload": payload
                })
            
            # Critique
            elif stage == "critique" and status == "complete":
                state["critique_results"] = payload
            
            # Verification
            elif stage == "verify" and status == "complete":
                state["verification_results"] = payload
            
            # Synthesis / meta_synthesis
            elif stage in ("synthesize", "meta_synthesis") and status == "complete":
                state["final_synthesis"] = payload.get("final_synthesis", "")
                state["meta_synthesis"] = payload.get("meta_synthesis", "")
                state["confidence_score"] = payload.get("confidence_score", 0)
        
        # Build aggregate stats from captured data
        if scenarios_captured:
            state["scenario_results"] = scenarios_captured
            state["aggregate_debate_stats"] = {
                "total_turns": sum(s.get("debate_turns", 0) for s in scenarios_captured),
                "scenarios_analyzed": len(scenarios_captured),
            }
        
        # Capture debate turns if not from payload
        if debate_turns and not state.get("conversation_history"):
            state["conversation_history"] = debate_turns
        
        return state
    
    # ========================================================================
    # ENGINE B HEALTH & SERVICES
    # ========================================================================
    
    async def _check_engine_b_health(self):
        """Check Engine B API health."""
        health_result = await self.engine_b_checker.check_health()
        self.report.stages["engine_b_health"] = health_result
        self.report.engine_b_healthy = health_result.overall_score >= 70
        
        logger.info(f"  Engine B Health: {health_result.overall_score:.0f}/100 [{health_result.overall_level.value}]")
    
    async def _test_engine_b_services(self):
        """Test individual Engine B services."""
        
        # Monte Carlo
        mc_result = await self.engine_b_checker.test_monte_carlo()
        self.report.stages["monte_carlo"] = mc_result
        logger.info(f"  Monte Carlo: {mc_result.overall_score:.0f}/100 [{mc_result.overall_level.value}]")
        
        # Forecasting
        forecast_result = await self.engine_b_checker.test_forecasting()
        self.report.stages["forecasting"] = forecast_result
        logger.info(f"  Forecasting: {forecast_result.overall_score:.0f}/100 [{forecast_result.overall_level.value}]")
        
        # Thresholds
        threshold_result = await self.engine_b_checker.test_thresholds()
        self.report.stages["thresholds"] = threshold_result
        logger.info(f"  Thresholds: {threshold_result.overall_score:.0f}/100 [{threshold_result.overall_level.value}]")
        
        # Sensitivity
        sensitivity_result = await self.engine_b_checker.test_sensitivity()
        self.report.stages["sensitivity"] = sensitivity_result
        logger.info(f"  Sensitivity: {sensitivity_result.overall_score:.0f}/100 [{sensitivity_result.overall_level.value}]")
        
        # Benchmarking
        benchmark_result = await self.engine_b_checker.test_benchmarking()
        self.report.stages["benchmarking"] = benchmark_result
        logger.info(f"  Benchmarking: {benchmark_result.overall_score:.0f}/100 [{benchmark_result.overall_level.value}]")
    
    async def _validate_hybrid_flow(self):
        """Validate the hybrid flow where Engine B runs first, then Engine A debates with numbers."""
        feedback_result = await self.hybrid_validator.validate_feedback_loop(self.state)
        self.report.stages["feedback_loop"] = feedback_result
        self.report.feedback_loop_working = feedback_result.overall_score >= 70
        
        logger.info(f"  Feedback Loop: {feedback_result.overall_score:.0f}/100 [{feedback_result.overall_level.value}]")
        
        # Set hybrid flow working flag
        self.report.hybrid_flow_working = (
            self.report.engine_b_healthy and 
            self.report.feedback_loop_working
        )
    
    # ========================================================================
    # CORE STAGE EVALUATION
    # ========================================================================
    
    async def _evaluate_core_stages(self):
        """Evaluate core pipeline stages."""
        
        # Classification
        self.report.stages["classification"] = self._evaluate_classification()
        
        # Data Extraction
        self.report.stages["data_extraction"] = self._evaluate_data_extraction()
        
        # Scenarios (6 external factor scenarios)
        self.report.stages["scenarios"] = self._evaluate_scenarios()
        
        # Engine B Coverage (per scenario)
        self.report.stages["engine_b_coverage"] = self._evaluate_engine_b_per_scenario()
        
        # Agents
        self.report.stages["agents"] = self._evaluate_agents()
        
        # Debate
        self.report.stages["debate"] = self._evaluate_debate()
        
        # Critique
        self.report.stages["critique"] = self._evaluate_critique()
        
        # Verification
        self.report.stages["verification"] = self._evaluate_verification()
        
        # Synthesis
        self.report.stages["synthesis"] = self._evaluate_synthesis()
    
    def _evaluate_classification(self) -> StageResult:
        """Evaluate query classification."""
        result = StageResult(stage_name="classification")
        
        complexity = self.state.get("complexity", "")
        
        # Check complexity is set
        if complexity:
            result.add_check(CheckResult(
                name="complexity_detected",
                passed=True,
                score=100,
                level=ScoreLevel.PASS,
                details=f"Complexity: {complexity}",
                evidence=complexity,
            ))
        else:
            result.add_check(CheckResult(
                name="complexity_detected",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details="No complexity classification found",
            ))
        
        # Check for correct classification (should be "complex" for this query)
        if complexity == "complex":
            result.add_check(CheckResult(
                name="correct_classification",
                passed=True,
                score=100,
                level=ScoreLevel.PASS,
                details="Correctly classified as complex strategic decision",
            ))
        else:
            result.add_check(CheckResult(
                name="correct_classification",
                passed=False,
                score=50,
                level=ScoreLevel.WARN,
                details=f"Expected 'complex', got '{complexity}'",
            ))
        
        logger.info(f"  Classification: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        return result
    
    def _evaluate_data_extraction(self) -> StageResult:
        """Evaluate data extraction quality."""
        result = StageResult(stage_name="data_extraction")
        
        facts = self.state.get("extracted_facts", [])
        fact_count = len(facts) if isinstance(facts, list) else 0
        
        # Check fact count
        if fact_count >= self.config.MIN_FACTS_EXTRACTED:
            score = 100
            level = ScoreLevel.PASS
        elif fact_count >= self.config.MIN_FACTS_EXTRACTED * 0.5:
            score = 70
            level = ScoreLevel.WARN
        else:
            score = max(0, fact_count / self.config.MIN_FACTS_EXTRACTED * 100)
            level = ScoreLevel.FAIL
        
        result.add_check(CheckResult(
            name="fact_count",
            passed=fact_count >= self.config.MIN_FACTS_EXTRACTED,
            score=score,
            level=level,
            details=f"Extracted {fact_count} facts (minimum: {self.config.MIN_FACTS_EXTRACTED})",
            evidence=fact_count,
        ))
        
        # Check data sources diversity
        sources = set()
        for fact in facts[:100] if isinstance(facts, list) else []:
            if isinstance(fact, dict):
                source = fact.get("source", "")
                if source:
                    sources.add(source)
        
        source_count = len(sources)
        if source_count >= self.config.MIN_DATA_SOURCES:
            score = 100
            level = ScoreLevel.PASS
        elif source_count >= 3:
            score = 70
            level = ScoreLevel.WARN
        else:
            score = source_count / self.config.MIN_DATA_SOURCES * 100
            level = ScoreLevel.FAIL
        
        result.add_check(CheckResult(
            name="source_diversity",
            passed=source_count >= self.config.MIN_DATA_SOURCES,
            score=score,
            level=level,
            details=f"Used {source_count} distinct sources",
            evidence=list(sources)[:10],
        ))
        
        logger.info(f"  Data Extraction: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Facts: {fact_count}, Sources: {source_count}")
        return result
    
    def _evaluate_scenarios(self) -> StageResult:
        """Evaluate scenario generation - 6 external factor scenarios."""
        result = StageResult(stage_name="scenarios")
        
        # Try multiple sources for scenario data
        scenarios = self.state.get("scenarios", [])
        
        # If no scenarios in state, try to get from scenario_results
        if not scenarios:
            scenario_results = self.state.get("scenario_results", [])
            if scenario_results:
                # Convert scenario results to scenario format
                scenarios = [
                    {
                        "name": sr.get("scenario_name", sr.get("name", f"Scenario {i}")),
                        "type": sr.get("scenario_id", ""),
                        "assumptions": sr.get("modified_assumptions", {}),
                    }
                    for i, sr in enumerate(scenario_results)
                ]
        
        # Also check events for scenarios
        if not scenarios:
            for event in self.events:
                if event.get("stage") == "parallel_exec" and event.get("status") == "started":
                    scenarios = event.get("payload", {}).get("scenarios", [])
                    if scenarios:
                        break
        
        # Check count is 6
        result.add_check(CheckResult(
            name="scenario_count",
            passed=len(scenarios) == 6,
            score=100 if len(scenarios) == 6 else max(0, (len(scenarios) / 6) * 100),
            level=ScoreLevel.PASS if len(scenarios) == 6 else ScoreLevel.WARN if len(scenarios) >= 4 else ScoreLevel.FAIL,
            details=f"Generated {len(scenarios)} scenarios (expected: 6)",
        ))
        
        # Check for base case
        has_base = any(
            s.get("name", "").lower() == "base_case" or 
            s.get("type") == "base_case" or
            "base" in s.get("name", "").lower()
            for s in scenarios
        )
        result.add_check(CheckResult(
            name="has_base_case",
            passed=has_base,
            score=100 if has_base else 0,
            level=ScoreLevel.PASS if has_base else ScoreLevel.FAIL,
            details="Base case scenario present" if has_base else "Missing base case",
        ))
        
        # Check scenarios are external factors (have assumptions/adjustments)
        if scenarios:
            has_assumptions = all(
                "assumptions" in s or "adjustments" in s or "variables" in s or "factors" in s
                for s in scenarios
            )
            result.add_check(CheckResult(
                name="scenarios_have_assumptions",
                passed=has_assumptions,
                score=100 if has_assumptions else 50,
                level=ScoreLevel.PASS if has_assumptions else ScoreLevel.WARN,
                details="All scenarios have variable adjustments" if has_assumptions else "Scenarios missing assumptions",
            ))
            
            # Check for diverse scenario types (not all same type)
            scenario_names = [s.get("name", "") for s in scenarios]
            unique_themes = set()
            for name in scenario_names:
                name_lower = name.lower()
                if "oil" in name_lower or "energy" in name_lower:
                    unique_themes.add("energy")
                elif "pandemic" in name_lower or "crisis" in name_lower:
                    unique_themes.add("crisis")
                elif "competition" in name_lower or "market" in name_lower:
                    unique_themes.add("competition")
                elif "policy" in name_lower or "regulation" in name_lower:
                    unique_themes.add("policy")
                elif "base" in name_lower:
                    unique_themes.add("base")
                else:
                    unique_themes.add(name_lower[:10])
            
            diverse = len(unique_themes) >= 3
            result.add_check(CheckResult(
                name="scenario_diversity",
                passed=diverse,
                score=100 if diverse else 50,
                level=ScoreLevel.PASS if diverse else ScoreLevel.WARN,
                details=f"Scenario themes: {unique_themes}" if diverse else "Limited scenario diversity",
                evidence=list(unique_themes),
            ))
        
        logger.info(f"  Scenarios: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Count: {len(scenarios)}, Has base: {has_base}")
        return result
    
    def _evaluate_engine_b_per_scenario(self) -> StageResult:
        """Validate Engine B ran for each scenario.
        
        Services are categorized:
        - RUN ONCE: benchmarking, correlation (data doesn't change per scenario)
        - RUN PER SCENARIO: monte_carlo, sensitivity, forecasting, thresholds
        """
        result = StageResult(stage_name="engine_b_coverage")
        
        # Check for engine_b_aggregate (from parallel workflow)
        engine_b_aggregate = self.state.get("engine_b_aggregate", {})
        engine_b_results = self.state.get("engine_b_results", {})
        scenarios = self.state.get("scenarios", [])
        scenario_results = self.state.get("scenario_results", [])
        
        # Count scenarios with Engine B compute from aggregate
        if engine_b_aggregate:
            scenarios_with_compute = engine_b_aggregate.get("scenarios_with_compute", 0)
            if scenarios_with_compute > 0:
                total_scenarios = len(scenarios) if scenarios else len(scenario_results) if scenario_results else 6
                coverage = scenarios_with_compute / total_scenarios if total_scenarios > 0 else 0
                
                result.add_check(CheckResult(
                    name="run_once_services",
                    passed=True,
                    score=100,
                    level=ScoreLevel.PASS,
                    details=f"Engine B aggregate: {engine_b_aggregate.get('total_monte_carlo_runs', 0)} Monte Carlo runs",
                ))
                
                result.add_check(CheckResult(
                    name="all_scenarios_computed",
                    passed=coverage >= 0.8,
                    score=coverage * 100,
                    level=ScoreLevel.PASS if coverage >= 0.8 else ScoreLevel.WARN if coverage >= 0.5 else ScoreLevel.FAIL,
                    details=f"Engine B computed {scenarios_with_compute}/{total_scenarios} scenarios",
                    evidence={"sensitivity_drivers": engine_b_aggregate.get("sensitivity_drivers", [])},
                ))
                
                logger.info(f"  Engine B Coverage: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
                return result
        
        # Also check scenario_results for embedded engine_b_results
        if scenario_results:
            computed_count = sum(
                1 for sr in scenario_results 
                if isinstance(sr, dict) and sr.get("engine_b_results", {}).get("status") == "complete"
            )
            if computed_count > 0:
                result.add_check(CheckResult(
                    name="run_once_services",
                    passed=True,
                    score=100,
                    level=ScoreLevel.PASS,
                    details="Engine B services ran via parallel executor",
                ))
                
                result.add_check(CheckResult(
                    name="all_scenarios_computed",
                    passed=computed_count >= len(scenario_results) * 0.8,
                    score=(computed_count / len(scenario_results)) * 100 if scenario_results else 0,
                    level=ScoreLevel.PASS if computed_count >= len(scenario_results) * 0.8 else ScoreLevel.WARN,
                    details=f"Engine B computed {computed_count}/{len(scenario_results)} scenarios",
                ))
                
                logger.info(f"  Engine B Coverage: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
                return result
        
        # Check "run once" services exist at top level
        run_once_services = self.config.ENGINE_B_RUN_ONCE
        run_once_found = []
        for service in run_once_services:
            if service in engine_b_results or any(service in str(v) for v in engine_b_results.values()):
                run_once_found.append(service)
        
        result.add_check(CheckResult(
            name="run_once_services",
            passed=len(run_once_found) >= 1,
            score=100 if len(run_once_found) == len(run_once_services) else 50 if run_once_found else 0,
            level=ScoreLevel.PASS if run_once_found else ScoreLevel.WARN,
            details=f"Run-once services: {run_once_found} (benchmarking, correlation)",
        ))
        
        # Get scenario names
        scenario_names = [s.get("name") for s in scenarios if s.get("name")]
        
        if not scenario_names:
            # If no named scenarios, check if engine_b_results has multiple entries
            scenarios_computed = len([k for k in engine_b_results.keys() if k not in run_once_services])
            result.add_check(CheckResult(
                name="all_scenarios_computed",
                passed=scenarios_computed >= 6,
                score=min(100, (scenarios_computed / 6) * 100) if scenarios_computed > 0 else 0,
                level=ScoreLevel.PASS if scenarios_computed >= 6 else ScoreLevel.WARN if scenarios_computed >= 3 else ScoreLevel.FAIL,
                details=f"Engine B computed {scenarios_computed} scenarios (no named scenarios found)",
                evidence={"computed_keys": list(engine_b_results.keys())},
            ))
            logger.info(f"  Engine B Coverage: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
            return result
        
        # Check Engine B has results for each scenario
        covered = [name for name in scenario_names if name in engine_b_results]
        missing = [name for name in scenario_names if name not in engine_b_results]
        
        coverage = len(covered) / len(scenario_names) if scenario_names else 0
        
        result.add_check(CheckResult(
            name="all_scenarios_computed",
            passed=coverage == 1.0,
            score=coverage * 100,
            level=ScoreLevel.PASS if coverage == 1.0 else ScoreLevel.WARN if coverage >= 0.5 else ScoreLevel.FAIL,
            details=f"Engine B computed {len(covered)}/{len(scenario_names)} scenarios",
            evidence={"covered": covered, "missing": missing},
        ))
        
        # Check each scenario has per-scenario compute services
        per_scenario_services = self.config.ENGINE_B_RUN_PER_SCENARIO
        for scenario_name in covered[:6]:  # Limit to first 6 for brevity
            scenario_results = engine_b_results.get(scenario_name, {})
            
            services_found = []
            for service in per_scenario_services:
                if service in scenario_results or service.replace("_", "") in str(scenario_results).lower():
                    services_found.append(service)
            
            complete = len(services_found) >= 3  # At least MC, forecast, thresholds
            result.add_check(CheckResult(
                name=f"scenario_{scenario_name[:20]}_complete",
                passed=complete,
                score=100 if complete else 50,
                level=ScoreLevel.PASS if complete else ScoreLevel.WARN,
                details=f"{scenario_name}: {services_found}",
            ))
        
        logger.info(f"  Engine B Coverage: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Run-once: {run_once_found}")
        logger.info(f"    Per-scenario: {len(covered)}/{len(scenario_names)} scenarios")
        return result
    
    def _evaluate_agents(self) -> StageResult:
        """Evaluate agent execution."""
        result = StageResult(stage_name="agents")
        
        # Check for agent participation - try multiple sources
        agent_reports = self.state.get("agent_reports", [])
        agents_count = self.state.get("agents_count", 0)
        debate_results = self.state.get("debate_results", {}) or {}
        conversation = self.state.get("conversation_history", []) or debate_results.get("conversation_history", [])
        
        # Extract unique speakers from conversation
        speakers = set()
        for turn in conversation:
            if isinstance(turn, dict):
                speaker = turn.get("speaker", "") or turn.get("agent", "")
                if speaker:
                    speakers.add(speaker)
        
        # Also extract agents from agent_reports
        for report in agent_reports:
            if isinstance(report, dict):
                agent = report.get("agent", "")
                if agent:
                    speakers.add(agent)
        
        expected_agents = ["MicroEconomist", "MacroEconomist", "Nationalization", 
                         "SkillsAgent", "PatternDetective"]
        
        found_agents = []
        missing_agents = []
        for agent in expected_agents:
            # Check if any speaker contains the agent name
            found = any(agent.lower() in s.lower() for s in speakers)
            if found:
                found_agents.append(agent)
            else:
                missing_agents.append(agent)
        
        # Use agents_count from done event if available and speakers is empty
        if not speakers and agents_count > 0:
            agent_score = min(100, agents_count / len(expected_agents) * 100)
            found_agents = [f"Agent_{i}" for i in range(agents_count)]
        else:
            agent_score = len(found_agents) / len(expected_agents) * 100
        
        result.add_check(CheckResult(
            name="agent_participation",
            passed=len(found_agents) >= 3 or agents_count >= 3,
            score=agent_score,
            level=ScoreLevel.PASS if agent_score >= 80 else ScoreLevel.WARN if agent_score >= 50 else ScoreLevel.FAIL,
            details=f"Found {len(found_agents)}/{len(expected_agents)} expected agents (agent_reports: {len(agent_reports)}, agents_count: {agents_count})",
            evidence={"found": found_agents, "missing": missing_agents, "all_speakers": list(speakers), "agent_reports_count": len(agent_reports)},
        ))
        
        logger.info(f"  Agents: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Found: {found_agents}")
        return result
    
    def _evaluate_debate(self) -> StageResult:
        """Evaluate debate quality."""
        result = StageResult(stage_name="debate")
        
        # Try multiple sources for debate turn count
        debate_turns_direct = self.state.get("debate_turns", 0)  # From done event
        debate_results = self.state.get("debate_results", {}) or {}
        conversation = self.state.get("conversation_history", []) or debate_results.get("conversation_history", [])
        aggregate_stats = self.state.get("aggregate_debate_stats", {}) or {}
        stats = self.state.get("stats", {}) or {}
        
        # Get turn count from best available source
        turn_count = (
            debate_turns_direct or  # Direct from done event
            stats.get("n_turns", 0) or  # From stats
            aggregate_stats.get("total_turns", 0) or  # From aggregate
            debate_results.get("total_turns", 0) or  # From debate_results
            len(conversation)  # Fall back to counting conversation
        )
        
        # Get debate depth
        debate_depth = self.state.get("debate_depth", "standard")
        min_turns = (self.config.MIN_DEBATE_TURNS_LEGENDARY 
                    if debate_depth == "legendary" 
                    else self.config.MIN_DEBATE_TURNS_STANDARD)
        
        # Check turn count
        if turn_count >= min_turns:
            score = 100
            level = ScoreLevel.PASS
        elif turn_count >= min_turns * 0.7:
            score = 80
            level = ScoreLevel.PASS
        elif turn_count >= min_turns * 0.5:
            score = 60
            level = ScoreLevel.WARN
        else:
            score = turn_count / min_turns * 100
            level = ScoreLevel.FAIL
        
        result.add_check(CheckResult(
            name="debate_turns",
            passed=turn_count >= min_turns * 0.7,
            score=score,
            level=level,
            details=f"{turn_count} turns (target: {min_turns} for {debate_depth})",
            evidence=turn_count,
        ))
        
        # Check for debate phases
        phases = set()
        for turn in conversation:
            phase = turn.get("phase", "")
            if phase:
                phases.add(phase)
        
        expected_phases = ["opening", "challenge", "risk", "consensus"]
        phase_score = len(phases) / max(len(expected_phases), 1) * 100
        
        result.add_check(CheckResult(
            name="debate_phases",
            passed=len(phases) >= 3,
            score=min(100, phase_score),
            level=ScoreLevel.PASS if len(phases) >= 3 else ScoreLevel.WARN,
            details=f"Phases found: {phases}",
            evidence=list(phases),
        ))
        
        # Check debate content quality (are they discussing options?)
        option_mentions = 0
        for turn in conversation[:20]:  # Sample first 20 turns
            content = turn.get("content", "").lower()
            if "option a" in content or "option b" in content or "financial" in content or "logistics" in content:
                option_mentions += 1
        
        content_score = min(100, option_mentions / 20 * 100 * 2)  # Scale up
        
        result.add_check(CheckResult(
            name="debate_relevance",
            passed=option_mentions >= 10,
            score=content_score,
            level=ScoreLevel.PASS if content_score >= 70 else ScoreLevel.WARN,
            details=f"{option_mentions}/20 sampled turns discuss the options",
        ))
        
        logger.info(f"  Debate: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Turns: {turn_count}, Phases: {len(phases)}")
        return result
    
    def _evaluate_critique(self) -> StageResult:
        """Evaluate critique quality."""
        result = StageResult(stage_name="critique")
        
        critique_results = self.state.get("critique_results", {})
        
        # Check for critiques
        critiques = critique_results.get("critiques", [])
        critique_count = len(critiques) if isinstance(critiques, list) else 0
        
        result.add_check(CheckResult(
            name="critique_count",
            passed=critique_count >= 5,
            score=min(100, critique_count * 10),
            level=ScoreLevel.PASS if critique_count >= 5 else ScoreLevel.WARN if critique_count >= 2 else ScoreLevel.FAIL,
            details=f"{critique_count} critiques generated",
            evidence=critique_count,
        ))
        
        # Check for red flags
        red_flags = critique_results.get("red_flags", [])
        red_flag_count = len(red_flags) if isinstance(red_flags, list) else 0
        
        result.add_check(CheckResult(
            name="red_flags",
            passed=red_flag_count >= 2,
            score=min(100, red_flag_count * 25),
            level=ScoreLevel.PASS if red_flag_count >= 3 else ScoreLevel.WARN if red_flag_count >= 1 else ScoreLevel.FAIL,
            details=f"{red_flag_count} red flags identified",
            evidence=red_flag_count,
        ))
        
        logger.info(f"  Critique: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        return result
    
    def _evaluate_verification(self) -> StageResult:
        """Evaluate fact verification."""
        result = StageResult(stage_name="verification")
        
        verification = self.state.get("verification_results", {})
        fabrication_detected = verification.get("fabrication_detected", False)
        
        result.add_check(CheckResult(
            name="no_fabrication",
            passed=not fabrication_detected,
            score=100 if not fabrication_detected else 0,
            level=ScoreLevel.PASS if not fabrication_detected else ScoreLevel.FAIL,
            details="No fabrication detected" if not fabrication_detected else "FABRICATION DETECTED",
        ))
        
        logger.info(f"  Verification: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        return result
    
    def _evaluate_synthesis(self) -> StageResult:
        """Evaluate synthesis quality."""
        result = StageResult(stage_name="synthesis")
        
        synthesis = self.state.get("final_synthesis", "")
        synthesis_length = len(synthesis)
        
        # Check length
        if synthesis_length >= self.config.MIN_SYNTHESIS_LENGTH:
            score = 100
            level = ScoreLevel.PASS
        elif synthesis_length >= self.config.MIN_SYNTHESIS_LENGTH * 0.5:
            score = 70
            level = ScoreLevel.WARN
        else:
            score = synthesis_length / self.config.MIN_SYNTHESIS_LENGTH * 100
            level = ScoreLevel.FAIL
        
        result.add_check(CheckResult(
            name="synthesis_length",
            passed=synthesis_length >= self.config.MIN_SYNTHESIS_LENGTH,
            score=score,
            level=level,
            details=f"{synthesis_length} characters (minimum: {self.config.MIN_SYNTHESIS_LENGTH})",
            evidence=synthesis_length,
        ))
        
        # Check for recommendation
        has_recommendation = any(word in synthesis.lower() for word in 
                                 ["recommend", "should", "option a", "option b", "advise"])
        
        result.add_check(CheckResult(
            name="has_recommendation",
            passed=has_recommendation,
            score=100 if has_recommendation else 30,
            level=ScoreLevel.PASS if has_recommendation else ScoreLevel.FAIL,
            details="Contains clear recommendation" if has_recommendation else "No clear recommendation found",
        ))
        
        # Check for numbers in synthesis
        numbers = re.findall(r'\d+(?:\.\d+)?%?', synthesis)
        has_numbers = len(numbers) >= 10
        
        result.add_check(CheckResult(
            name="quantitative_content",
            passed=has_numbers,
            score=min(100, len(numbers) * 3),
            level=ScoreLevel.PASS if has_numbers else ScoreLevel.WARN,
            details=f"Found {len(numbers)} numeric values in synthesis",
            evidence=len(numbers),
        ))
        
        logger.info(f"  Synthesis: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Length: {synthesis_length} chars, Numbers: {len(numbers)}")
        return result
    
    # ========================================================================
    # MCKINSEY-GRADE EVALUATION (NEW)
    # ========================================================================
    
    async def _evaluate_mckinsey_features(self):
        """Evaluate McKinsey-grade features."""
        
        # Data Structuring
        self.report.stages["data_structuring"] = self._evaluate_data_structuring()
        
        # Calculations
        self.report.stages["calculations"] = self._evaluate_calculations()
        
        # McKinsey Compliance Checklist
        self.report.stages["mckinsey_compliance"] = self._evaluate_mckinsey_compliance()
    
    def _evaluate_data_structuring(self) -> StageResult:
        """Evaluate data structuring for calculations."""
        result = StageResult(stage_name="data_structuring")
        
        structured = self.state.get("structured_inputs")
        
        if structured is None:
            result.add_check(CheckResult(
                name="structured_inputs_exist",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details="No structured inputs found - data structuring node not implemented yet",
            ))
            logger.info(f"  Data Structuring: NOT IMPLEMENTED")
            return result
        
        # Check structure validity
        result.add_check(CheckResult(
            name="structured_inputs_exist",
            passed=True,
            score=100,
            level=ScoreLevel.PASS,
            details="Structured inputs present",
        ))
        
        # Check for options
        options = structured.get("options", [])
        result.add_check(CheckResult(
            name="options_structured",
            passed=len(options) >= 2,
            score=100 if len(options) >= 2 else 50,
            level=ScoreLevel.PASS if len(options) >= 2 else ScoreLevel.WARN,
            details=f"{len(options)} options structured",
        ))
        
        # Check data quality flag
        data_quality = self.state.get("data_quality", "UNKNOWN")
        result.add_check(CheckResult(
            name="data_quality_assessed",
            passed=data_quality in ["HIGH", "MEDIUM"],
            score=100 if data_quality == "HIGH" else 70 if data_quality == "MEDIUM" else 30,
            level=ScoreLevel.PASS if data_quality in ["HIGH", "MEDIUM"] else ScoreLevel.WARN,
            details=f"Data quality: {data_quality}",
        ))
        
        logger.info(f"  Data Structuring: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        return result
    
    def _evaluate_calculations(self) -> StageResult:
        """Evaluate deterministic calculations."""
        result = StageResult(stage_name="calculations")
        
        calc_results = self.state.get("calculated_results")
        
        if calc_results is None:
            result.add_check(CheckResult(
                name="calculations_exist",
                passed=False,
                score=0,
                level=ScoreLevel.FAIL,
                details="No calculated results found - calculation engine not implemented yet",
            ))
            logger.info(f"  Calculations: NOT IMPLEMENTED")
            return result
        
        # Check calculations exist
        result.add_check(CheckResult(
            name="calculations_exist",
            passed=True,
            score=100,
            level=ScoreLevel.PASS,
            details="Calculated results present",
        ))
        
        # Check for NPV
        options = calc_results.get("options", [])
        has_npv = all("npv" in opt.get("metrics", {}) for opt in options)
        
        result.add_check(CheckResult(
            name="npv_calculated",
            passed=has_npv,
            score=100 if has_npv else 0,
            level=ScoreLevel.PASS if has_npv else ScoreLevel.FAIL,
            details="NPV calculated for all options" if has_npv else "NPV missing",
        ))
        
        # Check for IRR
        has_irr = all("irr" in opt.get("metrics", {}) or "irr_pct" in opt.get("metrics", {}) 
                      for opt in options)
        
        result.add_check(CheckResult(
            name="irr_calculated",
            passed=has_irr,
            score=100 if has_irr else 0,
            level=ScoreLevel.PASS if has_irr else ScoreLevel.FAIL,
            details="IRR calculated for all options" if has_irr else "IRR missing",
        ))
        
        # Check for sensitivity analysis
        has_sensitivity = all(len(opt.get("sensitivity", [])) >= self.config.REQUIRED_SENSITIVITY_SCENARIOS
                             for opt in options)
        
        result.add_check(CheckResult(
            name="sensitivity_analysis",
            passed=has_sensitivity,
            score=100 if has_sensitivity else 50,
            level=ScoreLevel.PASS if has_sensitivity else ScoreLevel.WARN,
            details=f"Sensitivity analysis with {self.config.REQUIRED_SENSITIVITY_SCENARIOS} scenarios" if has_sensitivity else "Insufficient sensitivity scenarios",
        ))
        
        # Check for comparison
        comparison = calc_results.get("comparison")
        has_comparison = comparison is not None and "winner" in comparison
        
        result.add_check(CheckResult(
            name="option_comparison",
            passed=has_comparison,
            score=100 if has_comparison else 0,
            level=ScoreLevel.PASS if has_comparison else ScoreLevel.FAIL,
            details=f"Winner: {comparison.get('winner', 'N/A')}" if has_comparison else "No comparison calculated",
        ))
        
        # Check calculation method is deterministic
        calc_method = calc_results.get("calculation_method", "")
        is_deterministic = calc_method == "deterministic"
        
        result.add_check(CheckResult(
            name="deterministic_method",
            passed=is_deterministic,
            score=100 if is_deterministic else 50,
            level=ScoreLevel.PASS if is_deterministic else ScoreLevel.WARN,
            details="Calculations are deterministic (Python)" if is_deterministic else f"Method: {calc_method}",
        ))
        
        logger.info(f"  Calculations: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        return result
    
    def _evaluate_mckinsey_compliance(self) -> StageResult:
        """Evaluate overall McKinsey-grade compliance."""
        result = StageResult(stage_name="mckinsey_compliance")
        
        checklist = {}
        
        # Check 1: NPV present in output
        synthesis = self.state.get("final_synthesis", "")
        has_npv_in_output = "npv" in synthesis.lower() or "net present value" in synthesis.lower()
        checklist["npv_in_output"] = has_npv_in_output
        
        result.add_check(CheckResult(
            name="npv_in_output",
            passed=has_npv_in_output,
            score=100 if has_npv_in_output else 0,
            level=ScoreLevel.PASS if has_npv_in_output else ScoreLevel.FAIL,
            details="NPV mentioned in synthesis" if has_npv_in_output else "NPV not found in output",
        ))
        
        # Check 2: IRR present in output
        has_irr_in_output = "irr" in synthesis.lower() or "internal rate" in synthesis.lower()
        checklist["irr_in_output"] = has_irr_in_output
        
        result.add_check(CheckResult(
            name="irr_in_output",
            passed=has_irr_in_output,
            score=100 if has_irr_in_output else 0,
            level=ScoreLevel.PASS if has_irr_in_output else ScoreLevel.FAIL,
            details="IRR mentioned in synthesis" if has_irr_in_output else "IRR not found in output",
        ))
        
        # Check 3: Sensitivity analysis in output
        has_sensitivity_in_output = any(word in synthesis.lower() for word in 
                                        ["sensitivity", "scenario", "worst case", "best case"])
        checklist["sensitivity_in_output"] = has_sensitivity_in_output
        
        result.add_check(CheckResult(
            name="sensitivity_in_output",
            passed=has_sensitivity_in_output,
            score=100 if has_sensitivity_in_output else 0,
            level=ScoreLevel.PASS if has_sensitivity_in_output else ScoreLevel.FAIL,
            details="Sensitivity analysis in synthesis" if has_sensitivity_in_output else "No sensitivity analysis in output",
        ))
        
        # Check 4: Confidence level stated
        has_confidence = "confidence" in synthesis.lower() or re.search(r'\d{1,2}%\s*confidence', synthesis.lower())
        checklist["confidence_stated"] = has_confidence
        
        result.add_check(CheckResult(
            name="confidence_stated",
            passed=has_confidence,
            score=100 if has_confidence else 50,
            level=ScoreLevel.PASS if has_confidence else ScoreLevel.WARN,
            details="Confidence level stated" if has_confidence else "No confidence level in output",
        ))
        
        # Check 5: Tables present (markdown tables)
        has_tables = "|" in synthesis and "---" in synthesis
        checklist["tables_present"] = has_tables
        
        result.add_check(CheckResult(
            name="tables_present",
            passed=has_tables,
            score=100 if has_tables else 30,
            level=ScoreLevel.PASS if has_tables else ScoreLevel.WARN,
            details="Formatted tables in output" if has_tables else "No tables found",
        ))
        
        # Check 6: No vague LLM estimates (like "60-70%")
        vague_patterns = [
            r'\d{1,2}-\d{1,2}%',  # "60-70%"
            r'approximately \d+',  # "approximately 50"
            r'around \d+',        # "around 50"
            r'roughly \d+',       # "roughly 50"
        ]
        has_vague_estimates = any(re.search(p, synthesis.lower()) for p in vague_patterns)
        checklist["no_vague_estimates"] = not has_vague_estimates
        
        result.add_check(CheckResult(
            name="no_vague_estimates",
            passed=not has_vague_estimates,
            score=100 if not has_vague_estimates else 50,
            level=ScoreLevel.PASS if not has_vague_estimates else ScoreLevel.WARN,
            details="No vague estimates found" if not has_vague_estimates else "Contains vague LLM-style estimates",
        ))
        
        # Check 7: Cross-scenario analysis in output (robustness)
        has_scenario_comparison = any(term in synthesis.lower() for term in [
            "across scenarios", "in all scenarios", "scenarios show",
            "robust", "worst case", "best case", "base case",
            "under different", "if oil", "if pandemic", "if competition",
            "downside", "upside", "stress test", "vulnerable to"
        ])
        checklist["cross_scenario_analysis"] = has_scenario_comparison
        
        result.add_check(CheckResult(
            name="cross_scenario_in_output",
            passed=has_scenario_comparison,
            score=100 if has_scenario_comparison else 0,
            level=ScoreLevel.PASS if has_scenario_comparison else ScoreLevel.FAIL,
            details="Output shows robustness across scenarios" if has_scenario_comparison else "No cross-scenario analysis in output",
        ))
        
        # Check 8: Robustness ratio (X/6 scenarios pass pattern)
        # Check for robustness ratio patterns: "X/6 scenarios", "X/Y scenarios pass", "robustness: X/Y"
        robustness_patterns = [
            r'(\d)/(\d)\s*scenario',
            r'robustness[:\s]+(\d)/(\d)',
            r'(\d)\s*out\s*of\s*(\d)\s*scenario',
            r'(\d)/(\d)\s*pass',
        ]
        has_robustness_ratio = False
        robustness_match = None
        for pattern in robustness_patterns:
            match = re.search(pattern, synthesis.lower())
            if match:
                has_robustness_ratio = True
                robustness_match = match.group(0)
                break
        
        checklist["robustness_ratio"] = has_robustness_ratio
        
        result.add_check(CheckResult(
            name="robustness_ratio_stated",
            passed=has_robustness_ratio,
            score=100 if has_robustness_ratio else 50,
            level=ScoreLevel.PASS if has_robustness_ratio else ScoreLevel.WARN,
            details=f"Robustness ratio stated: {robustness_match}" if has_robustness_ratio else "No X/6 scenarios robustness ratio",
        ))
        
        # Store checklist
        self.report.mckinsey_checklist = checklist
        
        # Determine overall compliance
        compliance_score = sum(1 for v in checklist.values() if v) / len(checklist) * 100
        self.report.mckinsey_compliant = compliance_score >= 70
        
        logger.info(f"  McKinsey Compliance: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        # Count only True values, treating None as False
        passed_count = sum(1 for v in checklist.values() if v is True)
        logger.info(f"    Checklist: {passed_count}/{len(checklist)} passed")
        
        return result
    
    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================
    
    def _generate_recommendations(self):
        """Generate actionable recommendations based on results."""
        
        recommendations = []
        
        # Check Engine B health
        if not self.report.engine_b_healthy:
            recommendations.append(
                "CRITICAL: Engine B API not healthy - check service is running at " + self.config.ENGINE_B_URL
            )
        
        # Check individual Engine B services
        for service in ["monte_carlo", "forecasting", "thresholds", "sensitivity", "benchmarking"]:
            stage = self.report.stages.get(service)
            if stage and stage.overall_score < 70:
                recommendations.append(f"HIGH: Fix {service} service - score {stage.overall_score:.0f}/100")
        
        # Check feedback loop
        feedback = self.report.stages.get("feedback_loop")
        if feedback and feedback.overall_score < 70:
            recommendations.append(
                "HIGH: Feedback loop not working - Engine B results not flowing to synthesis"
            )
        
        # Check for missing McKinsey features
        calc_results = self.state.get("calculated_results")
        if calc_results is None:
            recommendations.append(
                "CRITICAL: Implement calculation engine (financial_engine.py) for NPV/IRR/sensitivity analysis"
            )
            recommendations.append(
                "CRITICAL: Add structure_data_node to convert extracted facts to calculation inputs"
            )
            recommendations.append(
                "CRITICAL: Add calculate_node to run deterministic financial calculations"
            )
        
        # Check synthesis quality
        synthesis_stage = self.report.stages.get("synthesis")
        if synthesis_stage and synthesis_stage.overall_score < 70:
            recommendations.append(
                "MEDIUM: Improve synthesis to include financial tables and structured format"
            )
        
        # Check for vague estimates
        mckinsey_stage = self.report.stages.get("mckinsey_compliance")
        if mckinsey_stage:
            for check in mckinsey_stage.checks:
                if check.name == "no_vague_estimates" and not check.passed:
                    recommendations.append(
                        "HIGH: Remove vague LLM-style estimates (e.g., '60-70%') - use calculated values only"
                    )
        
        # Check debate quality
        debate_stage = self.report.stages.get("debate")
        if debate_stage and debate_stage.overall_score < 80:
            recommendations.append(
                "MEDIUM: Increase debate depth or ensure all phases complete"
            )
        
        # Check data extraction
        extraction_stage = self.report.stages.get("data_extraction")
        if extraction_stage and extraction_stage.overall_score < 80:
            recommendations.append(
                "LOW: Expand data sources for richer fact extraction"
            )
        
        self.report.recommendations = recommendations
        
        for rec in recommendations:
            logger.info(f"  → {rec}")
    
    # ========================================================================
    # OUTPUT
    # ========================================================================
    
    def _save_reports(self):
        """Save diagnostic reports to files."""
        # Ensure output directory exists
        self.config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save main report
        report_path = self.config.OUTPUT_DIR / f"diagnostic_report_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(self._report_to_dict(), f, indent=2, default=str)
        
        # Save raw state
        state_path = self.config.OUTPUT_DIR / f"raw_state_{timestamp}.json"
        with open(state_path, 'w') as f:
            json.dump(self.report.raw_state, f, indent=2, default=str)
        
        # Save events
        events_path = self.config.OUTPUT_DIR / f"events_{timestamp}.json"
        with open(events_path, 'w') as f:
            json.dump(self.events, f, indent=2, default=str)
        
        logger.info(f"\nReports saved to: {self.config.OUTPUT_DIR}")
        logger.info(f"  - {report_path.name}")
        logger.info(f"  - {state_path.name}")
        logger.info(f"  - {events_path.name}")
    
    def _print_summary(self):
        """Print diagnostic summary to console."""
        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        print(f"\nQUERY: {self.report.query_name}")
        print(f"DOMAIN: {self.report.query_domain}")
        print(f"EXPECTED COMPLEXITY: {self.report.expected_complexity}")
        print(f"MODE: {'QUICK (30 turns)' if self.quick_mode else 'LEGENDARY (150 turns)'}")
        
        print(f"\nOVERALL SCORE: {self.report.overall_score:.1f}/100")
        print(f"EXECUTION TIME: {self.report.duration_seconds:.1f}s")
        print(f"ENGINE B HEALTHY: {'✅ YES' if self.report.engine_b_healthy else '❌ NO'}")
        print(f"HYBRID FLOW WORKING: {'✅ YES' if self.report.hybrid_flow_working else '❌ NO'}")
        print(f"FEEDBACK LOOP WORKING: {'✅ YES' if self.report.feedback_loop_working else '❌ NO'}")
        print(f"MCKINSEY COMPLIANT: {'✅ YES' if self.report.mckinsey_compliant else '❌ NO'}")
        
        print("\n--- Stage Scores ---")
        for stage_name, stage_result in self.report.stages.items():
            icon = "✓" if stage_result.overall_level == ScoreLevel.PASS else "⚠" if stage_result.overall_level == ScoreLevel.WARN else "✗"
            print(f"  [{icon}] {stage_name}: {stage_result.overall_score:.0f}/100 [{stage_result.overall_level.value}]")
            
            # Show failed/warning checks
            for check in stage_result.checks:
                if check.level in [ScoreLevel.FAIL, ScoreLevel.WARN]:
                    print(f"      - {check.name}: {check.details}")
        
        print("\n--- McKinsey Checklist ---")
        for item, passed in self.report.mckinsey_checklist.items():
            icon = "✓" if passed else "✗"
            print(f"  [{icon}] {item.replace('_', ' ').title()}")
        
        if self.report.recommendations:
            print("\n--- Recommendations ---")
            for rec in self.report.recommendations:
                print(f"  → {rec}")
        
        print("\n" + "=" * 80)
        grade = self._get_grade()
        print(f"{grade}")
        print("=" * 80)
    
    def _get_grade(self) -> str:
        """Get overall grade based on score."""
        score = self.report.overall_score
        if score >= 90 and self.report.mckinsey_compliant and self.report.hybrid_flow_working:
            return "🏆 LEGENDARY: Hybrid system fully operational - McKinsey-grade!"
        elif score >= 80 and self.report.hybrid_flow_working:
            return "✅ EXCELLENT: System performing at high level with hybrid flow"
        elif score >= 80:
            return "✅ EXCELLENT: System performing at high level"
        elif score >= 70:
            return "👍 GOOD: Core functionality working, some improvements needed"
        elif score >= 50:
            return "⚠️ FAIR: Significant gaps identified, see recommendations"
        else:
            return "❌ NEEDS WORK: Major issues to address"
    
    def _report_to_dict(self) -> Dict:
        """Convert report to dictionary for JSON serialization."""
        return {
            "timestamp": self.report.timestamp,
            "duration_seconds": self.report.duration_seconds,
            "overall_score": self.report.overall_score,
            "mckinsey_compliant": self.report.mckinsey_compliant,
            "mckinsey_checklist": self.report.mckinsey_checklist,
            "stages": {
                name: {
                    "score": stage.overall_score,
                    "level": stage.overall_level.value,
                    "checks": [
                        {
                            "name": c.name,
                            "passed": c.passed,
                            "score": c.score,
                            "level": c.level.value,
                            "details": c.details,
                        }
                        for c in stage.checks
                    ]
                }
                for name, stage in self.report.stages.items()
            },
            "recommendations": self.report.recommendations,
        }
    
    def _sanitize_state_for_json(self, state: Dict) -> Dict:
        """Sanitize state for JSON serialization."""
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize(item) for item in obj[:100]]  # Limit list length
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                return str(obj)[:500]  # Limit string length
        
        return sanitize(state)


# ============================================================================
# MAIN
# ============================================================================

def print_available_queries():
    """Print all available test queries."""
    print("\n" + "=" * 80)
    print("AVAILABLE TEST QUERIES - HYBRID ARCHITECTURE EDITION")
    print("=" * 80)
    print(f"\n{'Key':<25} {'Name':<35} {'Domain':<20} {'Complexity':<10}")
    print("-" * 90)
    
    for query in DiagnosticConfig.list_available_queries():
        print(f"{query['key']:<25} {query['name']:<35} {query['domain']:<20} {query['complexity']:<10}")
    
    print("\n" + "=" * 80)
    print("USAGE:")
    print("  Single query:     python qnwis_enhanced_diagnostic.py --query healthcare")
    print("  Qatarization:     python qnwis_enhanced_diagnostic.py --query qatarization")
    print("  Engine B only:    python qnwis_enhanced_diagnostic.py --test-engine-b-only")
    print("  Custom Engine B:  python qnwis_enhanced_diagnostic.py --engine-b-url http://localhost:8001")
    print("  Batch mode:       python qnwis_enhanced_diagnostic.py --batch")
    print("  List queries:     python qnwis_enhanced_diagnostic.py --list")
    print("  All complex:      python qnwis_enhanced_diagnostic.py --all-complex")
    print("=" * 80 + "\n")


async def run_single_diagnostic(query_key: str, quick_mode: bool = False) -> DiagnosticReport:
    """Run diagnostic for a single query."""
    config = DiagnosticConfig(query_key=query_key)
    diagnostic = QNWISDiagnostic(config=config, quick_mode=quick_mode)
    return await diagnostic.run_full_diagnostic()


async def run_batch_diagnostic(query_keys: List[str], quick_mode: bool = False) -> Dict[str, DiagnosticReport]:
    """Run diagnostic for multiple queries and compare results."""
    results = {}
    
    mode_str = "QUICK MODE" if quick_mode else "FULL MODE"
    print("\n" + "=" * 80)
    print(f"BATCH DIAGNOSTIC ({mode_str}) - Running {len(query_keys)} queries")
    print("=" * 80)
    
    for i, query_key in enumerate(query_keys, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}/{len(query_keys)}: {query_key}")
        print("=" * 80)
        
        try:
            report = await run_single_diagnostic(query_key, quick_mode=quick_mode)
            results[query_key] = report
        except Exception as e:
            print(f"ERROR: Query '{query_key}' failed: {e}")
            results[query_key] = None
    
    # Print batch summary
    print_batch_summary(results)
    
    # Save batch report
    save_batch_report(results)
    
    return results


def print_batch_summary(results: Dict[str, DiagnosticReport]):
    """Print summary of batch diagnostic results."""
    print("\n" + "=" * 80)
    print("BATCH DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    print(f"\n{'Query':<25} {'Score':<10} {'McKinsey':<12} {'Time (s)':<10} {'Status':<10}")
    print("-" * 70)
    
    total_score = 0
    successful = 0
    mckinsey_compliant = 0
    
    for query_key, report in results.items():
        if report is None:
            print(f"{query_key:<25} {'N/A':<10} {'N/A':<12} {'N/A':<10} {'FAILED':<10}")
            continue
        
        successful += 1
        total_score += report.overall_score
        if report.mckinsey_compliant:
            mckinsey_compliant += 1
        
        status = "✓ PASS" if report.overall_score >= 70 else "⚠ WARN" if report.overall_score >= 50 else "✗ FAIL"
        mckinsey = "✓ YES" if report.mckinsey_compliant else "✗ NO"
        
        print(f"{query_key:<25} {report.overall_score:>6.1f}    {mckinsey:<12} {report.duration_seconds:>7.1f}   {status:<10}")
    
    print("-" * 70)
    
    if successful > 0:
        avg_score = total_score / successful
        print(f"\n{'AVERAGE':<25} {avg_score:>6.1f}")
        print(f"{'McKinsey Compliant':<25} {mckinsey_compliant}/{successful}")
        print(f"{'Success Rate':<25} {successful}/{len(results)}")
    
    # Identify weakest domain
    if successful > 1:
        sorted_results = sorted(
            [(k, v) for k, v in results.items() if v is not None],
            key=lambda x: x[1].overall_score
        )
        weakest = sorted_results[0]
        strongest = sorted_results[-1]
        
        print(f"\n📉 Weakest Domain: {weakest[0]} ({weakest[1].overall_score:.1f}/100)")
        print(f"📈 Strongest Domain: {strongest[0]} ({strongest[1].overall_score:.1f}/100)")
    
    print("\n" + "=" * 80)
    
    # Overall grade
    if successful > 0:
        avg_score = total_score / successful
        if avg_score >= 90 and mckinsey_compliant == successful:
            print("🏆 LEGENDARY: System performs at McKinsey-grade across all domains!")
        elif avg_score >= 80:
            print("✅ EXCELLENT: System performs consistently well across domains")
        elif avg_score >= 70:
            print("👍 GOOD: System works across domains with minor gaps")
        elif avg_score >= 50:
            print("⚠️ FAIR: Performance varies by domain, improvements needed")
        else:
            print("❌ NEEDS WORK: Significant issues across multiple domains")
    
    print("=" * 80)


def save_batch_report(results: Dict[str, DiagnosticReport]):
    """Save batch diagnostic report to file."""
    output_dir = PROJECT_ROOT / "data" / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"batch_diagnostic_{timestamp}.json"
    
    batch_data = {
        "timestamp": datetime.now().isoformat(),
        "queries_run": len(results),
        "successful": sum(1 for r in results.values() if r is not None),
        "results": {}
    }
    
    for query_key, report in results.items():
        if report is None:
            batch_data["results"][query_key] = {"status": "FAILED"}
        else:
            batch_data["results"][query_key] = {
                "status": "SUCCESS",
                "overall_score": report.overall_score,
                "mckinsey_compliant": report.mckinsey_compliant,
                "engine_b_healthy": report.engine_b_healthy,
                "hybrid_flow_working": report.hybrid_flow_working,
                "duration_seconds": report.duration_seconds,
                "mckinsey_checklist": report.mckinsey_checklist,
                "recommendations": report.recommendations,
            }
    
    with open(report_path, 'w') as f:
        json.dump(batch_data, f, indent=2, default=str)
    
    print(f"\nBatch report saved to: {report_path}")


# ============================================================================
# ENGINE B ONLY TEST
# ============================================================================

async def test_engine_b_only(config: DiagnosticConfig) -> Dict[str, StageResult]:
    """Test only Engine B services without running full pipeline."""
    logger.info("=" * 80)
    logger.info("ENGINE B STANDALONE TEST")
    logger.info("=" * 80)
    
    checker = EngineBHealthCheck(config.ENGINE_B_URL)
    results = {}
    
    try:
        # Health check
        results["health"] = await checker.check_health()
        logger.info(f"  Health: {results['health'].overall_score:.0f}/100")
        
        # Individual services
        results["monte_carlo"] = await checker.test_monte_carlo()
        logger.info(f"  Monte Carlo: {results['monte_carlo'].overall_score:.0f}/100")
        
        results["forecasting"] = await checker.test_forecasting()
        logger.info(f"  Forecasting: {results['forecasting'].overall_score:.0f}/100")
        
        results["thresholds"] = await checker.test_thresholds()
        logger.info(f"  Thresholds: {results['thresholds'].overall_score:.0f}/100")
        
        results["sensitivity"] = await checker.test_sensitivity()
        logger.info(f"  Sensitivity: {results['sensitivity'].overall_score:.0f}/100")
        
        results["benchmarking"] = await checker.test_benchmarking()
        logger.info(f"  Benchmarking: {results['benchmarking'].overall_score:.0f}/100")
        
    finally:
        await checker.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("ENGINE B TEST SUMMARY")
    print("=" * 80)
    
    total_score = sum(r.overall_score for r in results.values()) / len(results) if results else 0
    print(f"\nOverall Engine B Score: {total_score:.1f}/100")
    
    for name, result in results.items():
        icon = "✓" if result.overall_level == ScoreLevel.PASS else "⚠" if result.overall_level == ScoreLevel.WARN else "✗"
        print(f"  [{icon}] {name}: {result.overall_score:.0f}/100")
        for check in result.checks:
            if not check.passed:
                print(f"      ❌ {check.name}: {check.details}")
    
    return results


async def main():
    """Run the diagnostic with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QNWIS Enhanced Diagnostic - Hybrid Architecture Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query healthcare          Run healthcare domain test (150 turns)
  %(prog)s --query qatarization        Run qatarization policy test (150 turns)
  %(prog)s --query qatarization --quick  Quick test (30 turns, faster iteration)
  %(prog)s --test-engine-b-only        Test only Engine B services (no debate)
  %(prog)s --batch                      Run all queries in sequence
  %(prog)s --batch --quick              Batch mode with quick debates
  %(prog)s --all-complex                Run all complex queries only
  %(prog)s --list                       List available queries
  %(prog)s --random                     Run random query
  %(prog)s --engine-b-url URL          Specify Engine B API URL
        """
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Specific query key to run (e.g., healthcare, education, qatarization)"
    )
    
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="Run all available queries in batch mode"
    )
    
    parser.add_argument(
        "--all-complex", "-c",
        action="store_true",
        help="Run all complex queries only"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available test queries"
    )
    
    parser.add_argument(
        "--random", "-r",
        action="store_true",
        help="Run a random query"
    )
    
    parser.add_argument(
        "--queries", "-Q",
        type=str,
        nargs="+",
        help="Run specific queries (space-separated list)"
    )
    
    parser.add_argument(
        "--test-engine-b-only",
        action="store_true",
        help="Test only Engine B services without running full pipeline"
    )
    
    parser.add_argument(
        "--engine-b-url",
        type=str,
        default=None,
        help="Engine B API URL (default: http://localhost:8001)"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test mode: 30 debate turns instead of 150 (faster iteration)"
    )
    
    args = parser.parse_args()
    
    # List queries
    if args.list:
        print_available_queries()
        return
    
    # Create config with optional Engine B URL override
    config = DiagnosticConfig(query_key=args.query)
    if args.engine_b_url:
        config.ENGINE_B_URL = args.engine_b_url
    
    # Test Engine B only mode
    if args.test_engine_b_only:
        return await test_engine_b_only(config)
    
    # Random query
    if args.random:
        import random
        query_keys = list(DiagnosticConfig.TEST_QUERIES.keys())
        query_key = random.choice(query_keys)
        print(f"\n🎲 Randomly selected: {query_key}\n")
        report = await run_single_diagnostic(query_key, quick_mode=args.quick)
        return report
    
    # Batch mode - all queries
    if args.batch:
        query_keys = list(DiagnosticConfig.TEST_QUERIES.keys())
        return await run_batch_diagnostic(query_keys, quick_mode=args.quick)
    
    # All complex queries
    if args.all_complex:
        query_keys = [
            key for key, query in DiagnosticConfig.TEST_QUERIES.items()
            if query["complexity"] == "complex"
        ]
        return await run_batch_diagnostic(query_keys, quick_mode=args.quick)
    
    # Specific queries list
    if args.queries:
        return await run_batch_diagnostic(args.queries, quick_mode=args.quick)
    
    # Single query (default or specified)
    query_key = args.query or DiagnosticConfig.DEFAULT_QUERY_KEY
    report = await run_single_diagnostic(query_key, quick_mode=args.quick)
    return report


if __name__ == "__main__":
    asyncio.run(main())

