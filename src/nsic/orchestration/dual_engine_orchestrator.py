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
    ):
        """
        Initialize dual-engine orchestrator.
        
        Args:
            engine_b: Engine B instance (or creates one)
            arbitrator: EnsembleArbitrator instance (or creates one)
            timing_logger: TimingLogger instance (or uses global)
            llm_client: Azure LLM client for Engine A
        """
        self.engine_b = engine_b or create_engine_b(mock=False)
        self._arbitrator = arbitrator
        self.timing = timing_logger or get_timing_logger()
        self._llm_client = llm_client
        
        # Stats
        self._stats = {
            "scenarios_processed": 0,
            "engine_a_runs": 0,
            "engine_b_runs": 0,
            "arbitrations": 0,
            "total_time_ms": 0.0,
        }
        
        logger.info("DualEngineOrchestrator initialized - REAL MODE")
    
    @property
    def arbitrator(self):
        """Lazy load arbitrator."""
        if self._arbitrator is None:
            from src.nsic.arbitration import create_ensemble_arbitrator
            self._arbitrator = create_ensemble_arbitrator()
        return self._arbitrator
    
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
    ) -> Optional[Dict[str, Any]]:
        """
        Run Engine A (Azure GPT-5) for deep analysis.
        
        Args:
            scenario: ScenarioDefinition
            context: Pre-fetched context
            
        Returns:
            Dict with analysis results or None on failure
        """
        if not self.llm_client:
            logger.warning("Azure LLM client not available for Engine A")
            return None
        
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
                }
                
            except Exception as e:
                logger.error(f"Engine A failed for {scenario.id}: {e}")
                return None
    
    async def _run_engine_b(
        self,
        scenario,
        turns: int = None,
    ) -> Optional[ScenarioResult]:
        """
        Run Engine B (DeepSeek) for broad exploration.
        
        Args:
            scenario: ScenarioDefinition
            turns: Number of turns (default: ENGINE_B_TURNS)
            
        Returns:
            ScenarioResult or None on failure
        """
        turns = turns or self.ENGINE_B_TURNS
        
        with self.timing.time_stage(Stage.ENGINE_B, scenario.id, turns=turns):
            try:
                result = await self.engine_b.analyze_scenario(scenario, turns=turns)
                self._stats["engine_b_runs"] += 1
                return result
            except Exception as e:
                logger.error(f"Engine B failed for {scenario.id}: {e}")
                return None
    
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
    ) -> DualEngineResult:
        """
        Process a single scenario through the dual-engine pipeline.
        
        Args:
            scenario: ScenarioDefinition
            run_both_engines: If True, run both engines and arbitrate
            
        Returns:
            DualEngineResult with final analysis
        """
        start_time = time.time()
        
        logger.info(f"Processing scenario: {scenario.id}")
        
        # Get context
        with self.timing.time_stage(Stage.CONTEXT_RETRIEVAL, scenario.id):
            context = ""
            try:
                context = await self.engine_b._get_context(scenario.description)
                context = self.engine_b._format_context_prompt(context)
            except Exception as e:
                logger.warning(f"Context retrieval failed: {e}")
        
        # Determine which engines to run
        engine_a_result = None
        engine_b_result = None
        
        if scenario.assigned_engine == "engine_a":
            # Run only Engine A
            engine_a_result = await self._run_engine_a(scenario, context)
            final_content = engine_a_result["content"] if engine_a_result else ""
            confidence = 0.85
            
        elif scenario.assigned_engine == "engine_b":
            # Run only Engine B
            engine_b_result = await self._run_engine_b(scenario)
            final_content = engine_b_result.final_synthesis if engine_b_result else ""
            confidence = 0.75
            
        else:  # "auto" - run both and arbitrate
            if run_both_engines:
                # Run both engines in parallel
                engine_a_task = self._run_engine_a(scenario, context)
                engine_b_task = self._run_engine_b(scenario, turns=10)  # Fewer turns for parallel
                
                engine_a_result, engine_b_result = await asyncio.gather(
                    engine_a_task,
                    engine_b_task,
                    return_exceptions=True,
                )
                
                # Handle exceptions
                if isinstance(engine_a_result, Exception):
                    logger.error(f"Engine A exception: {engine_a_result}")
                    engine_a_result = None
                if isinstance(engine_b_result, Exception):
                    logger.error(f"Engine B exception: {engine_b_result}")
                    engine_b_result = None
            else:
                # Default to Engine B only
                engine_b_result = await self._run_engine_b(scenario)
            
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
                final_content = ""
                confidence = 0.0
        
        total_time_ms = (time.time() - start_time) * 1000
        
        # Get timing breakdown
        report = self.timing.get_report(scenario.id)
        timing_breakdown = {}
        if report:
            for entry in report.entries:
                timing_breakdown[entry.stage.value] = entry.duration_ms
        
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
        )
        
        self._stats["scenarios_processed"] += 1
        self._stats["total_time_ms"] += total_time_ms
        
        logger.info(
            f"Scenario {scenario.id} complete: "
            f"confidence={confidence:.2f}, time={total_time_ms/1000:.1f}s"
        )
        
        return result
    
    async def process_all_scenarios(
        self,
        scenarios: List = None,
        max_concurrent: int = 2,
    ) -> List[DualEngineResult]:
        """
        Process all scenarios through the dual-engine pipeline.
        
        Args:
            scenarios: List of ScenarioDefinition (or loads from Phase 5)
            max_concurrent: Max concurrent scenarios
            
        Returns:
            List of DualEngineResult
        """
        if scenarios is None:
            from src.nsic.scenarios import ScenarioLoader
            loader = ScenarioLoader("scenarios")
            loader.load_all()
            scenarios = loader.get_all()
        
        logger.info(f"Processing {len(scenarios)} scenarios")
        
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
        return {
            "orchestrator": "healthy",
            "engine_b": self.engine_b.health_check(),
            "arbitrator": "loaded" if self._arbitrator else "lazy",
            "llm_client": "loaded" if self._llm_client else "lazy",
            "timing_logger": "active",
        }


def create_dual_engine_orchestrator() -> DualEngineOrchestrator:
    """Factory function to create DualEngineOrchestrator."""
    return DualEngineOrchestrator()
