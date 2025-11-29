#!/usr/bin/env python3
"""
QNWIS Full Diagnostic Script - McKinsey-Grade Edition

This script runs a comprehensive diagnostic of the QNWIS system, validating:

PART 1: Core Pipeline (Existing)
- Classification
- Data extraction
- Scenario generation  
- Agent execution
- Debate quality
- Critique
- Verification
- Synthesis

PART 2: McKinsey-Grade Features (New)
- Data structuring
- Deterministic calculations (NPV, IRR, payback)
- Sensitivity analysis
- Option comparison
- Number sourcing (no LLM-generated numbers)
- Ministerial template compliance

Usage:
    python scripts/qnwis_enhanced_diagnostic.py

Output:
    - Console summary with scores
    - Detailed JSON report in data/diagnostics/
    - McKinsey compliance checklist
"""

import asyncio
import json
import logging
import os
import re
import sys
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
    
    # ==========================================================================
    # TEST QUERY LIBRARY - Diverse domains to validate domain-agnostic design
    # ==========================================================================
    
    TEST_QUERIES = {
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
    
    def calculate_overall(self):
        if not self.stages:
            self.overall_score = 0.0
            return
        
        # Weight stages
        weights = {
            "classification": 0.05,
            "data_extraction": 0.15,
            "data_structuring": 0.10,  # NEW
            "calculations": 0.15,       # NEW
            "agents": 0.10,
            "debate": 0.15,
            "critique": 0.05,
            "verification": 0.05,
            "synthesis": 0.15,
            "mckinsey_compliance": 0.05,  # NEW
        }
        
        total_weight = 0.0
        weighted_score = 0.0
        
        for stage_name, result in self.stages.items():
            weight = weights.get(stage_name, 0.05)
            weighted_score += result.overall_score * weight
            total_weight += weight
        
        self.overall_score = weighted_score / total_weight if total_weight > 0 else 0.0


# ============================================================================
# DIAGNOSTIC ENGINE
# ============================================================================

class QNWISDiagnostic:
    """
    Comprehensive QNWIS diagnostic engine.
    
    Validates both core pipeline and McKinsey-grade features.
    """
    
    def __init__(self, config: DiagnosticConfig = None):
        self.config = config or DiagnosticConfig()
        self.report = None
        self.state = {}
        self.events = []
    
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
            # Step 1: Run the QNWIS pipeline
            logger.info("\n" + "=" * 80)
            logger.info("STEP 1: RUNNING QNWIS PIPELINE")
            logger.info("=" * 80)
            await self._run_pipeline()
            
            # Step 2: Evaluate core stages
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: EVALUATING CORE PIPELINE")
            logger.info("=" * 80)
            await self._evaluate_core_stages()
            
            # Step 3: Evaluate McKinsey-grade features
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3: EVALUATING MCKINSEY-GRADE FEATURES")
            logger.info("=" * 80)
            await self._evaluate_mckinsey_features()
            
            # Step 4: Generate recommendations
            logger.info("\n" + "=" * 80)
            logger.info("STEP 4: GENERATING RECOMMENDATIONS")
            logger.info("=" * 80)
            self._generate_recommendations()
            
        except Exception as e:
            logger.error(f"Diagnostic failed: {e}")
            import traceback
            traceback.print_exc()
            self.report.recommendations.append(f"CRITICAL: Diagnostic failed with error: {e}")
        
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
            logger.info("Starting pipeline execution...")
            
            # Capture events
            event_count = 0
            async for event in run_workflow_stream(self.config.TEST_QUERY, debate_depth="legendary"):
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
                    # Extract state from the final event payload
                    self.state = payload
                    logger.info(f"Final state captured from 'done' event")
            
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
        """Build state from captured events if final state not available."""
        state = {}
        
        for event in self.events:
            stage = event.get("stage", "")
            status = event.get("status", "")
            payload = event.get("payload", {})
            
            if status == "complete" and payload:
                # Merge payload into state
                if stage == "classify":
                    state["complexity"] = payload.get("complexity", "")
                    state["classification"] = payload
                elif stage == "prefetch":
                    state["extracted_facts"] = payload.get("extracted_facts", [])
                elif stage == "debate":
                    state["debate_results"] = payload
                    state["conversation_history"] = payload.get("conversation_history", [])
                elif stage == "critique":
                    state["critique_results"] = payload
                elif stage == "verify":
                    state["verification_results"] = payload
                elif stage in ("synthesize", "meta_synthesis"):
                    state["final_synthesis"] = payload.get("final_synthesis", "")
                    state["meta_synthesis"] = payload.get("meta_synthesis", "")
        
        return state
    
    # ========================================================================
    # CORE STAGE EVALUATION
    # ========================================================================
    
    async def _evaluate_core_stages(self):
        """Evaluate core pipeline stages."""
        
        # Classification
        self.report.stages["classification"] = self._evaluate_classification()
        
        # Data Extraction
        self.report.stages["data_extraction"] = self._evaluate_data_extraction()
        
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
    
    def _evaluate_agents(self) -> StageResult:
        """Evaluate agent execution."""
        result = StageResult(stage_name="agents")
        
        # Check for agent participation in debate
        debate_results = self.state.get("debate_results", {})
        conversation = debate_results.get("conversation_history", [])
        
        # Extract unique speakers
        speakers = set()
        for turn in conversation:
            speaker = turn.get("speaker", "")
            if speaker:
                speakers.add(speaker)
        
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
        
        agent_score = len(found_agents) / len(expected_agents) * 100
        
        result.add_check(CheckResult(
            name="agent_participation",
            passed=len(found_agents) >= 3,
            score=agent_score,
            level=ScoreLevel.PASS if agent_score >= 80 else ScoreLevel.WARN if agent_score >= 50 else ScoreLevel.FAIL,
            details=f"Found {len(found_agents)}/{len(expected_agents)} expected agents",
            evidence={"found": found_agents, "missing": missing_agents, "all_speakers": list(speakers)},
        ))
        
        logger.info(f"  Agents: {result.overall_score:.0f}/100 [{result.overall_level.value}]")
        logger.info(f"    Found: {found_agents}")
        return result
    
    def _evaluate_debate(self) -> StageResult:
        """Evaluate debate quality."""
        result = StageResult(stage_name="debate")
        
        debate_results = self.state.get("debate_results", {})
        conversation = debate_results.get("conversation_history", [])
        turn_count = len(conversation)
        
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
        
        print(f"\nOVERALL SCORE: {self.report.overall_score:.1f}/100")
        print(f"EXECUTION TIME: {self.report.duration_seconds:.1f}s")
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
        if score >= 90 and self.report.mckinsey_compliant:
            return "🏆 LEGENDARY: McKinsey-grade system fully operational!"
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
    print("AVAILABLE TEST QUERIES")
    print("=" * 80)
    print(f"\n{'Key':<25} {'Name':<35} {'Domain':<20} {'Complexity':<10}")
    print("-" * 90)
    
    for query in DiagnosticConfig.list_available_queries():
        print(f"{query['key']:<25} {query['name']:<35} {query['domain']:<20} {query['complexity']:<10}")
    
    print("\n" + "=" * 80)
    print("USAGE:")
    print("  Single query:  python qnwis_enhanced_diagnostic.py --query healthcare")
    print("  Batch mode:    python qnwis_enhanced_diagnostic.py --batch")
    print("  List queries:  python qnwis_enhanced_diagnostic.py --list")
    print("  All complex:   python qnwis_enhanced_diagnostic.py --all-complex")
    print("=" * 80 + "\n")


async def run_single_diagnostic(query_key: str) -> DiagnosticReport:
    """Run diagnostic for a single query."""
    config = DiagnosticConfig(query_key=query_key)
    diagnostic = QNWISDiagnostic(config=config)
    return await diagnostic.run_full_diagnostic()


async def run_batch_diagnostic(query_keys: List[str]) -> Dict[str, DiagnosticReport]:
    """Run diagnostic for multiple queries and compare results."""
    results = {}
    
    print("\n" + "=" * 80)
    print(f"BATCH DIAGNOSTIC - Running {len(query_keys)} queries")
    print("=" * 80)
    
    for i, query_key in enumerate(query_keys, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}/{len(query_keys)}: {query_key}")
        print("=" * 80)
        
        try:
            report = await run_single_diagnostic(query_key)
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
                "duration_seconds": report.duration_seconds,
                "mckinsey_checklist": report.mckinsey_checklist,
                "recommendations": report.recommendations,
            }
    
    with open(report_path, 'w') as f:
        json.dump(batch_data, f, indent=2, default=str)
    
    print(f"\nBatch report saved to: {report_path}")


async def main():
    """Run the diagnostic with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QNWIS Enhanced Diagnostic - McKinsey-Grade Testing Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query healthcare          Run healthcare domain test
  %(prog)s --query education            Run education domain test
  %(prog)s --batch                      Run all queries in sequence
  %(prog)s --all-complex                Run all complex queries only
  %(prog)s --list                       List available queries
  %(prog)s --random                     Run random query
        """
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Specific query key to run (e.g., healthcare, education, energy)"
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
    
    args = parser.parse_args()
    
    # List queries
    if args.list:
        print_available_queries()
        return
    
    # Random query
    if args.random:
        import random
        query_keys = list(DiagnosticConfig.TEST_QUERIES.keys())
        query_key = random.choice(query_keys)
        print(f"\n🎲 Randomly selected: {query_key}\n")
        report = await run_single_diagnostic(query_key)
        return report
    
    # Batch mode - all queries
    if args.batch:
        query_keys = list(DiagnosticConfig.TEST_QUERIES.keys())
        return await run_batch_diagnostic(query_keys)
    
    # All complex queries
    if args.all_complex:
        query_keys = [
            key for key, query in DiagnosticConfig.TEST_QUERIES.items()
            if query["complexity"] == "complex"
        ]
        return await run_batch_diagnostic(query_keys)
    
    # Specific queries list
    if args.queries:
        return await run_batch_diagnostic(args.queries)
    
    # Single query (default or specified)
    query_key = args.query or DiagnosticConfig.DEFAULT_QUERY_KEY
    report = await run_single_diagnostic(query_key)
    return report


if __name__ == "__main__":
    asyncio.run(main())

