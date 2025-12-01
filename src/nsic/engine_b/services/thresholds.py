"""
Threshold/Breaking Point Analysis Service
GPU Assignment: 5

Identifies critical thresholds where policy outcomes change.
Finds breaking points, tipping points, and constraint boundaries.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

# Try GPU acceleration
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    cp = np
    GPU_AVAILABLE = False

from scipy.optimize import brentq, bisect

logger = logging.getLogger(__name__)


@dataclass
class ThresholdConstraint:
    """Constraint to evaluate for threshold analysis."""
    
    # Constraint expression as Python code
    # Variables can be referenced by name
    expression: str
    
    # Threshold type
    # "upper": find where expression exceeds target
    # "lower": find where expression falls below target
    # "boundary": find where expression equals target
    threshold_type: Literal["upper", "lower", "boundary"] = "boundary"
    
    # Target value for the constraint
    target: float = 0.0
    
    # Human-readable description
    description: str = ""
    
    # Severity if breached
    severity: Literal["critical", "warning", "info"] = "warning"


@dataclass
class ThresholdInput:
    """Input specification for threshold analysis."""
    
    # Variable to sweep
    sweep_variable: str
    
    # Range to sweep
    sweep_range: tuple[float, float]
    
    # Other variables (fixed)
    fixed_variables: dict[str, float]
    
    # Constraints to evaluate
    constraints: list[ThresholdConstraint]
    
    # Resolution for sweep (number of points)
    resolution: int = 100
    
    # Precision for threshold finding
    precision: float = 1e-6
    
    # GPU ID
    gpu_id: int = 5


@dataclass
class ThresholdPoint:
    """Identified threshold/breaking point."""
    
    # Constraint that triggered
    constraint_description: str
    constraint_expression: str
    
    # Threshold value
    threshold_value: float
    
    # Type of threshold
    threshold_type: str
    
    # Value at threshold
    expression_value_at_threshold: float
    
    # Severity
    severity: str
    
    # Is the constraint currently violated?
    currently_violated: bool
    
    # Margin to threshold (how close current value is)
    margin_to_threshold: float
    margin_percent: float


@dataclass
class ThresholdResult:
    """Output from threshold analysis."""
    
    # Identified thresholds
    thresholds: list[ThresholdPoint]
    
    # Critical thresholds (immediately concerning)
    critical_thresholds: list[ThresholdPoint]
    
    # Safe operating range
    safe_range: Optional[tuple[float, float]]
    
    # Overall risk assessment
    risk_level: Literal["safe", "warning", "critical"]
    
    # Sweep data for visualization
    sweep_data: dict[str, list[float]]  # {variable: values, constraint1: values, ...}
    
    # Metadata
    n_constraints: int
    gpu_used: bool
    execution_time_ms: float


class ThresholdService:
    """
    Domain-agnostic threshold detection service.
    
    GPT-5 provides:
    - Variable to analyze (from policy parameter)
    - Range to sweep (from feasible bounds)
    - Constraints (from regulations/targets)
    
    This service computes:
    - Breaking points for each constraint
    - Safe operating range
    - Margin to nearest threshold
    """
    
    def __init__(self, gpu_id: int = 5):
        """Initialize threshold service."""
        self.gpu_id = gpu_id
        self.xp = cp if GPU_AVAILABLE else np
        
        if GPU_AVAILABLE:
            logger.info(f"ThresholdService initialized with GPU {gpu_id}")
        else:
            logger.info("ThresholdService running on CPU")
    
    def analyze(self, input_spec: ThresholdInput) -> ThresholdResult:
        """
        Analyze thresholds for given constraints.
        
        Args:
            input_spec: ThresholdInput with sweep variable and constraints
            
        Returns:
            ThresholdResult with identified thresholds
        """
        import time
        start_time = time.perf_counter()
        
        sweep_var = input_spec.sweep_variable
        sweep_min, sweep_max = input_spec.sweep_range
        
        # Generate sweep values
        sweep_values = np.linspace(sweep_min, sweep_max, input_spec.resolution)
        
        # Evaluate each constraint across sweep range
        sweep_data = {sweep_var: list(sweep_values)}
        thresholds = []
        
        for constraint in input_spec.constraints:
            # Evaluate constraint at each sweep value
            constraint_values = []
            for val in sweep_values:
                variables = {**input_spec.fixed_variables, sweep_var: val}
                result = self._evaluate_expression(constraint.expression, variables)
                constraint_values.append(result)
            
            constraint_values = np.array(constraint_values)
            sweep_data[constraint.description or constraint.expression] = list(constraint_values)
            
            # Find threshold crossing
            threshold_point = self._find_threshold(
                sweep_values,
                constraint_values,
                constraint,
                input_spec.fixed_variables,
                sweep_var,
                input_spec.precision,
            )
            
            if threshold_point:
                thresholds.append(threshold_point)
        
        # Sort by margin (most urgent first)
        thresholds.sort(key=lambda x: x.margin_percent)
        
        # Identify critical thresholds
        critical_thresholds = [t for t in thresholds if t.severity == "critical" or t.currently_violated]
        
        # Determine safe range
        safe_range = self._compute_safe_range(
            thresholds, 
            sweep_min, 
            sweep_max,
            input_spec.fixed_variables.get(sweep_var, (sweep_min + sweep_max) / 2)
        )
        
        # Determine overall risk level
        if any(t.currently_violated and t.severity == "critical" for t in thresholds):
            risk_level = "critical"
        elif any(t.currently_violated or t.margin_percent < 10 for t in thresholds):
            risk_level = "warning"
        else:
            risk_level = "safe"
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        return ThresholdResult(
            thresholds=thresholds,
            critical_thresholds=critical_thresholds,
            safe_range=safe_range,
            risk_level=risk_level,
            sweep_data=sweep_data,
            n_constraints=len(input_spec.constraints),
            gpu_used=GPU_AVAILABLE,
            execution_time_ms=execution_time_ms,
        )
    
    def _evaluate_expression(
        self,
        expression: str,
        variables: dict[str, float]
    ) -> float:
        """Safely evaluate expression with variables."""
        namespace = {**variables}
        namespace.update({
            "np": np,
            "exp": np.exp,
            "log": np.log,
            "sqrt": np.sqrt,
            "abs": abs,
            "min": min,
            "max": max,
        })
        
        try:
            return float(eval(expression, {"__builtins__": {}}, namespace))
        except Exception as e:
            logger.error(f"Expression evaluation failed: {expression} - {e}")
            return float('nan')
    
    def _find_threshold(
        self,
        sweep_values: np.ndarray,
        constraint_values: np.ndarray,
        constraint: ThresholdConstraint,
        fixed_variables: dict[str, float],
        sweep_var: str,
        precision: float,
    ) -> Optional[ThresholdPoint]:
        """Find threshold crossing for a constraint."""
        
        target = constraint.target
        
        # Compute relative values (constraint - target)
        relative_values = constraint_values - target
        
        # Find sign changes
        sign_changes = np.where(np.diff(np.sign(relative_values)))[0]
        
        if len(sign_changes) == 0:
            # No threshold crossing in range
            # Check if currently violated
            current_val = fixed_variables.get(sweep_var, sweep_values[0])
            idx = np.argmin(np.abs(sweep_values - current_val))
            current_constraint_val = constraint_values[idx]
            
            if constraint.threshold_type == "upper":
                currently_violated = current_constraint_val > target
            elif constraint.threshold_type == "lower":
                currently_violated = current_constraint_val < target
            else:
                currently_violated = False
            
            # Return info about closest approach
            min_margin_idx = np.argmin(np.abs(relative_values))
            threshold_val = sweep_values[min_margin_idx]
            margin = abs(relative_values[min_margin_idx])
            
            return ThresholdPoint(
                constraint_description=constraint.description or constraint.expression,
                constraint_expression=constraint.expression,
                threshold_value=float(threshold_val),
                threshold_type="no_crossing",
                expression_value_at_threshold=float(constraint_values[min_margin_idx]),
                severity=constraint.severity,
                currently_violated=currently_violated,
                margin_to_threshold=margin,
                margin_percent=float(margin / (abs(target) + 1e-10) * 100),
            )
        
        # Refine threshold using bisection
        crossing_idx = sign_changes[0]
        x_low, x_high = sweep_values[crossing_idx], sweep_values[crossing_idx + 1]
        
        def objective(x):
            variables = {**fixed_variables, sweep_var: x}
            return self._evaluate_expression(constraint.expression, variables) - target
        
        try:
            threshold_val = brentq(objective, x_low, x_high, xtol=precision)
        except ValueError:
            threshold_val = (x_low + x_high) / 2
        
        # Evaluate at threshold
        variables = {**fixed_variables, sweep_var: threshold_val}
        value_at_threshold = self._evaluate_expression(constraint.expression, variables)
        
        # Check current violation status
        current_val = fixed_variables.get(sweep_var, sweep_values[0])
        current_idx = np.argmin(np.abs(sweep_values - current_val))
        current_constraint_val = constraint_values[current_idx]
        
        if constraint.threshold_type == "upper":
            currently_violated = current_constraint_val > target
        elif constraint.threshold_type == "lower":
            currently_violated = current_constraint_val < target
        else:
            currently_violated = abs(current_constraint_val - target) < precision
        
        # Calculate margin
        margin = abs(current_val - threshold_val)
        range_size = abs(sweep_values[-1] - sweep_values[0])
        margin_percent = (margin / range_size * 100) if range_size > 0 else 0
        
        return ThresholdPoint(
            constraint_description=constraint.description or constraint.expression,
            constraint_expression=constraint.expression,
            threshold_value=float(threshold_val),
            threshold_type=constraint.threshold_type,
            expression_value_at_threshold=float(value_at_threshold),
            severity=constraint.severity,
            currently_violated=currently_violated,
            margin_to_threshold=float(margin),
            margin_percent=float(margin_percent),
        )
    
    def _compute_safe_range(
        self,
        thresholds: list[ThresholdPoint],
        sweep_min: float,
        sweep_max: float,
        current_value: float,
    ) -> Optional[tuple[float, float]]:
        """Compute safe operating range based on thresholds."""
        
        if not thresholds:
            return (sweep_min, sweep_max)
        
        # Find lower and upper bounds from thresholds
        lower_bound = sweep_min
        upper_bound = sweep_max
        
        for t in thresholds:
            if t.threshold_type == "no_crossing":
                continue
            
            if t.threshold_value < current_value:
                # Threshold is below current value - it's a lower bound
                lower_bound = max(lower_bound, t.threshold_value)
            else:
                # Threshold is above current value - it's an upper bound
                upper_bound = min(upper_bound, t.threshold_value)
        
        if lower_bound >= upper_bound:
            return None  # No safe range
        
        return (lower_bound, upper_bound)
    
    def health_check(self) -> dict:
        """Check service health."""
        return {
            "service": "thresholds",
            "status": "healthy",
            "gpu_available": GPU_AVAILABLE,
            "gpu_id": self.gpu_id,
        }


# Example usage
if __name__ == "__main__":
    service = ThresholdService()
    
    # Example: Qatarization threshold analysis
    input_spec = ThresholdInput(
        sweep_variable="qatarization_rate",
        sweep_range=(0.30, 0.80),
        fixed_variables={
            "qatarization_rate": 0.42,  # Current rate
            "labor_cost_multiplier": 1.2,
            "productivity_factor": 0.95,
        },
        constraints=[
            ThresholdConstraint(
                expression="qatarization_rate - 0.60",  # 60% target
                threshold_type="upper",
                target=0.0,
                description="2028 Target (60%)",
                severity="critical",
            ),
            ThresholdConstraint(
                expression="labor_cost_multiplier * qatarization_rate - 0.80",  # Cost ceiling
                threshold_type="upper",
                target=0.0,
                description="Cost ceiling breach",
                severity="warning",
            ),
        ],
        resolution=100,
    )
    
    result = service.analyze(input_spec)
    
    print(f"Risk Level: {result.risk_level}")
    print(f"Safe Range: {result.safe_range}")
    print(f"\nThresholds Found:")
    for t in result.thresholds:
        status = "VIOLATED" if t.currently_violated else f"margin: {t.margin_percent:.1f}%"
        print(f"  {t.constraint_description}: {t.threshold_value:.3f} ({status})")
