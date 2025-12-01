"""
Hybrid Flow Orchestrator
Integrates Engine A (qualitative) with Engine B (quantitative) compute results.
Manages the feedback loop and Engine A Prime validation rounds.
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from datetime import datetime

from .conflict_detector import ConflictDetector, ConflictReport, Conflict

# Import Engine B services
from ..services.monte_carlo import MonteCarloService, MonteCarloInput
from ..services.sensitivity import SensitivityService, SensitivityInput
from ..services.optimization import OptimizationService, OptimizationInput
from ..services.forecasting import ForecastingService, ForecastingInput
from ..services.thresholds import ThresholdService, ThresholdInput
from ..services.benchmarking import BenchmarkingService, BenchmarkingInput
from ..services.correlation import CorrelationService, CorrelationInput

logger = logging.getLogger(__name__)


@dataclass
class ComputeRequest:
    """Request for Engine B compute services."""
    
    # Which services to run
    monte_carlo: Optional[MonteCarloInput] = None
    sensitivity: Optional[SensitivityInput] = None
    optimization: Optional[OptimizationInput] = None
    forecasting: Optional[ForecastingInput] = None
    thresholds: Optional[ThresholdInput] = None
    benchmarking: Optional[BenchmarkingInput] = None
    correlation: Optional[CorrelationInput] = None


@dataclass
class HybridResult:
    """Complete result from hybrid Engine A + Engine B flow."""
    
    # Original Engine A result
    engine_a_result: dict
    
    # Engine B compute results
    engine_b_result: dict
    
    # Conflict analysis
    conflict_report: ConflictReport
    
    # Engine A Prime result (if triggered)
    engine_a_prime_result: Optional[dict] = None
    
    # Final synthesis
    final_synthesis: dict = field(default_factory=dict)
    
    # Execution metadata
    execution_time_ms: float = 0.0
    timestamp: str = ""
    

class HybridFlowOrchestrator:
    """
    Orchestrates the hybrid Engine A + Engine B workflow.
    
    Flow:
    1. Engine A completes debate (150 turns) - handled externally
    2. Engine B runs quantitative compute services
    3. Conflict detector compares results
    4. If conflicts: Engine A Prime runs focused debate (30-50 turns)
    5. Final synthesis combines qualitative + quantitative
    """
    
    def __init__(
        self,
        engine_a_prime_callback: Optional[Callable] = None,
        prime_turns: int = 40,
    ):
        """
        Initialize hybrid flow orchestrator.
        
        Args:
            engine_a_prime_callback: Async function to run Engine A Prime debate
                Signature: async def(questions: list[str], context: dict) -> dict
            prime_turns: Number of turns for Engine A Prime debate
        """
        self.engine_a_prime_callback = engine_a_prime_callback
        self.prime_turns = prime_turns
        
        # Initialize Engine B services
        self.services = {
            "monte_carlo": MonteCarloService(gpu_ids=[0, 1]),
            "sensitivity": SensitivityService(gpu_id=2),
            "optimization": OptimizationService(gpu_id=3),
            "forecasting": ForecastingService(gpu_id=4),
            "thresholds": ThresholdService(gpu_id=5),
            "benchmarking": BenchmarkingService(gpu_id=6),
            "correlation": CorrelationService(gpu_id=7),
        }
        
        self.conflict_detector = ConflictDetector()
        
        logger.info("HybridFlowOrchestrator initialized with all Engine B services")
    
    async def run(
        self,
        engine_a_result: dict,
        compute_request: ComputeRequest,
        on_progress: Optional[Callable[[str, dict], None]] = None,
    ) -> HybridResult:
        """
        Run the full hybrid flow.
        
        Args:
            engine_a_result: Result from Engine A debate
            compute_request: Specifications for Engine B services
            on_progress: Optional callback for progress updates
            
        Returns:
            HybridResult with complete analysis
        """
        import time
        start_time = time.perf_counter()
        
        def emit_progress(stage: str, data: dict):
            if on_progress:
                on_progress(stage, data)
            logger.info(f"Hybrid flow progress: {stage}")
        
        emit_progress("engine_b_start", {"services": self._get_requested_services(compute_request)})
        
        # Step 1: Run Engine B compute services
        engine_b_result = await self._run_engine_b(compute_request, emit_progress)
        
        emit_progress("conflict_detection_start", {})
        
        # Step 2: Detect conflicts
        conflict_report = self.conflict_detector.detect_conflicts(
            engine_a_result, engine_b_result
        )
        
        emit_progress("conflict_detection_complete", {
            "conflicts": len(conflict_report.conflicts),
            "alignment_score": conflict_report.alignment_score,
            "should_trigger_prime": conflict_report.should_trigger_prime,
        })
        
        # Step 3: Run Engine A Prime if needed
        engine_a_prime_result = None
        if conflict_report.should_trigger_prime:
            emit_progress("engine_a_prime_start", {
                "focus": conflict_report.prime_focus,
                "questions": conflict_report.prime_questions,
            })
            
            engine_a_prime_result = await self._run_engine_a_prime(
                engine_a_result,
                engine_b_result,
                conflict_report,
            )
            
            emit_progress("engine_a_prime_complete", {
                "turns": self.prime_turns,
            })
        
        # Step 4: Generate final synthesis
        emit_progress("synthesis_start", {})
        
        final_synthesis = self._generate_final_synthesis(
            engine_a_result,
            engine_b_result,
            conflict_report,
            engine_a_prime_result,
        )
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        emit_progress("complete", {
            "execution_time_ms": execution_time_ms,
        })
        
        return HybridResult(
            engine_a_result=engine_a_result,
            engine_b_result=engine_b_result,
            conflict_report=conflict_report,
            engine_a_prime_result=engine_a_prime_result,
            final_synthesis=final_synthesis,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    async def _run_engine_b(
        self,
        compute_request: ComputeRequest,
        emit_progress: Callable,
    ) -> dict:
        """Run all requested Engine B services."""
        results = {}
        
        # Run services concurrently
        tasks = []
        service_names = []
        
        if compute_request.monte_carlo:
            tasks.append(self._run_service("monte_carlo", compute_request.monte_carlo))
            service_names.append("monte_carlo")
        
        if compute_request.sensitivity:
            tasks.append(self._run_service("sensitivity", compute_request.sensitivity))
            service_names.append("sensitivity")
        
        if compute_request.optimization:
            tasks.append(self._run_service("optimization", compute_request.optimization))
            service_names.append("optimization")
        
        if compute_request.forecasting:
            tasks.append(self._run_service("forecasting", compute_request.forecasting))
            service_names.append("forecasting")
        
        if compute_request.thresholds:
            tasks.append(self._run_service("thresholds", compute_request.thresholds))
            service_names.append("thresholds")
        
        if compute_request.benchmarking:
            tasks.append(self._run_service("benchmarking", compute_request.benchmarking))
            service_names.append("benchmarking")
        
        if compute_request.correlation:
            tasks.append(self._run_service("correlation", compute_request.correlation))
            service_names.append("correlation")
        
        if tasks:
            # Run all services concurrently
            service_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, result in zip(service_names, service_results):
                if isinstance(result, Exception):
                    logger.error(f"Service {name} failed: {result}")
                    results[name] = {"error": str(result)}
                else:
                    results[name] = result
                    emit_progress(f"engine_b_{name}_complete", {
                        "execution_time_ms": result.get("execution_time_ms", 0),
                    })
        
        return results
    
    async def _run_service(self, name: str, input_spec: Any) -> dict:
        """Run a single Engine B service."""
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Unknown service: {name}")
        
        # Run service (most are synchronous but we wrap for consistency)
        loop = asyncio.get_event_loop()
        
        if name == "monte_carlo":
            result = await loop.run_in_executor(None, service.simulate, input_spec)
        elif name == "sensitivity":
            result = await loop.run_in_executor(None, service.analyze, input_spec)
        elif name == "optimization":
            result = await loop.run_in_executor(None, service.solve, input_spec)
        elif name == "forecasting":
            result = await loop.run_in_executor(None, service.forecast, input_spec)
        elif name == "thresholds":
            result = await loop.run_in_executor(None, service.analyze, input_spec)
        elif name == "benchmarking":
            result = await loop.run_in_executor(None, service.benchmark, input_spec)
        elif name == "correlation":
            result = await loop.run_in_executor(None, service.analyze, input_spec)
        else:
            raise ValueError(f"Unknown service: {name}")
        
        # Convert dataclass to dict if needed
        if hasattr(result, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(result)
        
        return result
    
    async def _run_engine_a_prime(
        self,
        engine_a_result: dict,
        engine_b_result: dict,
        conflict_report: ConflictReport,
    ) -> Optional[dict]:
        """Run Engine A Prime focused debate."""
        
        if not self.engine_a_prime_callback:
            logger.warning("Engine A Prime callback not configured, skipping")
            return None
        
        # Prepare context for Engine A Prime
        context = {
            "original_recommendation": engine_a_result.get("recommendation", ""),
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "engine_a_claim": c.engine_a_claim,
                    "engine_b_finding": c.engine_b_finding,
                    "evidence": c.evidence,
                    "severity": c.severity.value,
                }
                for c in conflict_report.critical_conflicts
            ],
            "quantitative_results": engine_b_result,
            "alignment_score": conflict_report.alignment_score,
        }
        
        # Run Engine A Prime
        try:
            result = await self.engine_a_prime_callback(
                questions=conflict_report.prime_questions,
                context=context,
            )
            return result
        except Exception as e:
            logger.error(f"Engine A Prime failed: {e}")
            return {"error": str(e)}
    
    def _generate_final_synthesis(
        self,
        engine_a_result: dict,
        engine_b_result: dict,
        conflict_report: ConflictReport,
        engine_a_prime_result: Optional[dict],
    ) -> dict:
        """Generate final synthesis combining all results."""
        
        synthesis = {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "hybrid_v5.0",
            
            # Qualitative foundation
            "qualitative_analysis": {
                "source": "engine_a",
                "recommendation": engine_a_result.get("recommendation", ""),
                "key_findings": engine_a_result.get("key_findings", []),
                "confidence": engine_a_result.get("confidence", 0.0),
            },
            
            # Quantitative validation
            "quantitative_validation": self._summarize_quantitative(engine_b_result),
            
            # Conflict resolution
            "conflict_analysis": {
                "alignment_score": conflict_report.alignment_score,
                "total_conflicts": len(conflict_report.conflicts),
                "critical_conflicts": len(conflict_report.critical_conflicts),
                "conflicts": [
                    {
                        "type": c.conflict_type,
                        "severity": c.severity.value,
                        "finding": c.engine_b_finding,
                        "recommendation": c.recommendation,
                    }
                    for c in conflict_report.conflicts
                ],
            },
            
            # Prime revision (if any)
            "revision": None,
            
            # Final recommendation
            "final_recommendation": "",
            "confidence_adjusted": 0.0,
            "risk_assessment": "",
        }
        
        # Include Engine A Prime revision if available
        if engine_a_prime_result and "error" not in engine_a_prime_result:
            synthesis["revision"] = {
                "source": "engine_a_prime",
                "revised_recommendation": engine_a_prime_result.get("recommendation", ""),
                "addressed_conflicts": engine_a_prime_result.get("addressed_conflicts", []),
            }
        
        # Generate final recommendation
        synthesis["final_recommendation"] = self._generate_final_recommendation(
            engine_a_result,
            engine_b_result,
            conflict_report,
            engine_a_prime_result,
        )
        
        # Adjust confidence based on alignment
        base_confidence = engine_a_result.get("confidence", 0.7)
        alignment_factor = conflict_report.alignment_score / 100
        synthesis["confidence_adjusted"] = base_confidence * (0.5 + 0.5 * alignment_factor)
        
        # Risk assessment
        synthesis["risk_assessment"] = self._generate_risk_assessment(
            engine_b_result, conflict_report
        )
        
        return synthesis
    
    def _summarize_quantitative(self, engine_b_result: dict) -> dict:
        """Summarize quantitative results."""
        summary = {}
        
        if "monte_carlo" in engine_b_result:
            mc = engine_b_result["monte_carlo"]
            summary["feasibility"] = {
                "success_rate": mc.get("success_rate"),
                "var_95": mc.get("var_95"),
                "interpretation": self._interpret_success_rate(mc.get("success_rate", 0)),
            }
        
        if "forecasting" in engine_b_result:
            fc = engine_b_result["forecasting"]
            summary["forecast"] = {
                "trend": fc.get("trend"),
                "slope": fc.get("trend_slope"),
                "confidence": fc.get("confidence_level"),
            }
        
        if "thresholds" in engine_b_result:
            th = engine_b_result["thresholds"]
            summary["thresholds"] = {
                "risk_level": th.get("risk_level"),
                "safe_range": th.get("safe_range"),
                "critical_count": len(th.get("critical_thresholds", [])),
            }
        
        if "benchmarking" in engine_b_result:
            bm = engine_b_result["benchmarking"]
            summary["benchmarking"] = {
                "composite_score": bm.get("composite_score"),
                "rank": bm.get("overall_rank"),
                "strengths": bm.get("strengths", []),
                "improvement_areas": bm.get("improvement_areas", []),
            }
        
        if "sensitivity" in engine_b_result:
            sens = engine_b_result["sensitivity"]
            summary["sensitivity"] = {
                "top_drivers": sens.get("top_drivers", []),
            }
        
        if "correlation" in engine_b_result:
            corr = engine_b_result["correlation"]
            if corr.get("driver_analysis"):
                summary["drivers"] = {
                    "top_positive": corr["driver_analysis"].get("top_positive_drivers", []),
                    "top_negative": corr["driver_analysis"].get("top_negative_drivers", []),
                }
        
        return summary
    
    def _interpret_success_rate(self, rate: float) -> str:
        """Interpret Monte Carlo success rate."""
        if rate >= 0.80:
            return "highly_feasible"
        elif rate >= 0.60:
            return "feasible"
        elif rate >= 0.40:
            return "uncertain"
        elif rate >= 0.20:
            return "challenging"
        else:
            return "unlikely"
    
    def _generate_final_recommendation(
        self,
        engine_a_result: dict,
        engine_b_result: dict,
        conflict_report: ConflictReport,
        engine_a_prime_result: Optional[dict],
    ) -> str:
        """Generate final synthesized recommendation."""
        
        # Use revised recommendation if available
        if engine_a_prime_result and engine_a_prime_result.get("recommendation"):
            base_recommendation = engine_a_prime_result["recommendation"]
        else:
            base_recommendation = engine_a_result.get("recommendation", "")
        
        # Add quantitative caveats
        caveats = []
        
        if "monte_carlo" in engine_b_result:
            success_rate = engine_b_result["monte_carlo"].get("success_rate", 0)
            if success_rate < 0.50:
                caveats.append(f"Note: Quantitative analysis shows {success_rate:.0%} success probability.")
        
        if conflict_report.critical_conflicts:
            caveats.append(f"Warning: {len(conflict_report.critical_conflicts)} critical issues require attention.")
        
        if caveats:
            return f"{base_recommendation}\n\n{''.join(caveats)}"
        
        return base_recommendation
    
    def _generate_risk_assessment(
        self,
        engine_b_result: dict,
        conflict_report: ConflictReport,
    ) -> str:
        """Generate overall risk assessment."""
        
        risk_factors = []
        
        # Monte Carlo risk
        if "monte_carlo" in engine_b_result:
            mc = engine_b_result["monte_carlo"]
            if mc.get("success_rate", 1) < 0.30:
                risk_factors.append("LOW_FEASIBILITY")
            if mc.get("var_95", 0) < 0:
                risk_factors.append("DOWNSIDE_RISK")
        
        # Threshold risk
        if "thresholds" in engine_b_result:
            th = engine_b_result["thresholds"]
            if th.get("risk_level") == "critical":
                risk_factors.append("THRESHOLD_BREACH")
        
        # Conflict risk
        if conflict_report.alignment_score < 50:
            risk_factors.append("LOW_ALIGNMENT")
        
        # Generate assessment
        if not risk_factors:
            return "LOW - Analysis supports recommendation with high confidence"
        elif len(risk_factors) == 1:
            return f"MEDIUM - One risk factor identified: {risk_factors[0]}"
        else:
            return f"HIGH - Multiple risk factors: {', '.join(risk_factors)}"
    
    def _get_requested_services(self, compute_request: ComputeRequest) -> list[str]:
        """Get list of requested service names."""
        services = []
        if compute_request.monte_carlo:
            services.append("monte_carlo")
        if compute_request.sensitivity:
            services.append("sensitivity")
        if compute_request.optimization:
            services.append("optimization")
        if compute_request.forecasting:
            services.append("forecasting")
        if compute_request.thresholds:
            services.append("thresholds")
        if compute_request.benchmarking:
            services.append("benchmarking")
        if compute_request.correlation:
            services.append("correlation")
        return services
    
    def health_check(self) -> dict:
        """Check health of all services."""
        health = {
            "orchestrator": "healthy",
            "services": {},
        }
        
        for name, service in self.services.items():
            try:
                health["services"][name] = service.health_check()
            except Exception as e:
                health["services"][name] = {"status": "unhealthy", "error": str(e)}
                health["orchestrator"] = "degraded"
        
        return health
