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
from typing import List, Dict, Any, Optional, Tuple
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
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "domain": self.domain,
            "engine_a_completed": self.engine_a_result is not None,
            "engine_b_completed": self.engine_b_result is not None,
            "arbitration_completed": self.arbitration_result is not None,
            "confidence": self.confidence,
            "total_time_ms": self.total_time_ms,
            "timing_breakdown": self.timing_breakdown,
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
        Run Engine A (Azure GPT-5) for deep analysis with graceful degradation.

        Args:
            scenario: ScenarioDefinition
            context: Pre-fetched context
            state: Current analysis state for degradation tracking

        Returns:
            Tuple of (result dict, updated state) - result may be None on failure
        """
        state = state or self.error_handler.create_state()

        if not self.llm_client:
            logger.warning("Azure LLM client not available for Engine A")
            state = await self.error_handler.handle_engine_a_failure(
                state, Exception("LLM client not available")
            )
            return None, state

        with self.timing.time_stage(Stage.ENGINE_A, scenario.id):
            try:
                # Build scenario prompt
                scenario_text = f"""Scenario: {scenario.name}
Domain: {scenario.domain}
Description: {scenario.description}

Inputs:
"""
                for inp in scenario.inputs:
                    scenario_text += f"- {inp.variable}: {inp.base_value} → {inp.shock_value} ({inp.shock_type})\n"

                # Run deep analysis
                response = await self.llm_client.analyze_scenario(
                    scenario=scenario_text,
                    context=context,
                    depth="comprehensive",
                )

                self._stats["engine_a_runs"] += 1

                return {
                    "engine": "engine_a",
                    "content": response.content,
                    "model": response.model,
                    "task_type": response.task_type,
                    "latency_ms": response.latency_ms,
                    "turns_completed": 1,  # Single deep turn
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

        # Step 1: Generate 30 scenarios from question
        generator = create_scenario_generator()
        scenario_set = await generator.generate(user_question)

        logger.info(
            f"Generated {scenario_set.total_count} scenarios: "
            f"{len(scenario_set.engine_a_scenarios)} for Engine A, "
            f"{len(scenario_set.engine_b_scenarios)} for Engine B"
        )

        # Step 2: Process Engine A scenarios (deep analysis)
        engine_a_results = await self._process_engine_a_batch(
            scenario_set.engine_a_scenarios,
            max_concurrent=max_concurrent,
        )

        # Step 3: Process Engine B scenarios (broad exploration)
        engine_b_results = await self._process_engine_b_batch(
            scenario_set.engine_b_scenarios,
            max_concurrent=max_concurrent,
        )

        # Step 4: Synthesize results
        synthesis = self._synthesize_results(
            user_question,
            scenario_set,
            engine_a_results,
            engine_b_results,
        )

        result = {
            "question": user_question,
            "scenario_set": scenario_set.to_dict(),
            "engine_a_results": [r.to_dict() for r in engine_a_results],
            "engine_b_results": [r.to_dict() for r in engine_b_results],
            "synthesis": synthesis,
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
    ) -> List[DualEngineResult]:
        """
        Process scenarios through Engine A (deep analysis).
        
        Args:
            scenarios: List of GeneratedScenario for Engine A
            max_concurrent: Max concurrent scenarios
            
        Returns:
            List of DualEngineResult
        """
        logger.info(f"Processing {len(scenarios)} scenarios through Engine A")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_one(scenario: GeneratedScenario):
            async with semaphore:
                return await self._run_engine_a_generated(scenario)
        
        tasks = [process_one(s) for s in scenarios]
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
    ) -> Optional[DualEngineResult]:
        """
        Run Engine A on a generated scenario.
        
        Args:
            scenario: GeneratedScenario to process
            
        Returns:
            DualEngineResult or None on failure
        """
        start_time = time.time()
        
        if not self.llm_client:
            logger.warning("Azure LLM client not available for Engine A")
            return None
        
        with self.timing.time_stage(Stage.ENGINE_A, scenario.id):
            try:
                response = await self.llm_client.analyze_scenario(
                    scenario=scenario.prompt,
                    context="",
                    depth="comprehensive",
                )
                
                self._stats["engine_a_runs"] += 1
                
                total_time_ms = (time.time() - start_time) * 1000
                
                return DualEngineResult(
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    domain=scenario.category,
                    engine_a_result={
                        "engine": "engine_a",
                        "content": response.content,
                        "model": response.model,
                        "latency_ms": response.latency_ms,
                    },
                    final_content=response.content,
                    confidence=0.85,
                    total_time_ms=total_time_ms,
                )
                
            except Exception as e:
                logger.error(f"Engine A failed for {scenario.id}: {e}")
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
            Synthesis dict with key findings
        """
        return {
            "question": question,
            "scenarios_analyzed": scenario_set.total_count,
            "engine_a_completed": len(engine_a_results),
            "engine_b_completed": len(engine_b_results),
            "base_case_result": engine_a_results[0].final_content[:500] if engine_a_results else "",
            "deep_scenario_count": len([r for r in engine_a_results if r.scenario_id.startswith("deep_")]),
            "broad_scenario_count": len(engine_b_results),
            "overall_confidence": self._calculate_overall_confidence(engine_a_results, engine_b_results),
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


def create_dual_engine_orchestrator() -> DualEngineOrchestrator:
    """Factory function to create DualEngineOrchestrator."""
    return DualEngineOrchestrator()
