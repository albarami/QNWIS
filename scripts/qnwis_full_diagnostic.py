#!/usr/bin/env python3
"""
QNWIS Full System Diagnostic
============================

Runs a legendary query through the entire system and evaluates:
1. Classification accuracy
2. Data extraction completeness
3. All 12 agents execution
4. Model routing correctness (GPT-5 vs GPT-4o)
5. Debate quality and turn count
6. Scenario generation
7. Final synthesis quality

Usage:
    python scripts/qnwis_full_diagnostic.py
    
Output:
    - Detailed logs for every stage
    - Evaluation report with scores
    - Gap analysis
    - Recommendations
"""

import asyncio
import json
import os
import sys
import time
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

# Ensure DATABASE_URL is set (required by deterministic engine)
# Uses same default as smart_data_router.py, master_data_extraction.py, etc.
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://postgres:1234@localhost:5432/qnwis"

# Create logs directory if needed
Path("logs").mkdir(exist_ok=True)
Path("data/diagnostics").mkdir(parents=True, exist_ok=True)

# Configure detailed logging
log_filename = f'logs/diagnostic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QNWIS_DIAGNOSTIC")

# =============================================================================
# DIAGNOSTIC DATA STRUCTURES
# =============================================================================

@dataclass
class StageResult:
    """Result of evaluating a single stage."""
    stage_name: str
    status: str  # "PASS", "WARN", "FAIL"
    score: float  # 0-100
    execution_time: float
    details: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    """Result of evaluating a single agent."""
    agent_name: str
    executed: bool
    model_used: str
    expected_model: str
    correct_model: bool
    output_length: int
    has_citations: bool
    has_specific_numbers: bool
    execution_time: float
    quality_score: float
    issues: List[str] = field(default_factory=list)


@dataclass
class DataSourceResult:
    """Result of evaluating a data source."""
    source_name: str
    called: bool
    facts_returned: int
    response_time: float
    data_quality: str  # "HIGH", "MEDIUM", "LOW"
    issues: List[str] = field(default_factory=list)


@dataclass 
class DiagnosticReport:
    """Full diagnostic report."""
    timestamp: str
    query: str
    total_execution_time: float
    overall_score: float
    stage_results: List[StageResult] = field(default_factory=list)
    agent_results: List[AgentResult] = field(default_factory=list)
    data_source_results: List[DataSourceResult] = field(default_factory=list)
    debate_analysis: Dict[str, Any] = field(default_factory=dict)
    scenario_analysis: Dict[str, Any] = field(default_factory=dict)
    synthesis_analysis: Dict[str, Any] = field(default_factory=dict)
    model_routing_analysis: Dict[str, Any] = field(default_factory=dict)
    gaps_identified: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# THE TEST QUERY
# =============================================================================

TEST_QUERY = """Qatar must choose its primary economic diversification focus for the next decade. 
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
- Both options are arithmetically feasible with current workforce pipeline

Which option should Qatar prioritize and why? Consider:
1. Competitive dynamics with UAE and Saudi Arabia
2. Qatarization potential in each sector  
3. Revenue diversification from hydrocarbons
4. Risk factors and mitigation strategies
5. 10-year projected outcomes under different scenarios"""

# =============================================================================
# EXPECTED CONFIGURATION - CORRECTED BASED ON CODEBASE ANALYSIS
# =============================================================================

# Actual 12 agents from graph_llm.py
EXPECTED_AGENTS = [
    # LLM Agents (5) - should use GPT-5 for reasoning
    {"name": "MicroEconomist", "type": "llm", "expected_model": "gpt-5"},
    {"name": "MacroEconomist", "type": "llm", "expected_model": "gpt-5"},
    {"name": "Nationalization", "type": "llm", "expected_model": "gpt-5"},
    {"name": "SkillsAgent", "type": "llm", "expected_model": "gpt-5"},
    {"name": "PatternDetective", "type": "llm", "expected_model": "gpt-5"},
    
    # Deterministic Agents (7) - no LLM needed
    {"name": "TimeMachine", "type": "deterministic", "expected_model": "none"},
    {"name": "Predictor", "type": "deterministic", "expected_model": "none"},
    {"name": "Scenario", "type": "deterministic", "expected_model": "none"},
    {"name": "PatternDetectiveAgent", "type": "deterministic", "expected_model": "none"},
    {"name": "PatternMiner", "type": "deterministic", "expected_model": "none"},
    {"name": "NationalStrategy", "type": "deterministic", "expected_model": "none"},
    {"name": "AlertCenter", "type": "deterministic", "expected_model": "none"},
]

# Data sources from prefetch_apis.py
EXPECTED_DATA_SOURCES = [
    "MoL LMIS",
    "GCC-STAT",
    "World Bank",
    "Semantic Scholar",
    "Brave Search",
    "Perplexity",
    "Qatar Open Data",
    "IMF Data Mapper",
    "ILO",
]

# Expected workflow stages from streaming.py and graph_llm.py
EXPECTED_STAGES = [
    "classify",
    "prefetch",
    "rag",
    "select_agents",
    "agents",
    "debate",
    "critique",
    "verify",
    "synthesize",
    "done"
]

# Model routing expectations
MODEL_ROUTING = {
    # GPT-4o tasks (fast, deterministic)
    "classification": "gpt-4o",
    "extraction": "gpt-4o",
    "verification": "gpt-4o",
    "fact_check": "gpt-4o",
    
    # GPT-5 tasks (reasoning, analysis)
    "feasibility_gate": "gpt-5",
    "scenario_generation": "gpt-5",
    "agent_analysis": "gpt-5",
    "debate": "gpt-5",
    "synthesis": "gpt-5",
}

# Debate depth configurations from legendary_debate_orchestrator.py
DEBATE_CONFIGS = {
    "simple": 40,
    "standard": 80,
    "legendary": 150,
    "complex": 150,
}


# =============================================================================
# DIAGNOSTIC CLASS
# =============================================================================

class QNWISDiagnostic:
    """
    Comprehensive diagnostic system for QNWIS.
    """
    
    def __init__(self):
        self.report = DiagnosticReport(
            timestamp=datetime.now().isoformat(),
            query=TEST_QUERY,
            total_execution_time=0,
            overall_score=0
        )
        self.raw_state = {}
        self.events = []
        self.final_state = {}
        
    async def run_full_diagnostic(self) -> DiagnosticReport:
        """
        Run the query through the system and evaluate everything.
        """
        logger.info("=" * 80)
        logger.info("QNWIS FULL SYSTEM DIAGNOSTIC")
        logger.info("=" * 80)
        logger.info(f"Query: {TEST_QUERY[:100]}...")
        logger.info(f"Started: {self.report.timestamp}")
        logger.info(f"Log file: {log_filename}")
        
        start_time = time.time()
        
        try:
            # Step 1: Import the correct workflow entry point
            logger.info("\n" + "=" * 80)
            logger.info("STEP 1: INITIALIZING WORKFLOW")
            logger.info("=" * 80)
            
            from src.qnwis.orchestration.streaming import run_workflow_stream
            logger.info("Successfully imported run_workflow_stream from streaming.py")
            
            # Step 2: Run the workflow with legendary debate depth
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: EXECUTING WORKFLOW WITH LEGENDARY DEBATE DEPTH")
            logger.info("=" * 80)
            logger.info(f"debate_depth='legendary' should trigger {DEBATE_CONFIGS['legendary']} turns")
            
            # Capture all events
            event_count = 0
            debate_turns_captured = 0
            
            async for event in run_workflow_stream(
                question=TEST_QUERY,
                debate_depth="legendary"  # Should trigger 150 turns
            ):
                event_count += 1
                
                # Convert WorkflowEvent to dict for storage
                if hasattr(event, 'to_dict'):
                    event_dict = event.to_dict()
                else:
                    event_dict = {
                        "stage": getattr(event, 'stage', 'unknown'),
                        "status": getattr(event, 'status', 'unknown'),
                        "payload": getattr(event, 'payload', {}),
                        "latency_ms": getattr(event, 'latency_ms', None),
                        "timestamp": getattr(event, 'timestamp', datetime.now().isoformat())
                    }
                
                self.events.append(event_dict)
                
                stage = event_dict.get('stage', '')
                status = event_dict.get('status', '')
                
                # Count debate turns
                if 'debate:turn' in stage or (stage == 'debate' and status == 'streaming'):
                    debate_turns_captured += 1
                    if debate_turns_captured % 10 == 0:
                        logger.info(f"  Debate turn {debate_turns_captured}...")
                
                # Log stage completions
                if status == 'complete':
                    latency = event_dict.get('latency_ms') or 0
                    logger.info(f"EVENT #{event_count}: {stage} - {status} ({latency:.0f}ms)")
                elif status == 'running':
                    logger.info(f"EVENT #{event_count}: {stage} - {status}")
                elif status == 'error':
                    logger.error(f"EVENT #{event_count}: {stage} - ERROR: {event_dict.get('payload', {})}")
                
                # Capture final state from done event
                if stage == 'done' or status == 'complete':
                    payload = event_dict.get('payload', {})
                    if isinstance(payload, dict):
                        self.final_state.update(payload)
            
            logger.info(f"\nTotal events captured: {event_count}")
            logger.info(f"Debate turns captured: {debate_turns_captured}")
            
            # Step 3: Evaluate each component
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3: EVALUATING COMPONENTS")
            logger.info("=" * 80)
            
            await self._evaluate_classification()
            await self._evaluate_data_extraction()
            await self._evaluate_scenario_generation()
            await self._evaluate_agents()
            await self._evaluate_debate(debate_turns_captured)
            await self._evaluate_critique()
            await self._evaluate_verification()
            await self._evaluate_synthesis()
            await self._evaluate_model_routing()
            
            # Step 4: Calculate overall score
            self.report.total_execution_time = time.time() - start_time
            self._calculate_overall_score()
            
            # Step 5: Generate recommendations
            self._generate_recommendations()
            
            # Step 6: Save report
            self._save_report()
            
            # Step 7: Print summary
            self._print_summary()
            
        except Exception as e:
            logger.error(f"DIAGNOSTIC FAILED: {str(e)}", exc_info=True)
            self.report.critical_issues.append(f"Workflow execution failed: {str(e)}")
            self.report.overall_score = 0
            self.report.total_execution_time = time.time() - start_time
            self._save_report()
            self._print_summary()
        
        return self.report

    def _find_event_by_stage(self, stage_name: str) -> Optional[Dict]:
        """Find the last complete event for a given stage."""
        for event in reversed(self.events):
            if event.get('stage') == stage_name and event.get('status') == 'complete':
                return event
        # Fall back to any event for this stage
        for event in reversed(self.events):
            if event.get('stage') == stage_name:
                return event
        return None

    def _find_all_events_by_stage(self, stage_prefix: str) -> List[Dict]:
        """Find all events matching a stage prefix."""
        return [e for e in self.events if e.get('stage', '').startswith(stage_prefix)]

    async def _evaluate_classification(self) -> StageResult:
        """Evaluate the classification stage."""
        logger.info("\n--- Evaluating: Classification ---")
        
        result = StageResult(
            stage_name="classification",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        # Find classification event
        event = self._find_event_by_stage("classify")
        
        if not event:
            result.issues.append("No classification event found")
            result.score = 0
            result.status = "FAIL"
            self.report.stage_results.append(result)
            return result
        
        payload = event.get('payload', {})
        complexity = payload.get('complexity', self.final_state.get('complexity', ''))
        
        logger.info(f"  Complexity: {complexity}")
        
        # For this strategic query, we expect "complex" classification
        if complexity != "complex":
            result.issues.append(f"Expected 'complex', got '{complexity}'")
            result.score -= 20
        
        result.details = {
            "complexity": complexity,
            "event_payload": payload
        }
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_data_extraction(self) -> StageResult:
        """Evaluate data extraction and sources."""
        logger.info("\n--- Evaluating: Data Extraction ---")
        
        result = StageResult(
            stage_name="data_extraction",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        # Find extraction/prefetch event
        event = self._find_event_by_stage("prefetch")
        if not event:
            event = self._find_event_by_stage("extraction")
        
        # Get facts from final state
        extracted_facts = self.final_state.get("extracted_facts", [])
        fact_count = len(extracted_facts) if isinstance(extracted_facts, list) else 0
        
        # Also check event payload
        if event:
            payload = event.get('payload', {})
            if 'facts_count' in payload:
                fact_count = max(fact_count, payload['facts_count'])
            if 'extracted_facts' in payload:
                fact_count = max(fact_count, len(payload['extracted_facts']))
        
        logger.info(f"  Total facts extracted: {fact_count}")
        
        # Evaluate fact count
        if fact_count < 50:
            result.issues.append(f"Very low fact count: {fact_count} (expected 100+)")
            result.score -= 50
        elif fact_count < 100:
            result.issues.append(f"Low fact count: {fact_count} (expected 100+)")
            result.score -= 25
        
        # Check data sources used
        data_sources = self.final_state.get("data_sources", [])
        if event:
            payload = event.get('payload', {})
            if 'sources' in payload:
                data_sources = payload['sources']
            elif 'data_sources' in payload:
                data_sources = payload['data_sources']
        
        logger.info(f"  Sources used: {data_sources}")
        
        sources_found = 0
        for expected_source in EXPECTED_DATA_SOURCES:
            found = any(expected_source.lower() in str(s).lower() for s in data_sources)
            source_result = DataSourceResult(
                source_name=expected_source,
                called=found,
                facts_returned=0,
                response_time=0,
                data_quality="UNKNOWN"
            )
            
            if found:
                sources_found += 1
            else:
                source_result.issues.append(f"Source not called: {expected_source}")
            
            self.report.data_source_results.append(source_result)
        
        if sources_found < 3:
            result.issues.append(f"Only {sources_found} data sources used (expected 5+)")
            result.score -= 20
        
        result.details = {
            "fact_count": fact_count,
            "sources_used": data_sources,
            "sources_found": sources_found
        }
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_scenario_generation(self) -> StageResult:
        """Evaluate scenario generation quality."""
        logger.info("\n--- Evaluating: Scenario Generation ---")
        
        result = StageResult(
            stage_name="scenario_generation",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        scenarios = self.final_state.get("scenarios", [])
        scenario_results = self.final_state.get("scenario_results", {})
        
        scenario_count = len(scenarios) if isinstance(scenarios, list) else 0
        
        logger.info(f"  Scenarios generated: {scenario_count}")
        
        # Check scenario count
        if scenario_count == 0:
            result.issues.append("No scenarios generated")
            result.score -= 40
        elif scenario_count < 3:
            result.issues.append(f"Too few scenarios: {scenario_count} (expected 5-6)")
            result.score -= 20
        
        # Analyze scenario quality
        scenario_analysis = {
            "count": scenario_count,
            "has_base_case": False,
            "has_best_case": False,
            "has_worst_case": False,
            "has_specific_numbers": 0,
            "scenarios": []
        }
        
        for scenario in scenarios:
            scenario_text = str(scenario).lower()
            
            if "base" in scenario_text:
                scenario_analysis["has_base_case"] = True
            if "best" in scenario_text or "optimistic" in scenario_text:
                scenario_analysis["has_best_case"] = True
            if "worst" in scenario_text or "collapse" in scenario_text or "pessimistic" in scenario_text:
                scenario_analysis["has_worst_case"] = True
            
            # Check for specific numbers
            numbers = re.findall(r'\d+\.?\d*%|\$?\d+(?:,\d+)*(?:\.\d+)?[BMK]?', str(scenario))
            if len(numbers) >= 3:
                scenario_analysis["has_specific_numbers"] += 1
        
        result.details = scenario_analysis
        self.report.scenario_analysis = scenario_analysis
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_agents(self) -> StageResult:
        """Evaluate all 12 agents."""
        logger.info("\n--- Evaluating: Agent Execution ---")
        
        result = StageResult(
            stage_name="agents",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        # Find all agent events
        agent_events = self._find_all_events_by_stage("agent:")
        
        # Get agent reports from final state
        agent_reports = self.final_state.get("agent_reports", [])
        
        agents_executed = []
        agents_missing = []
        
        for agent_config in EXPECTED_AGENTS:
            agent_name = agent_config["name"]
            agent_type = agent_config["type"]
            expected_model = agent_config["expected_model"]
            
            # Check for agent in events
            agent_event = None
            for event in agent_events:
                if agent_name.lower() in event.get('stage', '').lower():
                    agent_event = event
                    break
            
            # Check in agent reports
            agent_output = None
            for report in agent_reports:
                if hasattr(report, 'agent') and report.agent == agent_name:
                    agent_output = report
                    break
                elif isinstance(report, dict) and report.get('agent') == agent_name:
                    agent_output = report
                    break
            
            # Also check state keys
            for key in [f"{agent_name.lower()}_analysis", f"{agent_name}_analysis", agent_name.lower()]:
                if key in self.final_state:
                    agent_output = self.final_state[key]
                    break
            
            executed = agent_output is not None or agent_event is not None
            
            agent_result = AgentResult(
                agent_name=agent_name,
                executed=executed,
                model_used="unknown",
                expected_model=expected_model,
                correct_model=True,
                output_length=len(str(agent_output)) if agent_output else 0,
                has_citations=False,
                has_specific_numbers=False,
                execution_time=0,
                quality_score=0
            )
            
            if executed:
                agents_executed.append(agent_name)
                
                output_str = str(agent_output) if agent_output else ""
                
                # Check for citations
                agent_result.has_citations = "per extraction" in output_str.lower() or "[" in output_str
                
                # Check for specific numbers
                numbers = re.findall(r'\d+\.?\d*%|\d+(?:,\d+)*(?:\.\d+)?', output_str)
                agent_result.has_specific_numbers = len(numbers) >= 5
                
                # Calculate quality score
                quality = 50
                if agent_result.has_citations:
                    quality += 25
                if agent_result.has_specific_numbers:
                    quality += 25
                if agent_result.output_length > 500:
                    quality += 10
                agent_result.quality_score = min(100, quality)
                
                logger.info(f"  [OK] {agent_name}: {agent_result.output_length} chars, quality={agent_result.quality_score}")
            else:
                agents_missing.append(agent_name)
                agent_result.issues.append("Agent did not execute or produced no output")
                result.score -= 8
                logger.info(f"  [MISSING] {agent_name}")
            
            self.report.agent_results.append(agent_result)
        
        result.details = {
            "agents_executed": agents_executed,
            "agents_missing": agents_missing,
            "execution_rate": f"{len(agents_executed)}/{len(EXPECTED_AGENTS)}"
        }
        
        if len(agents_missing) > 0:
            result.issues.append(f"Missing agents: {', '.join(agents_missing)}")
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_debate(self, turns_captured: int) -> StageResult:
        """Evaluate the legendary debate."""
        logger.info("\n--- Evaluating: Legendary Debate ---")
        
        result = StageResult(
            stage_name="debate",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        # Get debate results from final state
        debate_results = self.final_state.get("debate_results", {})
        if not isinstance(debate_results, dict):
            debate_results = {}
        
        # Get turn count
        turn_count = debate_results.get("total_turns", 0)
        if turn_count == 0:
            # Try conversation history
            conv_history = debate_results.get("conversation_history", [])
            if isinstance(conv_history, list):
                turn_count = len(conv_history)
        if turn_count == 0 and turns_captured > 0:
            turn_count = turns_captured
        
        logger.info(f"  Debate turns: {turn_count}")
        logger.info(f"  Expected for legendary: {DEBATE_CONFIGS['legendary']}")
        
        debate_analysis = {
            "turn_count": turn_count,
            "expected_min": 100,
            "expected_max": 150,
            "has_challenges": False,
            "has_consensus": False,
            "has_edge_cases": False,
            "has_risk_analysis": False,
            "phases_found": [],
            "phases_completed": debate_results.get("phases_completed", 0)
        }
        
        # Get debate text for phase analysis
        debate_text = ""
        final_report = debate_results.get("final_report", "")
        if final_report:
            debate_text = str(final_report).lower()
        
        # Also check conversation history
        conv_history = debate_results.get("conversation_history", [])
        if isinstance(conv_history, list):
            for turn in conv_history:
                if isinstance(turn, dict):
                    debate_text += " " + str(turn.get("message", "")).lower()
        
        # Check phases
        if "opening" in debate_text:
            debate_analysis["phases_found"].append("opening")
        if "challenge" in debate_text:
            debate_analysis["has_challenges"] = True
            debate_analysis["phases_found"].append("challenge")
        if "defense" in debate_text or "response" in debate_text:
            debate_analysis["phases_found"].append("defense")
        if "edge case" in debate_text:
            debate_analysis["has_edge_cases"] = True
            debate_analysis["phases_found"].append("edge_cases")
        if "risk" in debate_text:
            debate_analysis["has_risk_analysis"] = True
            debate_analysis["phases_found"].append("risk_analysis")
        if "consensus" in debate_text:
            debate_analysis["has_consensus"] = True
            debate_analysis["phases_found"].append("consensus")
        
        # CRITICAL: Score based on turn count for legendary depth
        if turn_count < 25:
            result.issues.append(f"CRITICAL: Very low turn count: {turn_count} (expected 100-150 for Legendary)")
            result.score -= 60
        elif turn_count < 50:
            result.issues.append(f"Low turn count: {turn_count} (expected 100-150 for Legendary)")
            result.score -= 40
        elif turn_count < 100:
            result.issues.append(f"Below target: {turn_count} (expected 100-150 for Legendary)")
            result.score -= 20
        else:
            logger.info(f"  Turn count meets legendary threshold!")
        
        # Check if debate_depth parameter is being passed
        if turn_count < 50:
            result.issues.append("DIAGNOSTIC: debate_depth='legendary' may not be reaching the orchestrator")
            result.recommendations.append("Check if debate_depth parameter is passed through run_workflow_stream to LegendaryDebateOrchestrator")
        
        result.details = debate_analysis
        self.report.debate_analysis = debate_analysis
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_critique(self) -> StageResult:
        """Evaluate devil's advocate critique."""
        logger.info("\n--- Evaluating: Devil's Advocate Critique ---")
        
        result = StageResult(
            stage_name="critique",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        critique_results = self.final_state.get("critique_results", {})
        critique_report = self.final_state.get("critique_report", "")
        
        critique_text = str(critique_results) + str(critique_report)
        critique_length = len(critique_text)
        
        red_flags = []
        if isinstance(critique_results, dict):
            red_flags = critique_results.get("red_flags", [])
        
        red_flag_count = len(red_flags) if isinstance(red_flags, list) else 0
        
        logger.info(f"  Critique length: {critique_length} chars")
        logger.info(f"  Red flags: {red_flag_count}")
        
        critique_analysis = {
            "critique_length": critique_length,
            "red_flag_count": red_flag_count,
            "has_severity_ratings": "severity" in critique_text.lower() or "high" in critique_text.lower(),
            "has_robustness_scores": "robustness" in critique_text.lower(),
            "challenges_main_recommendation": "however" in critique_text.lower() or "risk" in critique_text.lower()
        }
        
        if critique_length < 200:
            result.issues.append(f"Critique too short: {critique_length} chars")
            result.score -= 30
        
        if red_flag_count < 2:
            result.issues.append(f"Too few red flags: {red_flag_count} (expected 3+)")
            result.score -= 20
        
        result.details = critique_analysis
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_verification(self) -> StageResult:
        """Evaluate fact verification."""
        logger.info("\n--- Evaluating: Verification ---")
        
        result = StageResult(
            stage_name="verification",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        fact_check_results = self.final_state.get("fact_check_results", {})
        fabrication_detected = self.final_state.get("fabrication_detected", False)
        
        logger.info(f"  Fabrication detected: {fabrication_detected}")
        
        result.details = {
            "fact_check_ran": bool(fact_check_results),
            "fabrication_detected": fabrication_detected
        }
        
        if fabrication_detected:
            result.issues.append("Fabrication detected in output")
            result.score -= 30
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_synthesis(self) -> StageResult:
        """Evaluate final synthesis quality."""
        logger.info("\n--- Evaluating: Final Synthesis ---")
        
        result = StageResult(
            stage_name="synthesis",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        synthesis = self.final_state.get("final_synthesis", "")
        if not synthesis:
            synthesis = self.final_state.get("debate_synthesis", "")
        if not synthesis:
            # Check debate results for final report
            debate_results = self.final_state.get("debate_results", {})
            if isinstance(debate_results, dict):
                synthesis = debate_results.get("final_report", "")
        
        synthesis_length = len(str(synthesis))
        
        logger.info(f"  Synthesis length: {synthesis_length} chars")
        
        synthesis_analysis = {
            "length": synthesis_length,
            "has_executive_summary": False,
            "has_recommendation": False,
            "has_confidence": False,
            "has_decisive_factors": False,
            "has_expert_disagreements": False,
            "has_red_flags": False,
            "has_scenario_table": False,
            "has_actions": False,
            "has_minister_card": False,
            "specific_number_count": 0,
            "quality_rating": "UNKNOWN"
        }
        
        synthesis_text = str(synthesis).lower()
        synthesis_raw = str(synthesis)
        
        # Check for required sections
        if "executive summary" in synthesis_text or "summary" in synthesis_text:
            synthesis_analysis["has_executive_summary"] = True
        else:
            result.issues.append("Missing Executive Summary")
            result.score -= 10
        
        if "recommend" in synthesis_text:
            synthesis_analysis["has_recommendation"] = True
        else:
            result.issues.append("Missing recommendation")
            result.score -= 15
        
        if "confidence" in synthesis_text or "%" in synthesis_text:
            synthesis_analysis["has_confidence"] = True
        
        if "disagree" in synthesis_text or "disagreement" in synthesis_text:
            synthesis_analysis["has_expert_disagreements"] = True
        
        if "red flag" in synthesis_text or "risk" in synthesis_text:
            synthesis_analysis["has_red_flags"] = True
        
        if "action" in synthesis_text:
            synthesis_analysis["has_actions"] = True
        
        # Count specific numbers
        numbers = re.findall(r'\d+\.?\d*%|\$?\d+(?:,\d+)*(?:\.\d+)?[BMK]?', synthesis_raw)
        synthesis_analysis["specific_number_count"] = len(numbers)
        
        if len(numbers) < 5:
            result.issues.append(f"Too few specific numbers: {len(numbers)} (expected 10+)")
            result.score -= 15
        
        # Overall quality rating
        if synthesis_length > 3000 and len(numbers) > 15:
            synthesis_analysis["quality_rating"] = "EXCELLENT"
        elif synthesis_length > 1500 and len(numbers) > 8:
            synthesis_analysis["quality_rating"] = "GOOD"
        elif synthesis_length > 500:
            synthesis_analysis["quality_rating"] = "FAIR"
        else:
            synthesis_analysis["quality_rating"] = "POOR"
            result.score -= 25
        
        logger.info(f"  Quality rating: {synthesis_analysis['quality_rating']}")
        logger.info(f"  Numbers found: {len(numbers)}")
        
        result.details = synthesis_analysis
        self.report.synthesis_analysis = synthesis_analysis
        
        result.status = "PASS" if result.score >= 80 else ("WARN" if result.score >= 50 else "FAIL")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    async def _evaluate_model_routing(self) -> StageResult:
        """Evaluate if correct models were used for each task."""
        logger.info("\n--- Evaluating: Model Routing ---")
        
        result = StageResult(
            stage_name="model_routing",
            status="PASS",
            score=100,
            execution_time=0,
            details={}
        )
        
        # Model routing is hard to verify without instrumentation
        # For now, we'll note it as "unknown"
        routing_analysis = {
            "correct_routes": [],
            "incorrect_routes": [],
            "unknown_routes": list(MODEL_ROUTING.keys()),
            "note": "Model routing verification requires additional instrumentation"
        }
        
        result.details = routing_analysis
        self.report.model_routing_analysis = routing_analysis
        
        # Don't penalize for unknown - this needs instrumentation
        result.status = "WARN"
        result.score = 70  # Neutral score
        result.issues.append("Model routing not fully instrumented for verification")
        
        self.report.stage_results.append(result)
        logger.info(f"  Score: {result.score}/100 - {result.status}")
        return result

    def _calculate_overall_score(self):
        """Calculate weighted overall score."""
        weights = {
            "classification": 0.05,
            "data_extraction": 0.15,
            "scenario_generation": 0.10,
            "agents": 0.20,
            "debate": 0.20,
            "critique": 0.10,
            "verification": 0.05,
            "synthesis": 0.10,
            "model_routing": 0.05
        }
        
        total_score = 0
        for stage_result in self.report.stage_results:
            weight = weights.get(stage_result.stage_name, 0.05)
            total_score += stage_result.score * weight
        
        self.report.overall_score = round(total_score, 1)

    def _generate_recommendations(self):
        """Generate recommendations based on findings."""
        
        # Collect all issues
        for stage in self.report.stage_results:
            if stage.status == "FAIL":
                self.report.critical_issues.append(f"{stage.stage_name}: {', '.join(stage.issues)}")
            self.report.gaps_identified.extend(stage.issues)
        
        # Generate recommendations
        debate_result = next((r for r in self.report.stage_results if r.stage_name == "debate"), None)
        if debate_result and debate_result.score < 80:
            self.report.recommendations.append(
                "CRITICAL: Debate not reaching legendary depth. "
                "Check that debate_depth='legendary' is passed through run_workflow_stream() "
                "to the LegendaryDebateOrchestrator.conduct_legendary_debate() method."
            )
            self.report.recommendations.append(
                "INVESTIGATION: Add logging in streaming.py line 475 to verify debate_depth is in initial_state, "
                "and in legendary_debate_orchestrator.py line 394 to verify it's received."
            )
        
        synthesis_result = next((r for r in self.report.stage_results if r.stage_name == "synthesis"), None)
        if synthesis_result and synthesis_result.score < 80:
            self.report.recommendations.append(
                "CRITICAL: Synthesis quality below target. "
                "Ensure debate final_report is being preserved and used in final synthesis."
            )
        
        missing_agents = [a.agent_name for a in self.report.agent_results if not a.executed]
        if missing_agents:
            self.report.recommendations.append(
                f"AGENTS: {len(missing_agents)} agents did not execute: {', '.join(missing_agents)}. "
                "Verify agent initialization and selection logic in graph_llm.py."
            )

    def _save_report(self):
        """Save the diagnostic report."""
        output_dir = Path("data/diagnostics")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        report_file = output_dir / f"diagnostic_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.report), f, indent=2, default=str)
        
        # Save raw state (truncated for storage)
        state_file = output_dir / f"raw_state_{timestamp}.json"
        try:
            truncated_state = {}
            for key, value in self.final_state.items():
                if isinstance(value, str) and len(value) > 10000:
                    truncated_state[key] = value[:10000] + "... [TRUNCATED]"
                elif callable(value):
                    truncated_state[key] = "[CALLABLE - SKIPPED]"
                else:
                    truncated_state[key] = value
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(truncated_state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save raw state: {e}")
        
        # Save events log
        events_file = output_dir / f"events_{timestamp}.json"
        try:
            with open(events_file, "w", encoding="utf-8") as f:
                json.dump(self.events, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save events: {e}")
        
        logger.info(f"\nReports saved to: {output_dir}")
        logger.info(f"  - {report_file.name}")
        logger.info(f"  - {state_file.name}")
        logger.info(f"  - {events_file.name}")

    def _print_summary(self):
        """Print summary to console."""
        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        print(f"\nOVERALL SCORE: {self.report.overall_score}/100")
        print(f"EXECUTION TIME: {self.report.total_execution_time:.1f}s")
        
        print("\n--- Stage Scores ---")
        for stage in self.report.stage_results:
            status_icon = "[OK]" if stage.status == "PASS" else ("[WARN]" if stage.status == "WARN" else "[FAIL]")
            print(f"  {status_icon} {stage.stage_name}: {stage.score}/100 [{stage.status}]")
            if stage.issues:
                for issue in stage.issues[:2]:
                    print(f"      - {issue}")
        
        print("\n--- Agent Status ---")
        executed = sum(1 for a in self.report.agent_results if a.executed)
        print(f"  Executed: {executed}/{len(self.report.agent_results)}")
        for agent in self.report.agent_results:
            status = "[OK]" if agent.executed else "[MISSING]"
            print(f"    {status} {agent.agent_name}: {agent.output_length} chars")
        
        print("\n--- Debate Analysis ---")
        print(f"  Turns: {self.report.debate_analysis.get('turn_count', 0)}")
        print(f"  Expected: 100-150 for legendary")
        print(f"  Phases: {self.report.debate_analysis.get('phases_found', [])}")
        
        print("\n--- Synthesis Quality ---")
        print(f"  Rating: {self.report.synthesis_analysis.get('quality_rating', 'UNKNOWN')}")
        print(f"  Length: {self.report.synthesis_analysis.get('length', 0)} chars")
        print(f"  Numbers: {self.report.synthesis_analysis.get('specific_number_count', 0)}")
        
        if self.report.critical_issues:
            print("\n--- CRITICAL ISSUES ---")
            for issue in self.report.critical_issues:
                print(f"  [X] {issue}")
        
        if self.report.recommendations:
            print("\n--- RECOMMENDATIONS ---")
            for rec in self.report.recommendations:
                print(f"  -> {rec}")
        
        print("\n" + "=" * 80)
        
        # Final verdict
        if self.report.overall_score >= 90:
            print("LEGENDARY: System performing at peak capacity!")
        elif self.report.overall_score >= 75:
            print("GOOD: System working well with minor improvements needed")
        elif self.report.overall_score >= 50:
            print("FAIR: Significant gaps identified, see recommendations")
        else:
            print("POOR: Critical issues must be addressed")
        
        print("=" * 80)


# =============================================================================
# ENTRY POINT
# =============================================================================

async def main():
    """Run the full diagnostic."""
    diagnostic = QNWISDiagnostic()
    report = await diagnostic.run_full_diagnostic()
    return report


if __name__ == "__main__":
    # Run diagnostic
    report = asyncio.run(main())
    
    # Exit with appropriate code
    if report.overall_score >= 75:
        sys.exit(0)
    else:
        sys.exit(1)

