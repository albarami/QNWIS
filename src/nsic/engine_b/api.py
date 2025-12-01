"""
Engine B FastAPI Application
Exposes all 7 compute services as REST endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Import services
from .services.monte_carlo import MonteCarloService, MonteCarloInput, MonteCarloResult
from .services.sensitivity import SensitivityService, SensitivityInput, SensitivityResult
from .services.optimization import OptimizationService, OptimizationInput, OptimizationVariable, OptimizationConstraint
from .services.forecasting import ForecastingService, ForecastingInput, ForecastingResult
from .services.thresholds import ThresholdService, ThresholdInput, ThresholdConstraint
from .services.benchmarking import BenchmarkingService, BenchmarkingInput, BenchmarkMetric, PeerData
from .services.correlation import CorrelationService, CorrelationInput, CorrelationResult

logger = logging.getLogger(__name__)

# Global service instances
services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    logger.info("Initializing Engine B compute services...")
    
    services["monte_carlo"] = MonteCarloService(gpu_ids=[0, 1])
    services["sensitivity"] = SensitivityService(gpu_id=2)
    services["optimization"] = OptimizationService(gpu_id=3)
    services["forecasting"] = ForecastingService(gpu_id=4)
    services["thresholds"] = ThresholdService(gpu_id=5)
    services["benchmarking"] = BenchmarkingService(gpu_id=6)
    services["correlation"] = CorrelationService(gpu_id=7)
    
    logger.info("Engine B services initialized successfully")
    yield
    
    logger.info("Shutting down Engine B services...")
    services.clear()


app = FastAPI(
    title="Engine B Compute API",
    description="GPU-accelerated quantitative compute services for policy analysis",
    version="5.0.0",
    lifespan=lifespan,
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Check health of all services."""
    health = {"status": "healthy", "services": {}}
    
    for name, service in services.items():
        try:
            health["services"][name] = service.health_check()
        except Exception as e:
            health["services"][name] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"
    
    return health


# ============================================================================
# MONTE CARLO SIMULATION
# ============================================================================

class MonteCarloRequest(BaseModel):
    """Request model for Monte Carlo simulation."""
    variables: dict[str, dict] = Field(..., description="Variables with distribution params")
    formula: str = Field(..., description="Python expression to evaluate")
    success_condition: str = Field(..., description="Condition for success")
    n_simulations: int = Field(default=10000, ge=100, le=1000000)
    seed: Optional[int] = None


@app.post("/monte_carlo")
async def run_monte_carlo(request: MonteCarloRequest):
    """Run Monte Carlo simulation."""
    try:
        service = services["monte_carlo"]
        input_spec = MonteCarloInput(
            variables=request.variables,
            formula=request.formula,
            success_condition=request.success_condition,
            n_simulations=request.n_simulations,
            seed=request.seed,
        )
        result = service.simulate(input_spec)
        return asdict(result)
    except Exception as e:
        logger.error(f"Monte Carlo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SENSITIVITY ANALYSIS
# ============================================================================

class SensitivityRequest(BaseModel):
    """Request model for sensitivity analysis."""
    base_values: dict[str, float] = Field(..., description="Base parameter values")
    formula: str = Field(..., description="Python expression to evaluate")
    ranges: Optional[dict[str, dict]] = Field(default=None, description="Parameter ranges")
    n_steps: int = Field(default=10, ge=3, le=100)


@app.post("/sensitivity")
async def run_sensitivity(request: SensitivityRequest):
    """Run sensitivity analysis."""
    try:
        service = services["sensitivity"]
        input_spec = SensitivityInput(
            base_values=request.base_values,
            formula=request.formula,
            ranges=request.ranges,
            n_steps=request.n_steps,
        )
        result = service.analyze(input_spec)
        
        # Convert dataclasses to dicts
        return {
            "base_result": result.base_result,
            "parameter_impacts": [asdict(p) for p in result.parameter_impacts],
            "tornado_data": result.tornado_data,
            "top_drivers": result.top_drivers,
            "sensitivity_matrix": result.sensitivity_matrix,
            "n_parameters": result.n_parameters,
            "gpu_used": result.gpu_used,
            "execution_time_ms": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"Sensitivity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OPTIMIZATION
# ============================================================================

class OptimizationVariableRequest(BaseModel):
    """Variable for optimization."""
    name: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    initial_value: Optional[float] = None


class OptimizationConstraintRequest(BaseModel):
    """Constraint for optimization."""
    expression: str
    constraint_type: str = "ineq"
    description: str = ""


class OptimizationRequest(BaseModel):
    """Request model for optimization."""
    variables: list[OptimizationVariableRequest]
    objective: str = Field(..., description="Objective function expression")
    sense: str = Field(default="minimize", description="minimize or maximize")
    constraints: list[OptimizationConstraintRequest] = []
    method: str = "auto"
    tolerance: float = 1e-6
    max_iterations: int = 1000


@app.post("/optimization")
async def run_optimization(request: OptimizationRequest):
    """Run optimization solver."""
    try:
        service = services["optimization"]
        
        variables = [
            OptimizationVariable(
                name=v.name,
                lower_bound=v.lower_bound,
                upper_bound=v.upper_bound,
                initial_value=v.initial_value,
            )
            for v in request.variables
        ]
        
        constraints = [
            OptimizationConstraint(
                expression=c.expression,
                constraint_type=c.constraint_type,
                description=c.description,
            )
            for c in request.constraints
        ]
        
        input_spec = OptimizationInput(
            variables=variables,
            objective=request.objective,
            sense=request.sense,
            constraints=constraints,
            method=request.method,
            tolerance=request.tolerance,
            max_iterations=request.max_iterations,
        )
        
        result = service.solve(input_spec)
        return asdict(result)
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FORECASTING
# ============================================================================

class ForecastingRequest(BaseModel):
    """Request model for time series forecasting."""
    historical_values: list[float] = Field(..., min_length=2)
    time_labels: Optional[list[str]] = None
    forecast_horizon: int = Field(default=5, ge=1, le=100)
    method: str = "auto"
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    seasonal_period: Optional[int] = None


@app.post("/forecasting")
async def run_forecasting(request: ForecastingRequest):
    """Run time series forecasting."""
    try:
        service = services["forecasting"]
        input_spec = ForecastingInput(
            historical_values=request.historical_values,
            time_labels=request.time_labels,
            forecast_horizon=request.forecast_horizon,
            method=request.method,
            confidence_level=request.confidence_level,
            seasonal_period=request.seasonal_period,
        )
        result = service.forecast(input_spec)
        
        return {
            "forecasts": [asdict(f) for f in result.forecasts],
            "trend": result.trend,
            "trend_slope": result.trend_slope,
            "mape": result.mape,
            "rmse": result.rmse,
            "r_squared": result.r_squared,
            "method_used": result.method_used,
            "confidence_level": result.confidence_level,
            "n_historical": result.n_historical,
            "gpu_used": result.gpu_used,
            "execution_time_ms": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"Forecasting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# THRESHOLDS
# ============================================================================

class ThresholdConstraintRequest(BaseModel):
    """Constraint for threshold analysis."""
    expression: str
    threshold_type: str = "boundary"
    target: float = 0.0
    description: str = ""
    severity: str = "warning"


class ThresholdRequest(BaseModel):
    """Request model for threshold analysis."""
    sweep_variable: str
    sweep_range: tuple[float, float]
    fixed_variables: dict[str, float]
    constraints: list[ThresholdConstraintRequest]
    resolution: int = Field(default=100, ge=10, le=1000)
    precision: float = 1e-6


@app.post("/thresholds")
async def run_thresholds(request: ThresholdRequest):
    """Run threshold/breaking point analysis."""
    try:
        service = services["thresholds"]
        
        constraints = [
            ThresholdConstraint(
                expression=c.expression,
                threshold_type=c.threshold_type,
                target=c.target,
                description=c.description,
                severity=c.severity,
            )
            for c in request.constraints
        ]
        
        input_spec = ThresholdInput(
            sweep_variable=request.sweep_variable,
            sweep_range=request.sweep_range,
            fixed_variables=request.fixed_variables,
            constraints=constraints,
            resolution=request.resolution,
            precision=request.precision,
        )
        
        result = service.analyze(input_spec)
        
        return {
            "thresholds": [asdict(t) for t in result.thresholds],
            "critical_thresholds": [asdict(t) for t in result.critical_thresholds],
            "safe_range": result.safe_range,
            "risk_level": result.risk_level,
            "sweep_data": result.sweep_data,
            "n_constraints": result.n_constraints,
            "gpu_used": result.gpu_used,
            "execution_time_ms": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"Thresholds error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BENCHMARKING
# ============================================================================

class PeerDataRequest(BaseModel):
    """Peer data for benchmarking."""
    name: str
    value: float
    region: Optional[str] = None
    income_group: Optional[str] = None


class BenchmarkMetricRequest(BaseModel):
    """Metric for benchmarking."""
    name: str
    qatar_value: float
    peers: list[PeerDataRequest]
    higher_is_better: bool = True
    target: Optional[float] = None
    international_standard: Optional[float] = None


class BenchmarkingRequest(BaseModel):
    """Request model for benchmarking."""
    metrics: list[BenchmarkMetricRequest]
    peer_filter: Optional[str] = None


@app.post("/benchmarking")
async def run_benchmarking(request: BenchmarkingRequest):
    """Run benchmarking analysis."""
    try:
        service = services["benchmarking"]
        
        metrics = [
            BenchmarkMetric(
                name=m.name,
                qatar_value=m.qatar_value,
                peers=[PeerData(p.name, p.value, p.region, p.income_group) for p in m.peers],
                higher_is_better=m.higher_is_better,
                target=m.target,
                international_standard=m.international_standard,
            )
            for m in request.metrics
        ]
        
        input_spec = BenchmarkingInput(
            metrics=metrics,
            peer_filter=request.peer_filter,
        )
        
        result = service.benchmark(input_spec)
        
        return {
            "metric_benchmarks": [
                {
                    **asdict(mb),
                    "best_peer": asdict(mb.best_peer),
                    "worst_peer": asdict(mb.worst_peer),
                    "closest_peers": [asdict(p) for p in mb.closest_peers],
                }
                for mb in result.metric_benchmarks
            ],
            "composite_score": result.composite_score,
            "overall_rank": result.overall_rank,
            "overall_percentile": result.overall_percentile,
            "strengths": result.strengths,
            "improvement_areas": result.improvement_areas,
            "outperforms_peers": result.outperforms_peers,
            "underperforms_peers": result.underperforms_peers,
            "n_metrics": result.n_metrics,
            "n_peers": result.n_peers,
            "gpu_used": result.gpu_used,
            "execution_time_ms": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"Benchmarking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CORRELATION
# ============================================================================

class CorrelationRequest(BaseModel):
    """Request model for correlation analysis."""
    data: dict[str, list[float]] = Field(..., description="Variable data")
    target_variable: Optional[str] = None
    methods: list[str] = ["pearson", "spearman"]
    alpha: float = Field(default=0.05, ge=0.001, le=0.1)


@app.post("/correlation")
async def run_correlation(request: CorrelationRequest):
    """Run correlation analysis."""
    try:
        service = services["correlation"]
        input_spec = CorrelationInput(
            data=request.data,
            target_variable=request.target_variable,
            methods=request.methods,
            alpha=request.alpha,
        )
        result = service.analyze(input_spec)
        
        return {
            "correlation_matrix": result.correlation_matrix,
            "significant_pairs": [asdict(p) for p in result.significant_pairs],
            "all_pairs": [asdict(p) for p in result.all_pairs],
            "driver_analysis": asdict(result.driver_analysis) if result.driver_analysis else None,
            "multicollinearity_warnings": result.multicollinearity_warnings,
            "n_variables": result.n_variables,
            "n_observations": result.n_observations,
            "n_significant": result.n_significant,
            "gpu_used": result.gpu_used,
            "execution_time_ms": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"Correlation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMBINED ANALYSIS
# ============================================================================

class CombinedAnalysisRequest(BaseModel):
    """Request for running multiple analyses at once."""
    monte_carlo: Optional[MonteCarloRequest] = None
    sensitivity: Optional[SensitivityRequest] = None
    forecasting: Optional[ForecastingRequest] = None
    thresholds: Optional[ThresholdRequest] = None
    benchmarking: Optional[BenchmarkingRequest] = None
    correlation: Optional[CorrelationRequest] = None


@app.post("/analyze")
async def run_combined_analysis(request: CombinedAnalysisRequest):
    """Run multiple analyses in one request."""
    results = {}
    
    if request.monte_carlo:
        try:
            results["monte_carlo"] = await run_monte_carlo(request.monte_carlo)
        except Exception as e:
            results["monte_carlo"] = {"error": str(e)}
    
    if request.sensitivity:
        try:
            results["sensitivity"] = await run_sensitivity(request.sensitivity)
        except Exception as e:
            results["sensitivity"] = {"error": str(e)}
    
    if request.forecasting:
        try:
            results["forecasting"] = await run_forecasting(request.forecasting)
        except Exception as e:
            results["forecasting"] = {"error": str(e)}
    
    if request.thresholds:
        try:
            results["thresholds"] = await run_thresholds(request.thresholds)
        except Exception as e:
            results["thresholds"] = {"error": str(e)}
    
    if request.benchmarking:
        try:
            results["benchmarking"] = await run_benchmarking(request.benchmarking)
        except Exception as e:
            results["benchmarking"] = {"error": str(e)}
    
    if request.correlation:
        try:
            results["correlation"] = await run_correlation(request.correlation)
        except Exception as e:
            results["correlation"] = {"error": str(e)}
    
    return results


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
