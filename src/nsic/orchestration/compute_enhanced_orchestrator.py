"""
Compute-Enhanced Dual Engine Orchestrator

Integrates Engine B v5.0 GPU compute services with the existing dual-engine flow:
1. Engine A (GPT-5) - Qualitative debates
2. Engine B (DeepSeek) - Broad scenario analysis  
3. Engine B Compute (NEW) - Quantitative validation

Flow:
- Engine A + Engine B (Llama) run in parallel
- Engine B Compute validates findings with Monte Carlo, Forecasting, etc.
- Conflict detector checks for A/B misalignment
- Engine A Prime runs if conflicts detected
- Final synthesis includes both qualitative + quantitative results
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

# Existing orchestrator
from .dual_engine_orchestrator import DualEngineOrchestrator, DualEngineResult

# New Engine B compute services
from ..engine_b.services.monte_carlo import MonteCarloService, MonteCarloInput
from ..engine_b.services.sensitivity import SensitivityService, SensitivityInput
from ..engine_b.services.forecasting import ForecastingService, ForecastingInput
from ..engine_b.services.thresholds import ThresholdService, ThresholdInput, ThresholdConstraint
from ..engine_b.services.benchmarking import BenchmarkingService, BenchmarkingInput, BenchmarkMetric, PeerData
from ..engine_b.services.correlation import CorrelationService, CorrelationInput
from ..engine_b.integration.conflict_detector import ConflictDetector, ConflictReport

logger = logging.getLogger(__name__)


@dataclass
class ComputeEnhancedResult:
    """Result with both qualitative and quantitative analysis."""
    
    # Original dual-engine result
    qualitative_result: Dict[str, Any]
    
    # Engine B compute results
    quantitative_result: Dict[str, Any]
    
    # Conflict analysis
    conflict_report: Optional[ConflictReport] = None
    
    # Engine A Prime result (if triggered)
    engine_a_prime_result: Optional[Dict[str, Any]] = None
    
    # Enhanced synthesis
    enhanced_synthesis: Dict[str, Any] = field(default_factory=dict)


class ComputeEnhancedOrchestrator:
    """
    Wraps DualEngineOrchestrator to add Engine B v5.0 compute services.
    
    This is the integration point that connects the new GPU compute
    services to the existing qualitative debate system.
    """
    
    def __init__(
        self,
        base_orchestrator: Optional[DualEngineOrchestrator] = None,
        engine_a_prime_callback: Optional[Callable] = None,
    ):
        """
        Initialize compute-enhanced orchestrator.
        
        Args:
            base_orchestrator: Existing dual-engine orchestrator (optional)
            engine_a_prime_callback: Callback to run Engine A Prime debate
        """
        self.base_orchestrator = base_orchestrator
        self.engine_a_prime_callback = engine_a_prime_callback
        
        # Initialize compute services
        self.monte_carlo = MonteCarloService(gpu_ids=[0, 1])
        self.sensitivity = SensitivityService(gpu_id=2)
        self.forecasting = ForecastingService(gpu_id=4)
        self.thresholds = ThresholdService(gpu_id=5)
        self.benchmarking = BenchmarkingService(gpu_id=6)
        self.correlation = CorrelationService(gpu_id=7)
        
        self.conflict_detector = ConflictDetector()
        
        logger.info("ComputeEnhancedOrchestrator initialized with Engine B v5.0 services")
    
    async def analyze_with_compute(
        self,
        question: str,
        qualitative_result: Dict[str, Any],
        extracted_data: Dict[str, Any],
        on_progress: Optional[Callable] = None,
    ) -> ComputeEnhancedResult:
        """
        Enhance qualitative analysis with quantitative compute.
        
        This is called AFTER Engine A completes its debate.
        
        Args:
            question: Original user question
            qualitative_result: Result from Engine A debate
            extracted_data: Data extracted during analysis (metrics, time series, etc.)
            on_progress: Optional progress callback
            
        Returns:
            ComputeEnhancedResult with both qualitative and quantitative analysis
        """
        def emit(stage: str, data: dict = None):
            if on_progress:
                on_progress(stage, data or {})
            logger.info(f"Compute stage: {stage}")
        
        emit("compute_start")
        
        # Run quantitative analysis based on extracted data
        quantitative_result = await self._run_compute_services(
            question, extracted_data, emit
        )
        
        emit("conflict_detection")
        
        # Check for conflicts between qualitative and quantitative results
        conflict_report = self.conflict_detector.detect_conflicts(
            qualitative_result, quantitative_result
        )
        
        emit("conflict_detected", {
            "conflicts": len(conflict_report.conflicts),
            "alignment_score": conflict_report.alignment_score,
            "should_trigger_prime": conflict_report.should_trigger_prime,
        })
        
        # Run Engine A Prime if conflicts detected
        engine_a_prime_result = None
        if conflict_report.should_trigger_prime and self.engine_a_prime_callback:
            emit("engine_a_prime_start", {
                "focus": conflict_report.prime_focus,
                "questions": conflict_report.prime_questions,
            })
            
            engine_a_prime_result = await self._run_engine_a_prime(
                qualitative_result,
                quantitative_result,
                conflict_report,
            )
            
            emit("engine_a_prime_complete")
        
        # Generate enhanced synthesis
        emit("synthesis")
        enhanced_synthesis = self._generate_enhanced_synthesis(
            question,
            qualitative_result,
            quantitative_result,
            conflict_report,
            engine_a_prime_result,
        )
        
        emit("complete")
        
        return ComputeEnhancedResult(
            qualitative_result=qualitative_result,
            quantitative_result=quantitative_result,
            conflict_report=conflict_report,
            engine_a_prime_result=engine_a_prime_result,
            enhanced_synthesis=enhanced_synthesis,
        )
    
    async def _run_compute_services(
        self,
        question: str,
        extracted_data: Dict[str, Any],
        emit: Callable,
    ) -> Dict[str, Any]:
        """Run relevant compute services based on extracted data."""
        results = {}
        
        # 1. Monte Carlo - if we have variable distributions
        if "variables" in extracted_data or "metrics" in extracted_data:
            emit("monte_carlo_start")
            try:
                # Build simulation from extracted metrics
                variables = self._build_mc_variables(extracted_data)
                if variables:
                    mc_input = MonteCarloInput(
                        variables=variables,
                        formula=extracted_data.get("formula", "sum(variables.values())"),
                        success_condition=extracted_data.get("success_condition", "result > 0"),
                        n_simulations=10000,
                        seed=42,
                    )
                    mc_result = self.monte_carlo.simulate(mc_input)
                    results["monte_carlo"] = {
                        "success_rate": mc_result.success_rate,
                        "mean_result": mc_result.mean_result,
                        "var_95": mc_result.var_95,
                        "variable_contributions": mc_result.variable_contributions,
                    }
                    emit("monte_carlo_complete", {"success_rate": mc_result.success_rate})
            except Exception as e:
                logger.warning(f"Monte Carlo failed: {e}")
        
        # 2. Forecasting - if we have time series data
        if "time_series" in extracted_data or "historical_values" in extracted_data:
            emit("forecasting_start")
            try:
                historical = extracted_data.get("time_series") or extracted_data.get("historical_values", [])
                if len(historical) >= 3:
                    fc_result = self.forecasting.forecast(ForecastingInput(
                        historical_values=historical,
                        forecast_horizon=5,
                        confidence_level=0.95,
                    ))
                    results["forecasting"] = {
                        "trend": fc_result.trend,
                        "trend_slope": fc_result.trend_slope,
                        "forecasts": [
                            {"period": f.period, "value": f.point_forecast, "lower": f.lower_bound, "upper": f.upper_bound}
                            for f in fc_result.forecasts
                        ],
                        "mape": fc_result.mape,
                    }
                    emit("forecasting_complete", {"trend": fc_result.trend})
            except Exception as e:
                logger.warning(f"Forecasting failed: {e}")
        
        # 3. Sensitivity - if we have base values
        if "base_values" in extracted_data or "parameters" in extracted_data:
            emit("sensitivity_start")
            try:
                base_values = extracted_data.get("base_values") or extracted_data.get("parameters", {})
                if base_values:
                    sens_result = self.sensitivity.analyze(SensitivityInput(
                        base_values=base_values,
                        formula=extracted_data.get("formula", "+".join(base_values.keys())),
                    ))
                    results["sensitivity"] = {
                        "top_drivers": sens_result.top_drivers,
                        "base_result": sens_result.base_result,
                    }
                    emit("sensitivity_complete", {"top_drivers": sens_result.top_drivers})
            except Exception as e:
                logger.warning(f"Sensitivity failed: {e}")
        
        # 4. Benchmarking - if we have peer data
        if "peers" in extracted_data or "gcc_data" in extracted_data:
            emit("benchmarking_start")
            try:
                peer_data = extracted_data.get("peers") or extracted_data.get("gcc_data", {})
                qatar_value = extracted_data.get("qatar_value")
                
                if peer_data and qatar_value is not None:
                    peers = [PeerData(name, val) for name, val in peer_data.items()]
                    bm_result = self.benchmarking.benchmark(BenchmarkingInput(
                        metrics=[BenchmarkMetric(
                            name=extracted_data.get("metric_name", "Primary Metric"),
                            qatar_value=qatar_value,
                            peers=peers,
                            higher_is_better=extracted_data.get("higher_is_better", True),
                        )]
                    ))
                    mb = bm_result.metric_benchmarks[0]
                    results["benchmarking"] = {
                        "qatar_rank": mb.qatar_rank,
                        "qatar_percentile": mb.qatar_percentile,
                        "peer_mean": mb.peer_mean,
                        "gap_to_mean": mb.gap_to_mean,
                        "performance": mb.performance,
                        "is_outlier": mb.is_outlier,
                        "z_score": mb.z_score,
                    }
                    emit("benchmarking_complete", {"rank": mb.qatar_rank})
            except Exception as e:
                logger.warning(f"Benchmarking failed: {e}")
        
        # 5. Thresholds - if we have targets
        if "targets" in extracted_data or "thresholds" in extracted_data:
            emit("thresholds_start")
            try:
                targets = extracted_data.get("targets") or extracted_data.get("thresholds", {})
                current_value = extracted_data.get("current_value")
                
                if targets and current_value is not None:
                    constraints = [
                        ThresholdConstraint(
                            expression=f"x - {target_val}",
                            target=0,
                            description=f"Target: {target_name}",
                            severity="warning",
                        )
                        for target_name, target_val in targets.items()
                    ]
                    
                    th_result = self.thresholds.analyze(ThresholdInput(
                        sweep_variable="x",
                        sweep_range=(current_value * 0.5, current_value * 2),
                        fixed_variables={"x": current_value},
                        constraints=constraints,
                    ))
                    results["thresholds"] = {
                        "risk_level": th_result.risk_level,
                        "safe_range": th_result.safe_range,
                        "critical_count": len(th_result.critical_thresholds),
                    }
                    emit("thresholds_complete", {"risk_level": th_result.risk_level})
            except Exception as e:
                logger.warning(f"Thresholds failed: {e}")
        
        return results
    
    def _build_mc_variables(self, extracted_data: Dict[str, Any]) -> Dict[str, Dict]:
        """Build Monte Carlo variable specifications from extracted data."""
        variables = {}
        
        # Use explicitly defined variables
        if "variables" in extracted_data:
            return extracted_data["variables"]
        
        # Build from metrics
        if "metrics" in extracted_data:
            for metric_name, metric_data in extracted_data["metrics"].items():
                if isinstance(metric_data, dict):
                    mean = metric_data.get("value") or metric_data.get("mean", 0)
                    std = metric_data.get("std") or abs(mean * 0.1)  # 10% default std
                    variables[metric_name] = {
                        "mean": mean,
                        "std": std,
                        "distribution": metric_data.get("distribution", "normal"),
                    }
                elif isinstance(metric_data, (int, float)):
                    variables[metric_name] = {
                        "mean": metric_data,
                        "std": abs(metric_data * 0.1),
                        "distribution": "normal",
                    }
        
        return variables
    
    async def _run_engine_a_prime(
        self,
        qualitative_result: Dict[str, Any],
        quantitative_result: Dict[str, Any],
        conflict_report: ConflictReport,
    ) -> Optional[Dict[str, Any]]:
        """Run Engine A Prime focused validation debate."""
        if not self.engine_a_prime_callback:
            return None
        
        try:
            context = {
                "original_recommendation": qualitative_result.get("recommendation", ""),
                "conflicts": [
                    {
                        "type": c.conflict_type,
                        "engine_a_claim": c.engine_a_claim,
                        "engine_b_finding": c.engine_b_finding,
                        "severity": c.severity.value,
                    }
                    for c in conflict_report.critical_conflicts
                ],
                "quantitative_results": quantitative_result,
            }
            
            return await self.engine_a_prime_callback(
                questions=conflict_report.prime_questions,
                context=context,
            )
        except Exception as e:
            logger.error(f"Engine A Prime failed: {e}")
            return {"error": str(e)}
    
    def _generate_enhanced_synthesis(
        self,
        question: str,
        qualitative_result: Dict[str, Any],
        quantitative_result: Dict[str, Any],
        conflict_report: ConflictReport,
        engine_a_prime_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate final synthesis combining qualitative + quantitative."""
        
        synthesis = {
            "question": question,
            "version": "compute_enhanced_v5.0",
            
            # Qualitative findings
            "qualitative": {
                "recommendation": qualitative_result.get("recommendation", ""),
                "key_findings": qualitative_result.get("key_findings", []),
                "confidence": qualitative_result.get("confidence", 0.0),
            },
            
            # Quantitative validation
            "quantitative": {},
            
            # Conflict status
            "alignment": {
                "score": conflict_report.alignment_score,
                "conflicts": len(conflict_report.conflicts),
                "critical_conflicts": len(conflict_report.critical_conflicts),
            },
            
            # Final confidence (adjusted by alignment)
            "adjusted_confidence": 0.0,
            
            # Risk assessment
            "risk_assessment": "",
        }
        
        # Add quantitative summaries
        if "monte_carlo" in quantitative_result:
            mc = quantitative_result["monte_carlo"]
            synthesis["quantitative"]["feasibility"] = {
                "success_probability": mc.get("success_rate"),
                "interpretation": self._interpret_probability(mc.get("success_rate", 0)),
            }
        
        if "forecasting" in quantitative_result:
            fc = quantitative_result["forecasting"]
            synthesis["quantitative"]["outlook"] = {
                "trend": fc.get("trend"),
                "slope": fc.get("trend_slope"),
            }
        
        if "benchmarking" in quantitative_result:
            bm = quantitative_result["benchmarking"]
            synthesis["quantitative"]["competitive_position"] = {
                "rank": bm.get("qatar_rank"),
                "performance": bm.get("performance"),
            }
        
        if "sensitivity" in quantitative_result:
            sens = quantitative_result["sensitivity"]
            synthesis["quantitative"]["key_drivers"] = sens.get("top_drivers", [])
        
        # Use revised recommendation if Engine A Prime ran
        if engine_a_prime_result and engine_a_prime_result.get("recommendation"):
            synthesis["revised_recommendation"] = engine_a_prime_result["recommendation"]
        
        # Calculate adjusted confidence
        base_conf = qualitative_result.get("confidence", 0.7)
        alignment_factor = conflict_report.alignment_score / 100
        synthesis["adjusted_confidence"] = base_conf * (0.5 + 0.5 * alignment_factor)
        
        # Risk assessment
        synthesis["risk_assessment"] = self._generate_risk_assessment(
            quantitative_result, conflict_report
        )
        
        return synthesis
    
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
    
    def _generate_risk_assessment(
        self,
        quantitative_result: Dict[str, Any],
        conflict_report: ConflictReport,
    ) -> str:
        """Generate overall risk assessment."""
        risk_factors = []
        
        if "monte_carlo" in quantitative_result:
            mc = quantitative_result["monte_carlo"]
            if mc.get("success_rate", 1) < 0.30:
                risk_factors.append("LOW_FEASIBILITY")
        
        if "thresholds" in quantitative_result:
            th = quantitative_result["thresholds"]
            if th.get("risk_level") == "critical":
                risk_factors.append("THRESHOLD_BREACH")
        
        if conflict_report.alignment_score < 50:
            risk_factors.append("LOW_ALIGNMENT")
        
        if not risk_factors:
            return "LOW - Analysis supports recommendation with high confidence"
        elif len(risk_factors) == 1:
            return f"MEDIUM - One risk factor: {risk_factors[0]}"
        else:
            return f"HIGH - Multiple risk factors: {', '.join(risk_factors)}"
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all compute services."""
        return {
            "monte_carlo": self.monte_carlo.health_check(),
            "sensitivity": self.sensitivity.health_check(),
            "forecasting": self.forecasting.health_check(),
            "thresholds": self.thresholds.health_check(),
            "benchmarking": self.benchmarking.health_check(),
            "correlation": self.correlation.health_check(),
        }


def create_compute_enhanced_orchestrator(
    base_orchestrator: Optional[DualEngineOrchestrator] = None,
    engine_a_prime_callback: Optional[Callable] = None,
) -> ComputeEnhancedOrchestrator:
    """Factory function to create compute-enhanced orchestrator."""
    return ComputeEnhancedOrchestrator(
        base_orchestrator=base_orchestrator,
        engine_a_prime_callback=engine_a_prime_callback,
    )
