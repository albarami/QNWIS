"""
Sensitivity Analysis Service
GPU Assignment: 2

Computes how much each input parameter affects the output.
Generates tornado chart data and identifies key drivers.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

# Try GPU acceleration, fallback to CPU
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    cp = np
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SensitivityInput:
    """Input specification for sensitivity analysis."""
    
    # Base values for each parameter: {name: base_value}
    base_values: dict[str, float]
    
    # Variation ranges: {name: {"low": float, "high": float}}
    # If not specified, defaults to ±20% of base value
    ranges: Optional[dict[str, dict]] = None
    
    # Formula as Python expression
    formula: str = ""
    
    # Number of steps for continuous sensitivity (default 10)
    n_steps: int = 10
    
    # GPU ID to use
    gpu_id: int = 2


@dataclass
class ParameterImpact:
    """Impact analysis for a single parameter."""
    name: str
    base_value: float
    low_value: float
    high_value: float
    impact_at_low: float  # Result when parameter at low
    impact_at_high: float  # Result when parameter at high
    swing: float  # Absolute difference (high - low impact)
    elasticity: float  # % change in output per % change in input
    direction: str  # "positive" or "negative" correlation


@dataclass
class SensitivityResult:
    """Output from sensitivity analysis."""
    
    # Base case result
    base_result: float
    
    # Parameter impacts sorted by swing (largest first)
    parameter_impacts: list[ParameterImpact]
    
    # Tornado chart data (ready for visualization)
    tornado_data: list[dict]
    
    # Top drivers (parameters with highest elasticity)
    top_drivers: list[str]
    
    # Sensitivity matrix (parameter x output at each step)
    sensitivity_matrix: dict[str, list[float]]
    
    # Metadata
    n_parameters: int
    gpu_used: bool
    execution_time_ms: float


class SensitivityService:
    """
    Domain-agnostic sensitivity analysis service.
    
    GPT-5 provides:
    - Base parameter values (from extracted data)
    - Variation ranges (from domain knowledge)
    - Formula to evaluate (from policy logic)
    
    This service computes:
    - Parameter-by-parameter impact
    - Tornado chart data
    - Top driver identification
    - Elasticity coefficients
    """
    
    def __init__(self, gpu_id: int = 2):
        """Initialize sensitivity service with GPU assignment."""
        self.gpu_id = gpu_id
        self.xp = cp if GPU_AVAILABLE else np
        
        if GPU_AVAILABLE:
            logger.info(f"SensitivityService initialized with GPU {gpu_id}")
        else:
            logger.info("SensitivityService running on CPU (CuPy not available)")
    
    def analyze(self, input_spec: SensitivityInput) -> SensitivityResult:
        """
        Run sensitivity analysis.
        
        Args:
            input_spec: SensitivityInput with base values and ranges
            
        Returns:
            SensitivityResult with impacts and tornado data
        """
        import time
        start_time = time.perf_counter()
        
        # Calculate base result
        base_result = self._evaluate_formula(input_spec.formula, input_spec.base_values)
        
        # Set default ranges if not provided
        ranges = input_spec.ranges or {}
        for param, base_val in input_spec.base_values.items():
            if param not in ranges:
                # Default: ±20% of base value
                margin = abs(base_val * 0.20) if base_val != 0 else 0.1
                ranges[param] = {
                    "low": base_val - margin,
                    "high": base_val + margin,
                }
        
        # Analyze each parameter
        parameter_impacts = []
        sensitivity_matrix = {}
        
        for param in input_spec.base_values:
            impact, steps = self._analyze_parameter(
                param,
                input_spec.base_values,
                ranges[param],
                input_spec.formula,
                input_spec.n_steps,
                base_result,
            )
            parameter_impacts.append(impact)
            sensitivity_matrix[param] = steps
        
        # Sort by absolute swing (descending)
        parameter_impacts.sort(key=lambda x: abs(x.swing), reverse=True)
        
        # Generate tornado chart data
        tornado_data = self._generate_tornado_data(parameter_impacts, base_result)
        
        # Identify top drivers (top 3 by elasticity)
        sorted_by_elasticity = sorted(
            parameter_impacts, 
            key=lambda x: abs(x.elasticity), 
            reverse=True
        )
        top_drivers = [p.name for p in sorted_by_elasticity[:3]]
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        return SensitivityResult(
            base_result=base_result,
            parameter_impacts=parameter_impacts,
            tornado_data=tornado_data,
            top_drivers=top_drivers,
            sensitivity_matrix=sensitivity_matrix,
            n_parameters=len(input_spec.base_values),
            gpu_used=GPU_AVAILABLE,
            execution_time_ms=execution_time_ms,
        )
    
    def _analyze_parameter(
        self,
        param_name: str,
        base_values: dict[str, float],
        param_range: dict,
        formula: str,
        n_steps: int,
        base_result: float,
    ) -> tuple[ParameterImpact, list[float]]:
        """Analyze sensitivity to a single parameter."""
        
        low_val = param_range["low"]
        high_val = param_range["high"]
        base_val = base_values[param_name]
        
        # Generate step values
        step_values = np.linspace(low_val, high_val, n_steps)
        step_results = []
        
        for step_val in step_values:
            # Create modified values
            modified = base_values.copy()
            modified[param_name] = step_val
            result = self._evaluate_formula(formula, modified)
            step_results.append(result)
        
        # Calculate impact at extremes
        impact_at_low = step_results[0]
        impact_at_high = step_results[-1]
        swing = impact_at_high - impact_at_low
        
        # Calculate elasticity (% change output / % change input)
        if base_val != 0 and base_result != 0:
            pct_change_input = (high_val - low_val) / abs(base_val)
            pct_change_output = (impact_at_high - impact_at_low) / abs(base_result)
            elasticity = pct_change_output / pct_change_input if pct_change_input != 0 else 0
        else:
            elasticity = 0.0
        
        # Determine direction
        direction = "positive" if swing > 0 else "negative" if swing < 0 else "neutral"
        
        impact = ParameterImpact(
            name=param_name,
            base_value=base_val,
            low_value=low_val,
            high_value=high_val,
            impact_at_low=impact_at_low,
            impact_at_high=impact_at_high,
            swing=swing,
            elasticity=elasticity,
            direction=direction,
        )
        
        return impact, step_results
    
    def _evaluate_formula(
        self,
        formula: str,
        values: dict[str, float]
    ) -> float:
        """Safely evaluate formula with parameter values."""
        namespace = {**values}
        namespace.update({
            "np": np,
            "exp": np.exp,
            "log": np.log,
            "sqrt": np.sqrt,
            "abs": abs,
            "min": min,
            "max": max,
            "power": np.power,
        })
        
        try:
            result = eval(formula, {"__builtins__": {}}, namespace)
            return float(result)
        except Exception as e:
            logger.error(f"Formula evaluation failed: {formula} - {e}")
            return 0.0
    
    def _generate_tornado_data(
        self,
        impacts: list[ParameterImpact],
        base_result: float
    ) -> list[dict]:
        """Generate data structure for tornado chart visualization."""
        tornado_data = []
        
        for impact in impacts:
            # Determine which side goes left/right
            left_val = min(impact.impact_at_low, impact.impact_at_high)
            right_val = max(impact.impact_at_low, impact.impact_at_high)
            
            tornado_data.append({
                "parameter": impact.name,
                "base_value": impact.base_value,
                "low_input": impact.low_value,
                "high_input": impact.high_value,
                "left_bar": left_val - base_result,  # Offset from base
                "right_bar": right_val - base_result,
                "swing": abs(impact.swing),
                "elasticity": impact.elasticity,
                "direction": impact.direction,
            })
        
        return tornado_data
    
    def one_at_a_time(
        self,
        base_values: dict[str, float],
        formula: str,
        variation_pct: float = 0.10,
    ) -> dict[str, float]:
        """
        Quick one-at-a-time sensitivity (OAT).
        Vary each parameter by ±variation_pct and return swing.
        
        Returns:
            Dict mapping parameter name to swing magnitude
        """
        base_result = self._evaluate_formula(formula, base_values)
        swings = {}
        
        for param, base_val in base_values.items():
            margin = abs(base_val * variation_pct) if base_val != 0 else variation_pct
            
            # Low case
            low_values = base_values.copy()
            low_values[param] = base_val - margin
            low_result = self._evaluate_formula(formula, low_values)
            
            # High case
            high_values = base_values.copy()
            high_values[param] = base_val + margin
            high_result = self._evaluate_formula(formula, high_values)
            
            swings[param] = abs(high_result - low_result)
        
        return swings
    
    def health_check(self) -> dict:
        """Check service health and GPU availability."""
        return {
            "service": "sensitivity",
            "status": "healthy",
            "gpu_available": GPU_AVAILABLE,
            "gpu_id": self.gpu_id,
        }


# Example usage for testing
if __name__ == "__main__":
    # Example: Qatarization policy sensitivity
    service = SensitivityService()
    
    input_spec = SensitivityInput(
        base_values={
            "current_rate": 0.42,
            "annual_growth": 0.03,
            "retention_rate": 0.85,
            "new_entrants": 5000,
        },
        ranges={
            "current_rate": {"low": 0.38, "high": 0.46},
            "annual_growth": {"low": 0.01, "high": 0.05},
            "retention_rate": {"low": 0.75, "high": 0.95},
            "new_entrants": {"low": 3000, "high": 7000},
        },
        formula="current_rate + annual_growth * 5 * retention_rate + new_entrants / 100000",
        n_steps=10,
    )
    
    result = service.analyze(input_spec)
    
    print(f"Base Result: {result.base_result:.3f}")
    print(f"\nParameter Impacts (sorted by swing):")
    for impact in result.parameter_impacts:
        print(f"  {impact.name}: swing={impact.swing:.4f}, elasticity={impact.elasticity:.2f}")
    print(f"\nTop Drivers: {result.top_drivers}")
    print(f"Execution Time: {result.execution_time_ms:.1f}ms")
