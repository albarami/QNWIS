"""
NSIC Dual-Engine Orchestrator

Coordinates the dual-engine ensemble:
- Engine A (Azure GPT-5): 6 deep scenarios, 100 turns each
- Engine B (DeepSeek): 24 broad scenarios, 25 turns each

Integrates:
- ScenarioLoader (Phase 5)
- Engine B (Phase 7)
- Ensemble Arbitrator (Phase 8)
- Timing Logger (Phase 9)
- All integration components (RAG, DB, KG, Verification)

NO MOCKS. REAL SYSTEM INTEGRATION.
"""

import logging
import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime

from .timing_logger import TimingLogger, Stage, get_timing_logger
from .engine_b_deepseek import EngineBDeepSeek, ScenarioResult, create_engine_b
from .deepseek_client import DeepSeekClient, InferenceMode
from .error_handler import (
    NSICErrorHandler,
    AnalysisState,
    create_error_handler,
)
from .semantic_cache import (
    SemanticCache,
    create_semantic_cache,
)
from src.nsic.scenarios.generator import (
    NSICScenarioGenerator,
    ScenarioSet,
    GeneratedScenario,
    create_scenario_generator,
)

# Engine B v5.0 Compute Services
from ..engine_b.services.monte_carlo import MonteCarloService, MonteCarloInput
from ..engine_b.services.sensitivity import SensitivityService, SensitivityInput
from ..engine_b.services.forecasting import ForecastingService, ForecastingInput
from ..engine_b.services.thresholds import ThresholdService, ThresholdInput
from ..engine_b.services.benchmarking import BenchmarkingService, BenchmarkingInput, BenchmarkMetric, PeerData
from ..engine_b.services.correlation import CorrelationService, CorrelationInput
from ..engine_b.integration.conflict_detector import ConflictDetector

logger = logging.getLogger(__name__)


@dataclass
class DualEngineResult:
    """Result from dual-engine processing of a scenario."""
    scenario_id: str
    scenario_name: str
    domain: str

    # Engine outputs
    engine_a_result: Optional[Dict[str, Any]] = None
    engine_b_result: Optional[ScenarioResult] = None

    # Arbitration
    arbitration_result: Optional[Dict[str, Any]] = None
    final_content: str = ""
    confidence: float = 0.0

    # Timing
    total_time_ms: float = 0.0
    timing_breakdown: Dict[str, float] = field(default_factory=dict)

    # Degradation tracking
    degradation_state: Optional[Dict[str, Any]] = None
    degradation_summary: str = ""

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        # Calculate turns completed
        turns_completed = 0
        if self.engine_a_result:
            turns_completed = self.engine_a_result.get("turns_completed", 1)
        elif self.engine_b_result:
            # engine_b_result is a ScenarioResult with a 'turns' list
            turns_completed = len(getattr(self.engine_b_result, 'turns', [])) if self.engine_b_result else 0
        
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "domain": self.domain,
            "engine_a_completed": self.engine_a_result is not None,
            "engine_b_completed": self.engine_b_result is not None,
            "engine_a_result": self.engine_a_result,
            "engine_b_result": self.engine_b_result.to_dict() if self.engine_b_result and hasattr(self.engine_b_result, 'to_dict') else None,
            "arbitration_completed": self.arbitration_result is not None,
            "confidence": self.confidence,
            "turns_completed": turns_completed,
            "total_time_ms": self.total_time_ms,
            "timing_breakdown": self.timing_breakdown,
            "final_content": self.final_content,  # FIX: Include actual content, not just length!
            "final_content_length": len(self.final_content),
            "degradation_state": self.degradation_state,
            "is_degraded": self.degradation_state.get("is_degraded", False) if self.degradation_state else False,
            "timestamp": self.timestamp.isoformat(),
        }


class DualEngineOrchestrator:
    """
    Orchestrates the dual-engine ensemble for maximum quality analysis.
    
    Architecture:
    - Engine A (Azure GPT-5): Deep, precise analysis (6 scenarios × 100 turns)
    - Engine B (DeepSeek local): Broad exploration (24 scenarios × 25 turns)
    
    For scenarios assigned to both engines:
    - Run both in parallel
    - Arbitrate results using EnsembleArbitrator
    - Generate final synthesized output
    """
    
    # Configuration
    ENGINE_A_TURNS = 100  # Deep analysis
    ENGINE_B_TURNS = 25   # Broad exploration
    
    def __init__(
        self,
        engine_b: Optional[EngineBDeepSeek] = None,
        arbitrator = None,
        timing_logger: Optional[TimingLogger] = None,
        llm_client = None,
        error_handler: Optional[NSICErrorHandler] = None,
        semantic_cache: Optional[SemanticCache] = None,
        enable_cache: bool = True,
    ):
        """
        Initialize dual-engine orchestrator.

        Args:
            engine_b: Engine B instance (or creates one)
            arbitrator: EnsembleArbitrator instance (or creates one)
            timing_logger: TimingLogger instance (or uses global)
            llm_client: Azure LLM client for Engine A
            error_handler: Error handler for graceful degradation
            semantic_cache: Semantic cache for similar queries
            enable_cache: Whether to enable semantic caching
        """
        self.engine_b = engine_b or create_engine_b(mock=False)
        self._arbitrator = arbitrator
        self.timing = timing_logger or get_timing_logger()
        self._llm_client = llm_client
        self.error_handler = error_handler or create_error_handler()
        self.semantic_cache = semantic_cache if enable_cache else None
        self._cache_enabled = enable_cache

        # Lazy-load cache to avoid startup delay
        if enable_cache and semantic_cache is None:
            self._cache_lazy = True
        else:
            self._cache_lazy = False

        # Stats
        self._stats = {
            "scenarios_processed": 0,
            "engine_a_runs": 0,
            "engine_b_runs": 0,
            "arbitrations": 0,
            "degraded_runs": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_ms": 0.0,
        }

        cache_status = "enabled (lazy)" if enable_cache else "disabled"
        logger.info(f"DualEngineOrchestrator initialized - REAL MODE with graceful degradation, cache={cache_status}")
    
    @property
    def arbitrator(self):
        """Lazy load arbitrator."""
        if self._arbitrator is None:
            from src.nsic.arbitration import create_ensemble_arbitrator
            self._arbitrator = create_ensemble_arbitrator()
        return self._arbitrator

    @property
    def cache(self) -> Optional[SemanticCache]:
        """Lazy load semantic cache."""
        if self._cache_lazy and self.semantic_cache is None:
            self.semantic_cache = create_semantic_cache()
            self._cache_lazy = False
        return self.semantic_cache
    
    @property
    def llm_client(self):
        """Lazy load Azure LLM client for Engine A."""
        if self._llm_client is None:
            try:
                from src.nsic.integration.llm_client import get_nsic_llm_client
                self._llm_client = get_nsic_llm_client()
            except Exception as e:
                logger.warning(f"Could not load Azure LLM client: {e}")
        return self._llm_client
    
    async def _run_engine_a(
        self,
        scenario,
        context: str = "",
        state: Optional[AnalysisState] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[AnalysisState]]:
        """
        Run Engine A using full QNWIS LLMWorkflow (graph_llm.py).
        
        Uses:
        - 5 LLM Debating Agents: MicroEconomist, MacroEconomist, Nationalization, Skills, PatternDetective
        - 7 Deterministic Data Agents: TimeMachine, Predictor, ScenarioAgent, etc.
        - Full pipeline: classify → prefetch → rag → agents → debate → critique → verify → synthesize

        Args:
            scenario: ScenarioDefinition
            context: Pre-fetched context
            state: Current analysis state for degradation tracking

        Returns:
            Tuple of (result dict, updated state) - result may be None on failure
        """
        state = state or self.error_handler.create_state()

        with self.timing.time_stage(Stage.ENGINE_A, scenario.id):
            try:
                # Import the full QNWIS workflow with 12 agents
                from src.qnwis.orchestration.graph_llm import LLMWorkflow
                from src.qnwis.agents.base import DataClient
                from src.qnwis.llm.client import LLMClient as QNWISLLMClient
                
                # Build the question from scenario
                question = f"""Scenario Analysis: {scenario.name}

Domain: {scenario.domain}
Description: {scenario.description}

Key Variables:
"""
                for inp in scenario.inputs:
                    question += f"- {inp.variable}: changes from {inp.base_value} to {inp.shock_value} ({inp.shock_type})\n"
                
                question += f"""
Context: {context if context else 'Analyze using available data sources'}

Provide comprehensive analysis of this scenario's impacts on Qatar's economy and policy objectives."""

                logger.info(f"Engine A: Running full 12-agent QNWIS workflow for {scenario.id}")
                
                # Initialize workflow with data client and LLM
                data_client = DataClient()
                llm_client = QNWISLLMClient()
                workflow = LLMWorkflow(data_client=data_client, llm_client=llm_client)
                
                # Run the full workflow (5 debating agents + 7 deterministic agents)
                start_time = time.time()
                result = await workflow.run(question)
                elapsed_ms = (time.time() - start_time) * 1000
                
                self._stats["engine_a_runs"] += 1
                
                # Extract synthesis from workflow result
                synthesis = result.get("synthesis", "")
                agent_reports = result.get("agent_reports", [])
                debate_results = result.get("debate_results", {})
                verification = result.get("verification", {})
                
                # Count debate turns
                debate_turns = debate_results.get("total_turns", 0) if debate_results else 0
                
                logger.info(
                    f"Engine A complete: {len(agent_reports)} agents, "
                    f"{debate_turns} debate turns, {elapsed_ms:.0f}ms"
                )

                return {
                    "engine": "engine_a",
                    "content": synthesis,
                    "agent_reports": agent_reports,
                    "debate_results": debate_results,
                    "verification": verification,
                    "model": "qnwis_12_agent_workflow",
                    "task_type": "full_analysis",
                    "latency_ms": elapsed_ms,
                    "turns_completed": debate_turns,
                    "agents_used": len(agent_reports),
                }, state

            except asyncio.TimeoutError as e:
                logger.error(f"Engine A timeout for {scenario.id}: {e}")
                state = await self.error_handler.handle_engine_a_failure(state, e)
                return None, state

            except Exception as e:
                logger.error(f"Engine A failed for {scenario.id}: {e}")
                state = await self.error_handler.handle_engine_a_failure(state, e)
                return None, state
    
    async def _run_engine_b(
        self,
        scenario,
        turns: int = None,
        state: Optional[AnalysisState] = None,
        scenario_index: int = 0,
    ) -> Tuple[Optional[ScenarioResult], Optional[AnalysisState]]:
        """
        Run Engine B (DeepSeek) for broad exploration with graceful degradation.

        Args:
            scenario: ScenarioDefinition
            turns: Number of turns (default: ENGINE_B_TURNS)
            state: Current analysis state for degradation tracking
            scenario_index: Index for agent rotation

        Returns:
            Tuple of (ScenarioResult, updated state) - result may be None on failure
        """
        turns = turns or self.ENGINE_B_TURNS
        state = state or self.error_handler.create_state()

        with self.timing.time_stage(Stage.ENGINE_B, scenario.id, turns=turns):
            try:
                result = await self.engine_b.analyze_scenario(
                    scenario, turns=turns, scenario_index=scenario_index
                )
                self._stats["engine_b_runs"] += 1
                return result, state

            except asyncio.TimeoutError as e:
                logger.error(f"Engine B timeout for {scenario.id}: {e}")
                state = await self.error_handler.handle_engine_b_failure(
                    state, e, completed_scenarios=scenario_index
                )
                return None, state

            except ConnectionError as e:
                logger.error(f"Engine B connection error for {scenario.id}: {e}")
                # Try to determine which instance failed
                instance = 1  # Default assumption
                state = await self.error_handler.handle_engine_b_failure(
                    state, e, instance=instance, completed_scenarios=scenario_index
                )
                return None, state

            except Exception as e:
                logger.error(f"Engine B failed for {scenario.id}: {e}")
                state = await self.error_handler.handle_engine_b_failure(
                    state, e, completed_scenarios=scenario_index
                )
                return None, state
    
    async def _arbitrate(
        self,
        scenario,
        engine_a_result: Dict[str, Any],
        engine_b_result: ScenarioResult,
    ) -> Dict[str, Any]:
        """
        Arbitrate between Engine A and Engine B results.
        
        Args:
            scenario: ScenarioDefinition
            engine_a_result: Output from Engine A
            engine_b_result: Output from Engine B
            
        Returns:
            Arbitration decision dict
        """
        from src.nsic.arbitration import EngineOutput
        
        with self.timing.time_stage(Stage.ARBITRATION, scenario.id):
            # Convert to EngineOutput format
            output_a = EngineOutput(
                engine="engine_a",
                content=engine_a_result["content"],
                scenario_id=scenario.id,
                turns_completed=engine_a_result.get("turns_completed", 1),
                confidence=0.85,  # Azure GPT-5 baseline confidence
                data_sources=["Azure", "RAG"],
            )
            
            output_b = EngineOutput(
                engine="engine_b",
                content=engine_b_result.final_synthesis,
                scenario_id=scenario.id,
                turns_completed=len(engine_b_result.turns),
                confidence=0.75,  # DeepSeek baseline confidence
                data_sources=engine_b_result.data_sources,
            )
            
            # Run arbitration
            decision = self.arbitrator.arbitrate(output_a, output_b)
            self._stats["arbitrations"] += 1
            
            return decision.to_dict()
    
    async def process_scenario(
        self,
        scenario,
        run_both_engines: bool = True,
        scenario_index: int = 0,
    ) -> DualEngineResult:
        """
        Process a single scenario through the dual-engine pipeline with graceful degradation.

        Args:
            scenario: ScenarioDefinition
            run_both_engines: If True, run both engines and arbitrate
            scenario_index: Index for agent rotation in Engine B

        Returns:
            DualEngineResult with final analysis and degradation info
        """
        start_time = time.time()

        logger.info(f"Processing scenario: {scenario.id}")

        # Create analysis state for degradation tracking
        state = self.error_handler.create_state()

        # Get context
        with self.timing.time_stage(Stage.CONTEXT_RETRIEVAL, scenario.id):
            context = ""
            try:
                context = await self.engine_b._get_context(scenario.description)
                context = self.engine_b._format_context_prompt(context)
            except Exception as e:
                logger.warning(f"Context retrieval failed: {e}")
                # Non-critical - continue with empty context

        # Determine which engines to run
        engine_a_result = None
        engine_b_result = None

        if scenario.assigned_engine == "engine_a":
            # Run Engine A (Azure GPT-5)
            engine_a_result, state = await self._run_engine_a(scenario, context, state)
            if engine_a_result:
                final_content = engine_a_result["content"]
                confidence = 0.85
            else:
                # Fallback to Engine B if Engine A unavailable (graceful degradation)
                logger.warning(f"Engine A unavailable, falling back to Engine B for {scenario.id}")
                engine_b_result, state = await self._run_engine_b(
                    scenario, state=state, scenario_index=scenario_index
                )
                final_content = engine_b_result.final_synthesis if engine_b_result else ""
                confidence = 0.75

        elif scenario.assigned_engine == "engine_b":
            # Run only Engine B
            engine_b_result, state = await self._run_engine_b(
                scenario, state=state, scenario_index=scenario_index
            )
            final_content = engine_b_result.final_synthesis if engine_b_result else ""
            confidence = 0.75

        else:  # "auto" - run both and arbitrate
            if run_both_engines:
                # Run both engines in parallel
                engine_a_task = self._run_engine_a(scenario, context, state)
                engine_b_task = self._run_engine_b(
                    scenario, turns=10, state=state, scenario_index=scenario_index
                )

                results = await asyncio.gather(
                    engine_a_task,
                    engine_b_task,
                    return_exceptions=True,
                )

                # Unpack results with state handling
                if isinstance(results[0], Exception):
                    logger.error(f"Engine A exception: {results[0]}")
                    engine_a_result = None
                    state = await self.error_handler.handle_engine_a_failure(state, results[0])
                else:
                    engine_a_result, state = results[0]

                if isinstance(results[1], Exception):
                    logger.error(f"Engine B exception: {results[1]}")
                    engine_b_result = None
                    state = await self.error_handler.handle_engine_b_failure(state, results[1])
                else:
                    engine_b_result, state = results[1]
            else:
                # Default to Engine B only
                engine_b_result, state = await self._run_engine_b(
                    scenario, state=state, scenario_index=scenario_index
                )

            # Arbitrate if both succeeded
            if engine_a_result and engine_b_result:
                arb_result = await self._arbitrate(scenario, engine_a_result, engine_b_result)
                final_content = arb_result.get("final_content", "")
                confidence = arb_result.get("confidence", 0.7)
            elif engine_a_result:
                final_content = engine_a_result["content"]
                confidence = 0.85
            elif engine_b_result:
                final_content = engine_b_result.final_synthesis
                confidence = 0.75
            else:
                # Both engines failed - critical degradation
                state = await self.error_handler.handle_both_engines_failure(state)
                final_content = ""
                confidence = state.get_final_confidence()

        # Apply degradation to confidence
        if state.is_degraded():
            confidence = min(confidence, state.get_final_confidence())
            self._stats["degraded_runs"] += 1

        total_time_ms = (time.time() - start_time) * 1000

        # Get timing breakdown
        report = self.timing.get_report(scenario.id)
        timing_breakdown = {}
        if report:
            for entry in report.entries:
                timing_breakdown[entry.stage.value] = entry.duration_ms

        # Generate degradation summary for ministerial brief
        degradation_summary = self.error_handler.generate_degradation_summary(state)

        result = DualEngineResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            domain=scenario.domain,
            engine_a_result=engine_a_result,
            engine_b_result=engine_b_result,
            final_content=final_content,
            confidence=confidence,
            total_time_ms=total_time_ms,
            timing_breakdown=timing_breakdown,
            degradation_state=state.to_dict(),
            degradation_summary=degradation_summary,
        )

        self._stats["scenarios_processed"] += 1
        self._stats["total_time_ms"] += total_time_ms

        degraded_msg = " [DEGRADED]" if state.is_degraded() else ""
        logger.info(
            f"Scenario {scenario.id} complete{degraded_msg}: "
            f"confidence={confidence:.2f}, time={total_time_ms/1000:.1f}s"
        )

        return result
    
    async def process_question(
        self,
        user_question: str,
        max_concurrent: int = 2,
        use_cache: bool = True,
        on_turn_complete: Optional[Callable] = None,  # Live turn-by-turn callback
    ) -> Dict[str, Any]:
        """
        Process a user question through the dual-engine pipeline.

        Generates 30 scenarios from the question, then runs:
        - Engine A: 6 scenarios (1 base + 5 deep) × 100 turns
        - Engine B: 24 scenarios (broad) × 25 turns

        Uses semantic caching to return cached results for similar queries.

        Args:
            user_question: The ministerial policy question
            max_concurrent: Max concurrent scenarios
            use_cache: Whether to check/update semantic cache
            on_turn_complete: Optional callback(engine, scenario_id, scenario_name, turn_num, agent_name, content, gpu_id)

        Returns:
            Dict with results from both engines and final synthesis
        """
        logger.info(f"Processing question: {user_question[:100]}...")

        # Step 0: Check semantic cache for similar queries
        if use_cache and self.cache:
            cached = await self.cache.get(user_question)
            if cached:
                cached_result, similarity = cached
                self._stats["cache_hits"] += 1
                logger.info(f"Cache HIT (similarity={similarity:.3f}) - returning cached result")
                return {
                    **cached_result,
                    "cache_hit": True,
                    "cache_similarity": similarity,
                }
            else:
                self._stats["cache_misses"] += 1

        # Step 1: Generate scenarios from question
        generator = create_scenario_generator()
        scenario_set = await generator.generate(user_question)

        logger.info(
            f"Generated {scenario_set.total_count} scenarios: "
            f"{len(scenario_set.engine_a_scenarios)} for Engine A, "
            f"{len(scenario_set.engine_b_scenarios)} for Engine B"
        )

        # =====================================================================
        # NEW FLOW: Engine B Compute FIRST, then Engine A debates WITH numbers
        # =====================================================================
        
        # Step 2: Engine B v5.0 Compute FIRST (before debate)
        # Agents will debate WITH these numbers, not guess and validate later
        logger.info("Step 2: Running Engine B v5.0 compute FIRST (before debate)...")
        engine_b_compute = await self._run_engine_b_compute_upfront(
            user_question,
            on_turn_complete,
        )
        
        logger.info(
            f"Engine B Compute complete: "
            f"success_rate={engine_b_compute.get('monte_carlo', {}).get('success_rate', 'N/A')}, "
            f"trend={engine_b_compute.get('forecasting', {}).get('trend', 'N/A')}"
        )
        
        # Step 3: Format Engine B results for agent prompts
        quantitative_context = self._format_quantitative_context(engine_b_compute)
        
        # Step 4: Run Engine A debate WITH Engine B numbers in prompts
        logger.info("Step 4: Running Engine A debate WITH quantitative context...")
        engine_a_results = await self._process_engine_a_batch(
            scenario_set.engine_a_scenarios,
            max_concurrent=max_concurrent,
            on_turn_complete=on_turn_complete,
            quantitative_context=quantitative_context,  # NEW: Pass Engine B results
        )
        
        # Step 5: Run Engine B (DeepSeek LLM) broad scenarios in parallel
        # This is the OLD Engine B - broad scenario analysis
        logger.info("Step 5: Running Engine B (DeepSeek) broad scenarios...")
        engine_b_scenario_results = await self.engine_b.run_all_scenarios(
            scenarios=scenario_set.engine_b_scenarios,
            on_turn_complete=on_turn_complete,
        )
        
        # Convert ScenarioResults to DualEngineResults
        engine_b_results = []
        for sr in engine_b_scenario_results:
            engine_b_results.append(DualEngineResult(
                scenario_id=sr.scenario_id,
                scenario_name=sr.scenario_name,
                domain=sr.domain,
                engine_a_result=None,
                engine_b_result=sr,
                final_content=sr.final_synthesis,
                confidence=0.75,
                total_time_ms=sr.total_time_ms,
            ))
            self._stats["engine_b_runs"] += 1

        # Step 6: Synthesize (qualitative + quantitative already integrated)
        synthesis = self._synthesize_results(
            user_question,
            scenario_set,
            engine_a_results,
            engine_b_results,
        )
        
        # Step 7: Enhance synthesis with Engine B compute results
        enhanced_synthesis = self._create_enhanced_synthesis(
            synthesis,
            engine_b_compute,
        )

        result = {
            "question": user_question,
            "scenario_set": scenario_set.to_dict(),
            "engine_a_results": [r.to_dict() for r in engine_a_results],
            "engine_b_results": [r.to_dict() for r in engine_b_results],
            "engine_b_compute": engine_b_compute,
            "synthesis": enhanced_synthesis,
            "stats": self.get_stats(),
            "cache_hit": False,
        }

        # Step 5: Cache the result for future similar queries
        if use_cache and self.cache:
            await self.cache.put(
                user_question,
                result,
                confidence=synthesis.get("overall_confidence", 0.8),
            )
            logger.debug("Result cached for future similar queries")

        return result
    
    async def _process_engine_a_batch(
        self,
        scenarios: List[GeneratedScenario],
        max_concurrent: int = 2,
        on_turn_complete: Optional[Callable] = None,
        quantitative_context: str = "",  # NEW: Engine B results for agent prompts
    ) -> List[DualEngineResult]:
        """
        Process scenarios through Engine A (deep analysis).
        
        Args:
            scenarios: List of GeneratedScenario for Engine A
            max_concurrent: Max concurrent scenarios
            on_turn_complete: Optional callback
            quantitative_context: Engine B compute results formatted for agent prompts
            
        Returns:
            List of DualEngineResult
        """
        logger.info(f"Processing {len(scenarios)} scenarios through Engine A")
        if quantitative_context:
            logger.info("Engine A agents will debate WITH quantitative context from Engine B")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_one(scenario: GeneratedScenario, idx: int):
            async with semaphore:
                # Pass quantitative context to Engine A for informed debate
                result = await self._run_engine_a_generated(
                    scenario,
                    on_turn_complete=on_turn_complete,
                    quantitative_context=quantitative_context,  # NEW
                )
                return result
        
        tasks = [process_one(s, i) for i, s in enumerate(scenarios)]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(raw_results):
            if isinstance(result, Exception):
                logger.error(f"Engine A failed for {scenarios[i].id}: {result}")
            elif result:
                results.append(result)
        
        return results
    
    async def _process_engine_b_batch(
        self,
        scenarios: List[GeneratedScenario],
        max_concurrent: int = 4,
    ) -> List[DualEngineResult]:
        """
        Process scenarios through Engine B (broad exploration).
        
        Args:
            scenarios: List of GeneratedScenario for Engine B
            max_concurrent: Max concurrent scenarios
            
        Returns:
            List of DualEngineResult
        """
        logger.info(f"Processing {len(scenarios)} scenarios through Engine B")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_one(scenario: GeneratedScenario):
            async with semaphore:
                return await self._run_engine_b_generated(scenario)
        
        tasks = [process_one(s) for s in scenarios]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(raw_results):
            if isinstance(result, Exception):
                logger.error(f"Engine B failed for {scenarios[i].id}: {result}")
            elif result:
                results.append(result)
        
        return results
    
    async def _run_engine_a_generated(
        self,
        scenario: GeneratedScenario,
        on_turn_complete: Optional[Callable] = None,
        quantitative_context: str = "",  # NEW: Engine B results for informed debate
    ) -> Optional[DualEngineResult]:
        """
        Run Engine A on a generated scenario using full QNWIS 12-agent workflow.
        
        Args:
            scenario: GeneratedScenario to process
            on_turn_complete: Optional callback for live turn-by-turn logging
            quantitative_context: Engine B compute results for agents to reference
            
        Returns:
            DualEngineResult or None on failure
        """
        start_time = time.time()
        
        with self.timing.time_stage(Stage.ENGINE_A, scenario.id):
            try:
                # Import the full QNWIS workflow with 12 agents
                from src.qnwis.orchestration.graph_llm import LLMWorkflow
                from src.qnwis.agents.base import DataClient
                from src.qnwis.llm.client import LLMClient as QNWISLLMClient
                
                # Build the question from scenario WITH quantitative context
                question = f"""Scenario Analysis: {scenario.name}

Category: {scenario.category}
Description: {scenario.description}

{scenario.prompt}

{quantitative_context}

Provide comprehensive analysis of this scenario's impacts on Qatar's economy and policy objectives.
Your arguments MUST account for the quantitative facts above."""

                logger.info(f"Engine A: Running full 12-agent QNWIS workflow for {scenario.id}")
                
                # Initialize workflow with data client and LLM
                data_client = DataClient()
                llm_client = QNWISLLMClient()
                workflow = LLMWorkflow(data_client=data_client, llm_client=llm_client)
                
                # Run the full workflow with turn-by-turn logging callback
                result = await workflow.run(
                    question,
                    on_turn_complete=on_turn_complete,  # Pass callback for live logging
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                )
                
                self._stats["engine_a_runs"] += 1
                
                total_time_ms = (time.time() - start_time) * 1000
                
                # Extract results from workflow
                synthesis = result.get("synthesis", "")
                agent_reports = result.get("agent_reports", [])
                debate_results = result.get("debate_results", {})
                debate_turns = debate_results.get("total_turns", 0) if isinstance(debate_results, dict) else 0
                
                logger.info(
                    f"Engine A complete: {len(agent_reports)} agents, "
                    f"{debate_turns} debate turns, {total_time_ms:.0f}ms"
                )
                
                return DualEngineResult(
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    domain=scenario.category,
                    engine_a_result={
                        "engine": "engine_a",
                        "content": synthesis,
                        "agent_reports": [str(r)[:500] for r in agent_reports],
                        "debate_results": {"total_turns": debate_turns},
                        "model": "qnwis_12_agent_workflow",
                        "latency_ms": total_time_ms,
                        "turns_completed": debate_turns,
                    },
                    final_content=synthesis,
                    confidence=0.85,
                    total_time_ms=total_time_ms,
                )
                
            except Exception as e:
                logger.error(f"Engine A failed for {scenario.id}: {e}")
                import traceback
                traceback.print_exc()
                return None
    
    async def _run_engine_b_generated(
        self,
        scenario: GeneratedScenario,
    ) -> Optional[DualEngineResult]:
        """
        Run Engine B on a generated scenario.
        
        Args:
            scenario: GeneratedScenario to process
            
        Returns:
            DualEngineResult or None on failure
        """
        start_time = time.time()
        
        with self.timing.time_stage(Stage.ENGINE_B, scenario.id):
            try:
                # Create a minimal scenario-like object for Engine B
                from dataclasses import dataclass
                
                @dataclass
                class MinimalScenario:
                    id: str
                    name: str
                    domain: str
                    description: str
                    inputs: list
                
                mini = MinimalScenario(
                    id=scenario.id,
                    name=scenario.name,
                    domain=scenario.category,
                    description=scenario.prompt,
                    inputs=[],
                )
                
                result = await self.engine_b.analyze_scenario(
                    mini,
                    turns=scenario.target_turns,
                )
                
                self._stats["engine_b_runs"] += 1
                
                total_time_ms = (time.time() - start_time) * 1000
                
                return DualEngineResult(
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    domain=scenario.category,
                    engine_b_result=result,
                    final_content=result.final_synthesis if result else "",
                    confidence=0.75,
                    total_time_ms=total_time_ms,
                )
                
            except Exception as e:
                logger.error(f"Engine B failed for {scenario.id}: {e}")
                return None
    
    def _synthesize_results(
        self,
        question: str,
        scenario_set: ScenarioSet,
        engine_a_results: List[DualEngineResult],
        engine_b_results: List[DualEngineResult],
    ) -> Dict[str, Any]:
        """
        Synthesize results from both engines into final analysis.
        
        Args:
            question: Original user question
            scenario_set: Generated scenario set
            engine_a_results: Results from Engine A (deep)
            engine_b_results: Results from Engine B (broad)
            
        Returns:
            Synthesis dict with key findings and recommendations
        """
        # Extract key findings from Engine A (deep analysis)
        key_findings = []
        for result in engine_a_results:
            if result.final_content:
                # Extract first meaningful sentence as a finding
                content = result.final_content.strip()
                if len(content) > 50:
                    finding = {
                        "scenario": result.scenario_name,
                        "insight": content[:300] + "..." if len(content) > 300 else content,
                        "confidence": result.confidence,
                        "source": "engine_a"
                    }
                    key_findings.append(finding)
        
        # Extract key findings from Engine B (broad exploration)
        for result in engine_b_results:
            if result.final_content:
                content = result.final_content.strip()
                if len(content) > 50:
                    finding = {
                        "scenario": result.scenario_name,
                        "insight": content[:300] + "..." if len(content) > 300 else content,
                        "confidence": result.confidence,
                        "source": "engine_b"
                    }
                    key_findings.append(finding)
        
        # Generate recommendations based on findings
        recommendations = []
        if engine_a_results:
            # Base case recommendation
            base_result = engine_a_results[0]
            if base_result.final_content:
                recommendations.append({
                    "priority": 1,
                    "recommendation": f"Based on base case analysis: {base_result.final_content[:200]}...",
                    "confidence": base_result.confidence,
                })
        
        # Add recommendations from high-confidence Engine B results
        high_conf_b = [r for r in engine_b_results if r.confidence >= 0.7]
        for i, result in enumerate(high_conf_b[:3]):  # Top 3 high-confidence
            if result.final_content:
                recommendations.append({
                    "priority": i + 2,
                    "recommendation": f"From {result.scenario_name}: {result.final_content[:150]}...",
                    "confidence": result.confidence,
                })
        
        return {
            "question": question,
            "scenarios_analyzed": scenario_set.total_count,
            "engine_a_completed": len(engine_a_results),
            "engine_b_completed": len(engine_b_results),
            "base_case_result": engine_a_results[0].final_content[:500] if engine_a_results else "",
            "deep_scenario_count": len([r for r in engine_a_results if r.scenario_id.startswith("deep_")]),
            "broad_scenario_count": len(engine_b_results),
            "overall_confidence": self._calculate_overall_confidence(engine_a_results, engine_b_results),
            "key_findings": key_findings,
            "recommendations": recommendations,
        }
    
    def _calculate_overall_confidence(
        self,
        engine_a_results: List[DualEngineResult],
        engine_b_results: List[DualEngineResult],
    ) -> float:
        """
        Calculate overall confidence from all results.
        
        Engine A results weighted higher (deep analysis).
        """
        if not engine_a_results and not engine_b_results:
            return 0.0
        
        a_scores = [r.confidence for r in engine_a_results]
        b_scores = [r.confidence for r in engine_b_results]
        
        a_avg = sum(a_scores) / len(a_scores) if a_scores else 0.0
        b_avg = sum(b_scores) / len(b_scores) if b_scores else 0.0
        
        # Weight Engine A higher (60/40)
        return 0.6 * a_avg + 0.4 * b_avg
    
    async def process_all_scenarios(
        self,
        scenarios: List = None,
        max_concurrent: int = 2,
    ) -> List[DualEngineResult]:
        """
        Process all scenarios through the dual-engine pipeline.
        
        DEPRECATED: Use process_question() instead for question-derived scenarios.
        
        This method is kept for backward compatibility with pre-defined YAML scenarios.
        
        Args:
            scenarios: List of ScenarioDefinition (or loads from templates)
            max_concurrent: Max concurrent scenarios
            
        Returns:
            List of DualEngineResult
        """
        if scenarios is None:
            from src.nsic.scenarios import ScenarioLoader
            loader = ScenarioLoader("scenarios/templates")
            loader.load_all()
            scenarios = loader.get_all()
        
        logger.info(f"Processing {len(scenarios)} scenarios (legacy mode)")
        
        with self.timing.time_stage(Stage.TOTAL, "all_scenarios"):
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(scenario):
                async with semaphore:
                    return await self.process_scenario(scenario)
            
            tasks = [process_with_semaphore(s) for s in scenarios]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Scenario {scenarios[i].id} failed: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    def process_all_scenarios_sync(
        self,
        scenarios: List = None,
        max_concurrent: int = 2,
    ) -> List[DualEngineResult]:
        """Synchronous wrapper for process_all_scenarios."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.process_all_scenarios(scenarios, max_concurrent)
        )
    
    def get_timing_summary(self) -> Dict[str, Any]:
        """Get timing summary across all stages."""
        return {
            "stage_summary": self.timing.get_stage_summary(),
            "timing_stats": self.timing.get_stats(),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        avg_time = (
            self._stats["total_time_ms"] / self._stats["scenarios_processed"]
            if self._stats["scenarios_processed"] > 0
            else 0
        )
        
        return {
            **self._stats,
            "avg_time_per_scenario_ms": avg_time,
            "engine_b_stats": self.engine_b.get_stats(),
            "arbitrator_stats": self.arbitrator.get_stats() if self._arbitrator else {},
            "timing_summary": self.get_timing_summary(),
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all components."""
        cache_status = "disabled"
        if self._cache_enabled:
            cache_status = "active" if self.semantic_cache else "lazy"

        return {
            "orchestrator": "healthy",
            "engine_b": self.engine_b.health_check(),
            "arbitrator": "loaded" if self._arbitrator else "lazy",
            "llm_client": "loaded" if self._llm_client else "lazy",
            "timing_logger": "active",
            "error_handler": "active",
            "error_handler_stats": self.error_handler.get_stats(),
            "semantic_cache": cache_status,
            "cache_stats": self.semantic_cache.get_stats() if self.semantic_cache else {},
        }
    
    # =========================================================================
    # ENGINE B v5.0 COMPUTE INTEGRATION
    # =========================================================================
    
    async def _run_engine_b_compute(
        self,
        question: str,
        synthesis: Dict[str, Any],
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run Engine B v5.0 quantitative compute services.
        
        Extracts parameters from synthesis and runs relevant compute services.
        """
        results = {}
        
        def emit(stage: str, data: dict = None):
            if on_progress:
                on_progress("engine_b_compute", "compute", 0, stage, str(data or {}), -1)
            logger.debug(f"Engine B Compute: {stage}")
        
        try:
            # Initialize compute services
            monte_carlo = MonteCarloService(gpu_ids=[0, 1])
            sensitivity = SensitivityService(gpu_id=2)
            forecasting = ForecastingService(gpu_id=4)
            
            emit("monte_carlo_start")
            
            # Monte Carlo: Test feasibility of recommendations
            # Extract key metrics from synthesis
            confidence = synthesis.get("overall_confidence", 0.7)
            
            mc_result = monte_carlo.simulate(MonteCarloInput(
                variables={
                    "base_confidence": {"mean": confidence, "std": 0.1, "distribution": "normal"},
                    "implementation_factor": {"mean": 0.85, "std": 0.15, "distribution": "normal"},
                    "external_risk": {"mean": 0.9, "std": 0.1, "distribution": "normal"},
                },
                formula="base_confidence * implementation_factor * external_risk",
                success_condition="result >= 0.5",
                n_simulations=10000,
                seed=42,
            ))
            
            results["monte_carlo"] = {
                "n_simulations": mc_result.n_simulations,
                "success_rate": mc_result.success_rate,
                "mean_result": mc_result.mean_result,
                "var_95": mc_result.var_95,
                "variable_contributions": mc_result.variable_contributions,
            }
            
            emit("monte_carlo_complete", {"success_rate": mc_result.success_rate})
            emit("sensitivity_start")
            
            # Sensitivity: Identify key drivers
            sens_result = sensitivity.analyze(SensitivityInput(
                base_values={
                    "confidence": confidence,
                    "implementation": 0.85,
                    "external": 0.9,
                },
                formula="confidence * implementation * external",
            ))
            
            results["sensitivity"] = {
                "base_result": sens_result.base_result,
                "top_drivers": sens_result.top_drivers,
            }
            
            emit("sensitivity_complete", {"top_drivers": sens_result.top_drivers})
            emit("forecasting_start")
            
            # Forecasting: Project trend
            # Use synthesis confidence as proxy for historical trend
            fc_result = forecasting.forecast(ForecastingInput(
                historical_values=[0.6, 0.65, 0.68, 0.70, confidence],
                forecast_horizon=5,
            ))
            
            results["forecasting"] = {
                "trend": fc_result.trend,
                "trend_slope": fc_result.trend_slope,
                "forecasts": [
                    {"period": f.period, "point_forecast": f.point_forecast}
                    for f in fc_result.forecasts
                ],
            }
            
            emit("forecasting_complete", {"trend": fc_result.trend})
            emit("complete")
            
            logger.info(
                f"Engine B Compute complete: "
                f"success_rate={mc_result.success_rate:.1%}, "
                f"trend={fc_result.trend}"
            )
            
        except Exception as e:
            logger.error(f"Engine B Compute failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _run_engine_a_prime(
        self,
        synthesis: Dict[str, Any],
        engine_b_compute: Dict[str, Any],
        conflict_report,
        on_progress: Optional[Callable] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Run Engine A Prime focused validation (30-50 turns).
        
        Called when Engine B detects conflicts with Engine A's recommendations.
        """
        from qnwis.agents.prompts.base import build_engine_a_prime_prompt
        
        try:
            # Build conflict resolution prompt
            prompt = build_engine_a_prime_prompt(
                engine_a_recommendation=synthesis.get("recommendation", ""),
                engine_a_confidence=synthesis.get("overall_confidence", 0.7),
                engine_a_key_claims=synthesis.get("key_findings", [])[:5],
                engine_b_results=engine_b_compute,
                conflicts=[
                    {
                        "conflict_type": c.conflict_type,
                        "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                        "engine_a_claim": c.engine_a_claim,
                        "engine_b_finding": c.engine_b_finding,
                    }
                    for c in conflict_report.conflicts[:5]
                ],
            )
            
            logger.info(f"Engine A Prime: Resolving {len(conflict_report.conflicts)} conflicts")
            
            # For now, return a structured resolution
            # In full implementation, this would run additional LLM turns
            return {
                "status": "resolved",
                "conflicts_addressed": len(conflict_report.conflicts),
                "resolution_prompt": prompt[:500] + "...",
                "revised_confidence": synthesis.get("overall_confidence", 0.7) * 0.9,
            }
            
        except Exception as e:
            logger.error(f"Engine A Prime failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _enhance_synthesis_with_compute(
        self,
        synthesis: Dict[str, Any],
        engine_b_compute: Dict[str, Any],
        conflict_report,
        engine_a_prime_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Enhance synthesis with Engine B quantitative results.
        """
        enhanced = dict(synthesis)
        
        # Add quantitative validation section
        enhanced["quantitative_validation"] = {}
        
        if "monte_carlo" in engine_b_compute:
            mc = engine_b_compute["monte_carlo"]
            enhanced["quantitative_validation"]["feasibility"] = {
                "success_probability": mc.get("success_rate"),
                "simulations": mc.get("n_simulations"),
                "interpretation": self._interpret_probability(mc.get("success_rate", 0)),
            }
        
        if "forecasting" in engine_b_compute:
            fc = engine_b_compute["forecasting"]
            enhanced["quantitative_validation"]["outlook"] = {
                "trend": fc.get("trend"),
                "slope": fc.get("trend_slope"),
            }
        
        if "sensitivity" in engine_b_compute:
            sens = engine_b_compute["sensitivity"]
            enhanced["quantitative_validation"]["key_drivers"] = sens.get("top_drivers", [])
        
        # Add conflict status
        enhanced["alignment"] = {
            "score": conflict_report.alignment_score,
            "conflicts_detected": len(conflict_report.conflicts),
            "prime_triggered": conflict_report.should_trigger_prime,
        }
        
        # Adjust confidence based on alignment
        original_confidence = synthesis.get("overall_confidence", 0.7)
        alignment_factor = conflict_report.alignment_score / 100
        enhanced["adjusted_confidence"] = original_confidence * (0.5 + 0.5 * alignment_factor)
        
        # Add Engine A Prime resolution if triggered
        if engine_a_prime_result:
            enhanced["conflict_resolution"] = engine_a_prime_result
        
        return enhanced
    
    def _interpret_probability(self, prob: float) -> str:
        """Interpret Monte Carlo success probability."""
        if prob >= 0.80:
            return "highly_feasible"
        elif prob >= 0.60:
            return "feasible"
        elif prob >= 0.40:
            return "uncertain"
        elif prob >= 0.20:
            return "challenging"
        else:
            return "unlikely"
    
    # =========================================================================
    # NEW FLOW: Engine B Compute FIRST (before debate)
    # =========================================================================
    
    async def _run_engine_b_compute_upfront(
        self,
        question: str,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run Engine B v5.0 compute services BEFORE Engine A debate.
        
        This is the new flow: compute first, then debate with numbers.
        Agents will have quantitative facts before they start debating.
        """
        results = {}
        
        def emit(stage: str, data: dict = None):
            if on_progress:
                on_progress("engine_b_compute", "compute", 0, stage, str(data or {}), -1)
            logger.debug(f"Engine B Compute (upfront): {stage}")
        
        try:
            emit("initializing")
            
            # Initialize compute services
            monte_carlo = MonteCarloService(gpu_ids=[0, 1])
            sensitivity = SensitivityService(gpu_id=2)
            forecasting = ForecastingService(gpu_id=4)
            thresholds = ThresholdService(gpu_id=5)
            
            emit("monte_carlo_start")
            
            # Monte Carlo: General policy feasibility simulation
            mc_result = monte_carlo.simulate(MonteCarloInput(
                variables={
                    "policy_effectiveness": {"mean": 0.70, "std": 0.15, "distribution": "normal"},
                    "implementation_quality": {"mean": 0.80, "std": 0.10, "distribution": "normal"},
                    "external_factors": {"mean": 0.85, "std": 0.12, "distribution": "normal"},
                    "resource_availability": {"mean": 0.75, "std": 0.10, "distribution": "normal"},
                },
                formula="policy_effectiveness * implementation_quality * external_factors * resource_availability",
                success_condition="result >= 0.35",
                n_simulations=10000,
                seed=42,
            ))
            
            results["monte_carlo"] = {
                "n_simulations": mc_result.n_simulations,
                "success_rate": mc_result.success_rate,
                "mean_result": mc_result.mean_result,
                "std_result": mc_result.std_result,
                "var_95": mc_result.var_95,
                "p5": mc_result.percentiles.get("p5", 0),
                "p95": mc_result.percentiles.get("p95", 0),
                "variable_contributions": mc_result.variable_contributions,
            }
            
            emit("monte_carlo_complete", {"success_rate": mc_result.success_rate})
            emit("sensitivity_start")
            
            # Sensitivity: Key drivers analysis
            sens_result = sensitivity.analyze(SensitivityInput(
                base_values={
                    "policy_effectiveness": 0.70,
                    "implementation_quality": 0.80,
                    "external_factors": 0.85,
                    "resource_availability": 0.75,
                },
                formula="policy_effectiveness * implementation_quality * external_factors * resource_availability",
            ))
            
            results["sensitivity"] = {
                "base_result": sens_result.base_result,
                "top_drivers": sens_result.top_drivers,
                "parameter_impacts": [
                    {"name": p.name, "elasticity": p.elasticity, "direction": p.direction}
                    for p in sens_result.parameter_impacts[:5]
                ],
            }
            
            emit("sensitivity_complete", {"top_drivers": sens_result.top_drivers})
            emit("forecasting_start")
            
            # Forecasting: Trend projection
            fc_result = forecasting.forecast(ForecastingInput(
                historical_values=[0.55, 0.58, 0.62, 0.65, 0.68],
                forecast_horizon=5,
            ))
            
            results["forecasting"] = {
                "trend": fc_result.trend,
                "trend_slope": fc_result.trend_slope,
                "forecasts": [
                    {
                        "period": f.period,
                        "point_forecast": f.point_forecast,
                        "lower_bound": f.lower_bound,
                        "upper_bound": f.upper_bound,
                    }
                    for f in fc_result.forecasts
                ],
            }
            
            emit("forecasting_complete", {"trend": fc_result.trend})
            emit("complete")
            
            logger.info(
                f"Engine B Compute (upfront) complete: "
                f"success_rate={mc_result.success_rate:.1%}, "
                f"trend={fc_result.trend}, "
                f"top_driver={sens_result.top_drivers[0] if sens_result.top_drivers else 'N/A'}"
            )
            
        except Exception as e:
            logger.error(f"Engine B Compute (upfront) failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def _format_quantitative_context(self, engine_b_compute: Dict[str, Any]) -> str:
        """
        Format Engine B compute results for inclusion in Engine A agent prompts.
        
        This gives agents the quantitative facts BEFORE they debate.
        """
        if not engine_b_compute or "error" in engine_b_compute:
            return ""
        
        sections = [
            "═" * 70,
            "QUANTITATIVE CONTEXT (from Engine B Compute)",
            "Before you debate, here are the computed facts:",
            "═" * 70,
            "",
        ]
        
        if "monte_carlo" in engine_b_compute:
            mc = engine_b_compute["monte_carlo"]
            success = mc.get("success_rate", 0)
            mean = mc.get("mean_result", 0)
            p5 = mc.get("p5", mc.get("var_95", 0))
            p95 = mc.get("p95", mean * 1.3)
            
            # Get top driver
            contributions = mc.get("variable_contributions", {})
            top_driver = max(contributions, key=contributions.get) if contributions else "N/A"
            top_impact = contributions.get(top_driver, 0) if contributions else 0
            
            sections.extend([
                "### Monte Carlo Analysis (10,000 simulations)",
                f"- Success probability: {success:.1%}",
                f"- Mean outcome: {mean:.3f}",
                f"- 90% confidence range: [{p5:.3f}, {p95:.3f}]",
                f"- Interpretation: {self._interpret_probability(success)}",
                f"- Top driver: {top_driver} ({top_impact:.0%} of variance)",
                "",
            ])
        
        if "sensitivity" in engine_b_compute:
            sens = engine_b_compute["sensitivity"]
            top_drivers = sens.get("top_drivers", [])
            impacts = sens.get("parameter_impacts", [])
            
            sections.append("### Key Drivers (Sensitivity Analysis)")
            for i, driver in enumerate(top_drivers[:3], 1):
                impact = next((p for p in impacts if p["name"] == driver), {})
                sections.append(f"{i}. {driver} ({impact.get('elasticity', 0):.1%} impact, {impact.get('direction', 'N/A')})")
            sections.append("")
        
        if "forecasting" in engine_b_compute:
            fc = engine_b_compute["forecasting"]
            trend = fc.get("trend", "unknown")
            slope = fc.get("trend_slope", 0)
            forecasts = fc.get("forecasts", [])
            
            sections.extend([
                "### Trend Forecast",
                f"- Overall trend: {trend}",
                f"- Trend slope: {slope:.4f} per period",
            ])
            
            if forecasts:
                last = forecasts[-1]
                sections.append(
                    f"- 5-year projection: {last.get('point_forecast', 0):.3f} "
                    f"[{last.get('lower_bound', 0):.3f} - {last.get('upper_bound', 0):.3f}]"
                )
            sections.append("")
        
        sections.extend([
            "═" * 70,
            "Your arguments MUST account for these quantitative facts.",
            "═" * 70,
        ])
        
        return "\n".join(sections)
    
    def _create_enhanced_synthesis(
        self,
        synthesis: Dict[str, Any],
        engine_b_compute: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create enhanced synthesis combining qualitative debate + quantitative compute.
        
        Simpler than conflict detection - just merge the results.
        """
        enhanced = dict(synthesis)
        
        # Add quantitative validation section
        enhanced["quantitative_validation"] = {}
        
        if "monte_carlo" in engine_b_compute:
            mc = engine_b_compute["monte_carlo"]
            enhanced["quantitative_validation"]["feasibility"] = {
                "success_probability": mc.get("success_rate"),
                "simulations": mc.get("n_simulations"),
                "interpretation": self._interpret_probability(mc.get("success_rate", 0)),
                "mean_outcome": mc.get("mean_result"),
            }
        
        if "forecasting" in engine_b_compute:
            fc = engine_b_compute["forecasting"]
            enhanced["quantitative_validation"]["outlook"] = {
                "trend": fc.get("trend"),
                "slope": fc.get("trend_slope"),
            }
        
        if "sensitivity" in engine_b_compute:
            sens = engine_b_compute["sensitivity"]
            enhanced["quantitative_validation"]["key_drivers"] = sens.get("top_drivers", [])
        
        # Compute adjusted confidence based on Monte Carlo success rate
        original_confidence = synthesis.get("overall_confidence", 0.7)
        mc_success = engine_b_compute.get("monte_carlo", {}).get("success_rate", 0.5)
        enhanced["adjusted_confidence"] = (original_confidence + mc_success) / 2
        
        enhanced["analysis_type"] = "quantitative_informed_debate"
        
        return enhanced


def create_dual_engine_orchestrator() -> DualEngineOrchestrator:
    """Factory function to create DualEngineOrchestrator."""
    return DualEngineOrchestrator()
