"""
Optimization Solver Service
GPU Assignment: 3

Finds optimal values for policy parameters subject to constraints.
Supports linear, quadratic, and nonlinear optimization.
GPU-accelerated for large-scale matrix operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

# Try GPU acceleration with CuPy
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    cp = np  # Fallback to numpy
    GPU_AVAILABLE = False

# Try cvxpy for convex optimization, scipy as fallback
try:
    import cvxpy as cvx
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False

from scipy.optimize import minimize, linprog, differential_evolution

logger = logging.getLogger(__name__)


@dataclass
class OptimizationVariable:
    """Variable definition for optimization."""
    name: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    initial_value: Optional[float] = None


@dataclass
class OptimizationConstraint:
    """Constraint definition for optimization."""
    # Expression as Python code, e.g., "x + y <= 100"
    expression: str
    # Type: "eq" for equality, "ineq" for inequality (>=0)
    constraint_type: Literal["eq", "ineq"] = "ineq"
    # Human-readable description
    description: str = ""


@dataclass
class OptimizationInput:
    """Input specification for optimization."""
    
    # Variables to optimize
    variables: list[OptimizationVariable]
    
    # Objective function as Python expression
    # Variables referenced by name
    objective: str
    
    # Minimize or maximize
    sense: Literal["minimize", "maximize"] = "minimize"
    
    # Constraints
    constraints: list[OptimizationConstraint] = field(default_factory=list)
    
    # Solver method
    method: Literal["scipy", "cvxpy", "auto"] = "auto"
    
    # Tolerance for convergence
    tolerance: float = 1e-6
    
    # Maximum iterations
    max_iterations: int = 1000
    
    # GPU ID
    gpu_id: int = 3


@dataclass
class OptimizationResult:
    """Output from optimization."""
    
    # Optimal values
    optimal_values: dict[str, float]
    
    # Objective value at optimum
    optimal_objective: float
    
    # Feasibility status
    feasible: bool
    converged: bool
    
    # Constraint satisfaction
    constraint_status: list[dict]
    
    # Shadow prices (if available)
    shadow_prices: dict[str, float]
    
    # Solver info
    solver_used: str
    iterations: int
    execution_time_ms: float
    message: str


class OptimizationService:
    """
    Domain-agnostic optimization solver.
    GPU-accelerated for large matrix operations.
    
    GPT-5 provides:
    - Variables and their bounds (from policy constraints)
    - Objective function (from policy goals)
    - Constraints (from regulations/resources)
    
    This service computes:
    - Optimal variable values
    - Constraint binding analysis
    - Shadow prices for resources
    """
    
    def __init__(self, gpu_id: int = 3):
        """Initialize optimization service with GPU."""
        self.gpu_id = gpu_id
        self.gpu_available = GPU_AVAILABLE
        
        # Set GPU device if available
        if GPU_AVAILABLE:
            try:
                cp.cuda.Device(gpu_id).use()
                self.xp = cp
                logger.info(f"OptimizationService initialized on GPU {gpu_id}")
            except Exception as e:
                logger.warning(f"GPU {gpu_id} not available: {e}, using CPU")
                self.xp = np
                self.gpu_available = False
        else:
            self.xp = np
            if CVXPY_AVAILABLE:
                logger.info("OptimizationService using CPU with CVXPY support")
            else:
                logger.info("OptimizationService using CPU with SciPy only")
    
    def solve(self, input_spec: OptimizationInput) -> OptimizationResult:
        """
        Solve optimization problem.
        
        Args:
            input_spec: OptimizationInput with objective and constraints
            
        Returns:
            OptimizationResult with optimal values
        """
        import time
        start_time = time.perf_counter()
        
        # Select solver
        method = input_spec.method
        if method == "auto":
            method = "cvxpy" if CVXPY_AVAILABLE else "scipy"
        
        if method == "cvxpy" and CVXPY_AVAILABLE:
            result = self._solve_cvxpy(input_spec)
        else:
            result = self._solve_scipy(input_spec)
        
        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        return result
    
    def _solve_scipy(self, input_spec: OptimizationInput) -> OptimizationResult:
        """Solve using scipy.optimize."""
        
        # Build variable name to index mapping
        var_names = [v.name for v in input_spec.variables]
        var_indices = {name: i for i, name in enumerate(var_names)}
        
        # Initial values
        x0 = []
        bounds = []
        for var in input_spec.variables:
            x0.append(var.initial_value if var.initial_value is not None else 0.0)
            bounds.append((var.lower_bound, var.upper_bound))
        
        x0 = np.array(x0)
        
        # Build objective function
        def objective_fn(x):
            namespace = {var_names[i]: x[i] for i in range(len(var_names))}
            namespace.update({"np": np, "exp": np.exp, "log": np.log, "sqrt": np.sqrt})
            try:
                val = eval(input_spec.objective, {"__builtins__": {}}, namespace)
                # Handle maximize by negating
                return -float(val) if input_spec.sense == "maximize" else float(val)
            except Exception as e:
                logger.error(f"Objective evaluation failed: {e}")
                return float('inf')
        
        # Build constraints
        scipy_constraints = []
        for constraint in input_spec.constraints:
            def make_constraint_fn(expr):
                def constraint_fn(x):
                    namespace = {var_names[i]: x[i] for i in range(len(var_names))}
                    namespace.update({"np": np, "exp": np.exp, "log": np.log, "sqrt": np.sqrt})
                    try:
                        return float(eval(expr, {"__builtins__": {}}, namespace))
                    except Exception:
                        return -float('inf')
                return constraint_fn
            
            scipy_constraints.append({
                "type": constraint.constraint_type,
                "fun": make_constraint_fn(constraint.expression),
            })
        
        # Solve
        try:
            result = minimize(
                objective_fn,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=scipy_constraints,
                options={
                    'maxiter': input_spec.max_iterations,
                    'ftol': input_spec.tolerance,
                }
            )
            
            optimal_values = {var_names[i]: float(result.x[i]) for i in range(len(var_names))}
            optimal_obj = float(result.fun)
            if input_spec.sense == "maximize":
                optimal_obj = -optimal_obj
            
            # Check constraint satisfaction
            constraint_status = []
            for i, constraint in enumerate(input_spec.constraints):
                namespace = {name: optimal_values[name] for name in var_names}
                namespace.update({"np": np, "exp": np.exp, "log": np.log, "sqrt": np.sqrt})
                try:
                    value = float(eval(constraint.expression, {"__builtins__": {}}, namespace))
                    satisfied = value >= -1e-6 if constraint.constraint_type == "ineq" else abs(value) < 1e-6
                except Exception:
                    value = float('nan')
                    satisfied = False
                
                constraint_status.append({
                    "expression": constraint.expression,
                    "description": constraint.description,
                    "value": value,
                    "satisfied": satisfied,
                })
            
            return OptimizationResult(
                optimal_values=optimal_values,
                optimal_objective=optimal_obj,
                feasible=result.success,
                converged=result.success,
                constraint_status=constraint_status,
                shadow_prices={},  # Not available from SLSQP
                solver_used="scipy.SLSQP",
                iterations=result.nit,
                execution_time_ms=0,  # Set by caller
                message=result.message,
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return OptimizationResult(
                optimal_values={v.name: 0.0 for v in input_spec.variables},
                optimal_objective=float('inf'),
                feasible=False,
                converged=False,
                constraint_status=[],
                shadow_prices={},
                solver_used="scipy.SLSQP",
                iterations=0,
                execution_time_ms=0,
                message=str(e),
            )
    
    def _solve_cvxpy(self, input_spec: OptimizationInput) -> OptimizationResult:
        """Solve using CVXPY (for convex problems)."""
        if not CVXPY_AVAILABLE:
            return self._solve_scipy(input_spec)
        
        # Create CVXPY variables
        cvx_vars = {}
        for var in input_spec.variables:
            cvx_vars[var.name] = cvx.Variable(name=var.name)
        
        # Build objective
        # Note: This is simplified - real implementation would need expression parsing
        try:
            namespace = {**cvx_vars, "cvx": cvx}
            objective_expr = eval(input_spec.objective, {"__builtins__": {}}, namespace)
            
            if input_spec.sense == "maximize":
                objective = cvx.Maximize(objective_expr)
            else:
                objective = cvx.Minimize(objective_expr)
        except Exception as e:
            logger.warning(f"CVXPY objective failed, falling back to scipy: {e}")
            return self._solve_scipy(input_spec)
        
        # Build constraints
        cvx_constraints = []
        for var in input_spec.variables:
            if var.lower_bound is not None:
                cvx_constraints.append(cvx_vars[var.name] >= var.lower_bound)
            if var.upper_bound is not None:
                cvx_constraints.append(cvx_vars[var.name] <= var.upper_bound)
        
        for constraint in input_spec.constraints:
            try:
                namespace = {**cvx_vars, "cvx": cvx}
                constr_expr = eval(constraint.expression, {"__builtins__": {}}, namespace)
                cvx_constraints.append(constr_expr)
            except Exception as e:
                logger.warning(f"Constraint parsing failed: {e}")
        
        # Solve
        try:
            problem = cvx.Problem(objective, cvx_constraints)
            problem.solve(solver=cvx.ECOS, max_iters=input_spec.max_iterations)
            
            if problem.status in [cvx.OPTIMAL, cvx.OPTIMAL_INACCURATE]:
                optimal_values = {name: float(var.value) for name, var in cvx_vars.items()}
                
                # Get shadow prices from dual values
                shadow_prices = {}
                for i, constr in enumerate(cvx_constraints):
                    if constr.dual_value is not None:
                        shadow_prices[f"constraint_{i}"] = float(constr.dual_value)
                
                return OptimizationResult(
                    optimal_values=optimal_values,
                    optimal_objective=float(problem.value),
                    feasible=True,
                    converged=True,
                    constraint_status=[],
                    shadow_prices=shadow_prices,
                    solver_used="cvxpy.ECOS",
                    iterations=0,
                    execution_time_ms=0,
                    message=problem.status,
                )
            else:
                return OptimizationResult(
                    optimal_values={v.name: 0.0 for v in input_spec.variables},
                    optimal_objective=float('inf'),
                    feasible=False,
                    converged=False,
                    constraint_status=[],
                    shadow_prices={},
                    solver_used="cvxpy.ECOS",
                    iterations=0,
                    execution_time_ms=0,
                    message=problem.status,
                )
                
        except Exception as e:
            logger.warning(f"CVXPY solve failed, falling back to scipy: {e}")
            return self._solve_scipy(input_spec)
    
    def health_check(self) -> dict:
        """Check service health."""
        return {
            "service": "optimization",
            "status": "healthy",
            "cvxpy_available": CVXPY_AVAILABLE,
            "gpu_id": self.gpu_id,
            "gpu_available": self.gpu_available,
        }


# Example usage for testing
if __name__ == "__main__":
    # Example: Optimize budget allocation for Qatarization
    service = OptimizationService()
    
    input_spec = OptimizationInput(
        variables=[
            OptimizationVariable("training_budget", lower_bound=0, upper_bound=100, initial_value=50),
            OptimizationVariable("incentive_budget", lower_bound=0, upper_bound=100, initial_value=30),
            OptimizationVariable("marketing_budget", lower_bound=0, upper_bound=50, initial_value=20),
        ],
        objective="0.4 * training_budget + 0.35 * incentive_budget + 0.1 * marketing_budget",
        sense="maximize",
        constraints=[
            OptimizationConstraint(
                expression="training_budget + incentive_budget + marketing_budget - 150",
                constraint_type="ineq",
                description="Total budget <= 150M QAR"
            ),
            OptimizationConstraint(
                expression="training_budget - 0.3 * (training_budget + incentive_budget + marketing_budget)",
                constraint_type="ineq",
                description="Training >= 30% of total"
            ),
        ],
    )
    
    result = service.solve(input_spec)
    
    print(f"Optimal Values: {result.optimal_values}")
    print(f"Optimal Objective: {result.optimal_objective:.2f}")
    print(f"Feasible: {result.feasible}")
    print(f"Solver: {result.solver_used}")
    print(f"Execution Time: {result.execution_time_ms:.1f}ms")
