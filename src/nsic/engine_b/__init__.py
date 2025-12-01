"""
Engine B: GPU Compute Services
Domain-agnostic quantitative validation for Engine A recommendations.

Services:
- Monte Carlo simulation (GPU 0-1)
- Sensitivity analysis (GPU 2)
- Optimization solver (GPU 3)
- Time series forecasting (GPU 4)
- Threshold detection (GPU 5)
- Benchmarking (GPU 6)
- Correlation analysis (GPU 7)
"""

from .services.monte_carlo import MonteCarloService
from .services.sensitivity import SensitivityService
from .services.optimization import OptimizationService
from .services.forecasting import ForecastingService
from .services.thresholds import ThresholdService
from .services.benchmarking import BenchmarkingService
from .services.correlation import CorrelationService

__all__ = [
    "MonteCarloService",
    "SensitivityService", 
    "OptimizationService",
    "ForecastingService",
    "ThresholdService",
    "BenchmarkingService",
    "CorrelationService",
]

__version__ = "5.0.0"
