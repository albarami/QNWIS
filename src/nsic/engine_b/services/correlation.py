"""
Correlation and Driver Analysis Service
GPU Assignment: 7

Identifies relationships between variables and key drivers.
Computes Pearson, Spearman, and Kendall correlations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np
from scipy import stats

# Try GPU acceleration
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    cp = np
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CorrelationInput:
    """Input specification for correlation analysis."""
    
    # Data matrix: {variable_name: [values]}
    data: dict[str, list[float]]
    
    # Target variable (for driver analysis)
    target_variable: Optional[str] = None
    
    # Correlation methods to compute
    methods: list[Literal["pearson", "spearman", "kendall"]] = field(
        default_factory=lambda: ["pearson", "spearman"]
    )
    
    # Significance level for p-values
    alpha: float = 0.05
    
    # GPU ID
    gpu_id: int = 7


@dataclass
class CorrelationPair:
    """Correlation result between two variables."""
    variable_1: str
    variable_2: str
    pearson_r: Optional[float] = None
    pearson_p: Optional[float] = None
    spearman_r: Optional[float] = None
    spearman_p: Optional[float] = None
    kendall_tau: Optional[float] = None
    kendall_p: Optional[float] = None
    is_significant: bool = False
    relationship: Literal["strong_positive", "moderate_positive", "weak_positive",
                         "none", "weak_negative", "moderate_negative", "strong_negative"] = "none"


@dataclass
class DriverAnalysis:
    """Analysis of drivers for a target variable."""
    target_variable: str
    drivers: list[dict]  # Ranked list of {variable, correlation, p_value, rank}
    top_positive_drivers: list[str]
    top_negative_drivers: list[str]
    explained_variance: float  # Approximate R² from top drivers


@dataclass
class CorrelationResult:
    """Output from correlation analysis."""
    
    # Full correlation matrix
    correlation_matrix: dict[str, dict[str, float]]
    
    # Significant correlations only
    significant_pairs: list[CorrelationPair]
    
    # All pairwise correlations
    all_pairs: list[CorrelationPair]
    
    # Driver analysis (if target specified)
    driver_analysis: Optional[DriverAnalysis]
    
    # Multicollinearity warnings
    multicollinearity_warnings: list[dict]
    
    # Summary stats
    n_variables: int
    n_observations: int
    n_significant: int
    
    # Metadata
    gpu_used: bool
    execution_time_ms: float


class CorrelationService:
    """
    Domain-agnostic correlation and driver analysis service.
    
    GPT-5 provides:
    - Variable data (from extracted time series)
    - Target variable (from policy outcome of interest)
    
    This service computes:
    - Pairwise correlations (Pearson, Spearman, Kendall)
    - Statistical significance
    - Top drivers for target variable
    - Multicollinearity detection
    """
    
    def __init__(self, gpu_id: int = 7):
        """Initialize correlation service."""
        self.gpu_id = gpu_id
        self.xp = cp if GPU_AVAILABLE else np
        
        if GPU_AVAILABLE:
            logger.info(f"CorrelationService initialized with GPU {gpu_id}")
        else:
            logger.info("CorrelationService running on CPU")
    
    def analyze(self, input_spec: CorrelationInput) -> CorrelationResult:
        """
        Run correlation analysis.
        
        Args:
            input_spec: CorrelationInput with data and methods
            
        Returns:
            CorrelationResult with correlation matrices and drivers
        """
        import time
        start_time = time.perf_counter()
        
        data = input_spec.data
        variables = list(data.keys())
        n_variables = len(variables)
        n_observations = len(next(iter(data.values()))) if data else 0
        
        # Convert to numpy arrays
        arrays = {name: np.array(values) for name, values in data.items()}
        
        # Compute pairwise correlations
        all_pairs = []
        correlation_matrix = {v: {} for v in variables}
        
        for i, var1 in enumerate(variables):
            for j, var2 in enumerate(variables):
                if i <= j:
                    pair = self._compute_correlation(
                        arrays[var1], arrays[var2],
                        var1, var2,
                        input_spec.methods,
                        input_spec.alpha
                    )
                    all_pairs.append(pair)
                    
                    # Fill matrix (symmetric)
                    r = pair.pearson_r if pair.pearson_r is not None else (
                        pair.spearman_r if pair.spearman_r is not None else 0
                    )
                    correlation_matrix[var1][var2] = r
                    correlation_matrix[var2][var1] = r
        
        # Filter significant pairs
        significant_pairs = [p for p in all_pairs if p.is_significant and p.variable_1 != p.variable_2]
        
        # Driver analysis if target specified
        driver_analysis = None
        if input_spec.target_variable and input_spec.target_variable in data:
            driver_analysis = self._analyze_drivers(
                arrays, input_spec.target_variable, input_spec.alpha
            )
        
        # Multicollinearity detection
        multicollinearity_warnings = self._detect_multicollinearity(
            significant_pairs, input_spec.target_variable
        )
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        return CorrelationResult(
            correlation_matrix=correlation_matrix,
            significant_pairs=significant_pairs,
            all_pairs=all_pairs,
            driver_analysis=driver_analysis,
            multicollinearity_warnings=multicollinearity_warnings,
            n_variables=n_variables,
            n_observations=n_observations,
            n_significant=len(significant_pairs),
            gpu_used=GPU_AVAILABLE,
            execution_time_ms=execution_time_ms,
        )
    
    def _compute_correlation(
        self,
        x: np.ndarray,
        y: np.ndarray,
        name_x: str,
        name_y: str,
        methods: list[str],
        alpha: float
    ) -> CorrelationPair:
        """Compute correlations between two variables."""
        
        # Remove NaN values
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            return CorrelationPair(variable_1=name_x, variable_2=name_y)
        
        pair = CorrelationPair(variable_1=name_x, variable_2=name_y)
        
        # Pearson correlation
        if "pearson" in methods:
            try:
                r, p = stats.pearsonr(x_clean, y_clean)
                pair.pearson_r = float(r)
                pair.pearson_p = float(p)
            except Exception:
                pass
        
        # Spearman correlation
        if "spearman" in methods:
            try:
                r, p = stats.spearmanr(x_clean, y_clean)
                pair.spearman_r = float(r)
                pair.spearman_p = float(p)
            except Exception:
                pass
        
        # Kendall correlation
        if "kendall" in methods:
            try:
                tau, p = stats.kendalltau(x_clean, y_clean)
                pair.kendall_tau = float(tau)
                pair.kendall_p = float(p)
            except Exception:
                pass
        
        # Determine significance (any method)
        p_values = [p for p in [pair.pearson_p, pair.spearman_p, pair.kendall_p] if p is not None]
        pair.is_significant = any(p < alpha for p in p_values)
        
        # Classify relationship strength
        r = pair.pearson_r or pair.spearman_r or 0
        if abs(r) >= 0.7:
            pair.relationship = "strong_positive" if r > 0 else "strong_negative"
        elif abs(r) >= 0.4:
            pair.relationship = "moderate_positive" if r > 0 else "moderate_negative"
        elif abs(r) >= 0.2:
            pair.relationship = "weak_positive" if r > 0 else "weak_negative"
        else:
            pair.relationship = "none"
        
        return pair
    
    def _analyze_drivers(
        self,
        arrays: dict[str, np.ndarray],
        target: str,
        alpha: float
    ) -> DriverAnalysis:
        """Identify top drivers for target variable."""
        
        target_arr = arrays[target]
        drivers = []
        
        for var_name, var_arr in arrays.items():
            if var_name == target:
                continue
            
            # Compute correlation with target
            mask = ~(np.isnan(target_arr) | np.isnan(var_arr))
            if np.sum(mask) < 3:
                continue
            
            try:
                r, p = stats.pearsonr(target_arr[mask], var_arr[mask])
                drivers.append({
                    "variable": var_name,
                    "correlation": float(r),
                    "p_value": float(p),
                    "is_significant": p < alpha,
                    "abs_correlation": abs(r),
                })
            except Exception:
                pass
        
        # Sort by absolute correlation
        drivers.sort(key=lambda x: x["abs_correlation"], reverse=True)
        
        # Assign ranks
        for i, driver in enumerate(drivers):
            driver["rank"] = i + 1
        
        # Identify top positive and negative drivers
        top_positive = [d["variable"] for d in drivers if d["correlation"] > 0 and d["is_significant"]][:3]
        top_negative = [d["variable"] for d in drivers if d["correlation"] < 0 and d["is_significant"]][:3]
        
        # Approximate explained variance (sum of squared correlations of top 3)
        top_correlations = [d["correlation"] for d in drivers[:3]]
        explained_variance = sum(r**2 for r in top_correlations) / max(len(top_correlations), 1)
        
        return DriverAnalysis(
            target_variable=target,
            drivers=drivers,
            top_positive_drivers=top_positive,
            top_negative_drivers=top_negative,
            explained_variance=float(explained_variance),
        )
    
    def _detect_multicollinearity(
        self,
        significant_pairs: list[CorrelationPair],
        target: Optional[str]
    ) -> list[dict]:
        """Detect multicollinearity among predictors."""
        
        warnings = []
        
        for pair in significant_pairs:
            # Skip if one variable is the target
            if target and (pair.variable_1 == target or pair.variable_2 == target):
                continue
            
            r = abs(pair.pearson_r or pair.spearman_r or 0)
            
            if r >= 0.8:
                warnings.append({
                    "variables": [pair.variable_1, pair.variable_2],
                    "correlation": r,
                    "severity": "high",
                    "message": f"High multicollinearity between {pair.variable_1} and {pair.variable_2} (r={r:.2f})"
                })
            elif r >= 0.6:
                warnings.append({
                    "variables": [pair.variable_1, pair.variable_2],
                    "correlation": r,
                    "severity": "moderate",
                    "message": f"Moderate correlation between {pair.variable_1} and {pair.variable_2} (r={r:.2f})"
                })
        
        return warnings
    
    def quick_correlation(
        self,
        x: list[float],
        y: list[float],
        method: Literal["pearson", "spearman", "kendall"] = "pearson"
    ) -> tuple[float, float]:
        """
        Quick correlation between two variables.
        
        Returns:
            (correlation, p_value)
        """
        x_arr = np.array(x)
        y_arr = np.array(y)
        
        mask = ~(np.isnan(x_arr) | np.isnan(y_arr))
        x_clean = x_arr[mask]
        y_clean = y_arr[mask]
        
        if len(x_clean) < 3:
            return (0.0, 1.0)
        
        if method == "pearson":
            return stats.pearsonr(x_clean, y_clean)
        elif method == "spearman":
            return stats.spearmanr(x_clean, y_clean)
        else:
            return stats.kendalltau(x_clean, y_clean)
    
    def health_check(self) -> dict:
        """Check service health."""
        return {
            "service": "correlation",
            "status": "healthy",
            "gpu_available": GPU_AVAILABLE,
            "gpu_id": self.gpu_id,
        }


# Example usage
if __name__ == "__main__":
    service = CorrelationService()
    
    # Example: Analyze drivers of Qatarization rate
    input_spec = CorrelationInput(
        data={
            "qatarization_rate": [0.35, 0.37, 0.39, 0.40, 0.42],
            "gdp_growth": [0.05, 0.03, 0.04, 0.02, 0.03],
            "training_investment": [100, 120, 140, 160, 180],
            "expat_population": [2.0, 2.1, 2.2, 2.3, 2.4],
            "unemployment_rate": [0.05, 0.04, 0.04, 0.03, 0.03],
        },
        target_variable="qatarization_rate",
        methods=["pearson", "spearman"],
        alpha=0.05,
    )
    
    result = service.analyze(input_spec)
    
    print(f"Correlation Matrix:")
    for var, correlations in result.correlation_matrix.items():
        print(f"  {var}: {correlations}")
    
    print(f"\nSignificant Correlations ({result.n_significant}):")
    for pair in result.significant_pairs:
        print(f"  {pair.variable_1} <-> {pair.variable_2}: r={pair.pearson_r:.3f} ({pair.relationship})")
    
    if result.driver_analysis:
        print(f"\nTop Drivers of {result.driver_analysis.target_variable}:")
        for driver in result.driver_analysis.drivers[:5]:
            print(f"  {driver['rank']}. {driver['variable']}: r={driver['correlation']:.3f} (p={driver['p_value']:.3f})")
        print(f"Explained Variance: {result.driver_analysis.explained_variance:.1%}")
    
    if result.multicollinearity_warnings:
        print(f"\nMulticollinearity Warnings:")
        for warn in result.multicollinearity_warnings:
            print(f"  {warn['message']}")
