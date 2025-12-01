"""
Time Series Forecasting Service
GPU Assignment: 4

Provides trend forecasting and confidence intervals for policy projections.
Supports multiple methods: ETS, ARIMA, linear regression.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

# Try statsmodels for time series
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.arima.model import ARIMA
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

from scipy import stats
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)


@dataclass
class ForecastingInput:
    """Input specification for time series forecasting."""
    
    # Historical data points
    historical_values: list[float]
    
    # Time labels (optional, for display)
    time_labels: Optional[list[str]] = None
    
    # Number of periods to forecast
    forecast_horizon: int = 5
    
    # Forecasting method
    method: Literal["auto", "ets", "arima", "linear", "exponential"] = "auto"
    
    # Confidence level for intervals (e.g., 0.95 for 95%)
    confidence_level: float = 0.95
    
    # Seasonality period (for ETS/ARIMA)
    seasonal_period: Optional[int] = None
    
    # GPU ID
    gpu_id: int = 4


@dataclass
class ForecastPoint:
    """Single forecast point with confidence interval."""
    period: int
    point_forecast: float
    lower_bound: float
    upper_bound: float
    label: Optional[str] = None


@dataclass
class ForecastingResult:
    """Output from time series forecasting."""
    
    # Forecast values
    forecasts: list[ForecastPoint]
    
    # Trend analysis
    trend: Literal["increasing", "decreasing", "stable", "volatile"]
    trend_slope: float  # Annual rate of change
    
    # Historical fit metrics
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    r_squared: float
    
    # Method used
    method_used: str
    
    # Confidence bands
    confidence_level: float
    
    # Metadata
    n_historical: int
    gpu_used: bool
    execution_time_ms: float


class ForecastingService:
    """
    Domain-agnostic time series forecasting service.
    
    GPT-5 provides:
    - Historical data (from extracted time series)
    - Forecast horizon (from policy timeline)
    - Seasonality hints (from domain knowledge)
    
    This service computes:
    - Point forecasts
    - Confidence intervals
    - Trend direction and magnitude
    """
    
    def __init__(self, gpu_id: int = 4):
        """Initialize forecasting service."""
        self.gpu_id = gpu_id
        
        if STATSMODELS_AVAILABLE:
            logger.info(f"ForecastingService initialized with statsmodels support")
        else:
            logger.info("ForecastingService using scipy only (statsmodels not available)")
    
    def forecast(self, input_spec: ForecastingInput) -> ForecastingResult:
        """
        Generate time series forecast.
        
        Args:
            input_spec: ForecastingInput with historical data
            
        Returns:
            ForecastingResult with forecasts and confidence intervals
        """
        import time
        start_time = time.perf_counter()
        
        values = np.array(input_spec.historical_values)
        n_historical = len(values)
        
        # Select method
        method = input_spec.method
        if method == "auto":
            method = self._select_method(values)
        
        # Generate forecast
        if method == "ets" and STATSMODELS_AVAILABLE and n_historical >= 4:
            forecasts, fit_metrics, method_used = self._forecast_ets(
                values, input_spec.forecast_horizon, 
                input_spec.confidence_level, input_spec.seasonal_period
            )
        elif method == "arima" and STATSMODELS_AVAILABLE and n_historical >= 5:
            forecasts, fit_metrics, method_used = self._forecast_arima(
                values, input_spec.forecast_horizon, input_spec.confidence_level
            )
        elif method == "exponential":
            forecasts, fit_metrics, method_used = self._forecast_exponential(
                values, input_spec.forecast_horizon, input_spec.confidence_level
            )
        else:
            forecasts, fit_metrics, method_used = self._forecast_linear(
                values, input_spec.forecast_horizon, input_spec.confidence_level
            )
        
        # Add labels if provided
        if input_spec.time_labels:
            n_labels = len(input_spec.time_labels)
            for i, fc in enumerate(forecasts):
                fc.label = f"T+{i+1}"  # Default future labels
        
        # Analyze trend
        trend, trend_slope = self._analyze_trend(values)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        return ForecastingResult(
            forecasts=forecasts,
            trend=trend,
            trend_slope=trend_slope,
            mape=fit_metrics.get("mape", 0.0),
            rmse=fit_metrics.get("rmse", 0.0),
            r_squared=fit_metrics.get("r_squared", 0.0),
            method_used=method_used,
            confidence_level=input_spec.confidence_level,
            n_historical=n_historical,
            gpu_used=False,  # CPU-based forecasting
            execution_time_ms=execution_time_ms,
        )
    
    def _select_method(self, values: np.ndarray) -> str:
        """Automatically select best forecasting method."""
        n = len(values)
        
        if n < 3:
            return "linear"
        
        # Check for exponential growth pattern
        if np.all(values > 0):
            log_values = np.log(values)
            _, _, r_exp, _, _ = stats.linregress(range(n), log_values)
            if r_exp ** 2 > 0.8:
                return "exponential"
        
        # Check for seasonality (if enough data)
        if n >= 8 and STATSMODELS_AVAILABLE:
            return "ets"
        
        # Default to linear for short series
        return "linear"
    
    def _forecast_linear(
        self,
        values: np.ndarray,
        horizon: int,
        confidence: float
    ) -> tuple[list[ForecastPoint], dict, str]:
        """Linear trend forecast with prediction intervals."""
        n = len(values)
        x = np.arange(n)
        
        # Fit linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # Calculate residuals
        fitted = intercept + slope * x
        residuals = values - fitted
        se_residuals = np.std(residuals)
        
        # Calculate MAPE and RMSE
        mape = np.mean(np.abs(residuals / (values + 1e-10))) * 100
        rmse = np.sqrt(np.mean(residuals ** 2))
        
        # t-value for confidence interval
        t_val = stats.t.ppf((1 + confidence) / 2, n - 2)
        
        forecasts = []
        for i in range(horizon):
            future_x = n + i
            point = intercept + slope * future_x
            
            # Prediction interval (wider for future points)
            se_pred = se_residuals * np.sqrt(1 + 1/n + (future_x - x.mean())**2 / np.sum((x - x.mean())**2))
            margin = t_val * se_pred
            
            forecasts.append(ForecastPoint(
                period=i + 1,
                point_forecast=float(point),
                lower_bound=float(point - margin),
                upper_bound=float(point + margin),
            ))
        
        fit_metrics = {
            "mape": float(mape),
            "rmse": float(rmse),
            "r_squared": float(r_value ** 2),
        }
        
        return forecasts, fit_metrics, "linear"
    
    def _forecast_exponential(
        self,
        values: np.ndarray,
        horizon: int,
        confidence: float
    ) -> tuple[list[ForecastPoint], dict, str]:
        """Exponential growth forecast."""
        n = len(values)
        x = np.arange(n)
        
        # Fit exponential: y = a * exp(b * x)
        def exp_func(x, a, b):
            return a * np.exp(b * x)
        
        try:
            # Use positive values only
            values_pos = np.maximum(values, 1e-10)
            popt, pcov = curve_fit(exp_func, x, values_pos, p0=[values_pos[0], 0.1], maxfev=1000)
            a, b = popt
            
            fitted = exp_func(x, a, b)
            residuals = values_pos - fitted
            se_residuals = np.std(residuals)
            
            mape = np.mean(np.abs(residuals / values_pos)) * 100
            rmse = np.sqrt(np.mean(residuals ** 2))
            
            # R-squared
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((values_pos - np.mean(values_pos)) ** 2)
            r_squared = 1 - ss_res / (ss_tot + 1e-10)
            
            # Confidence interval
            z_val = stats.norm.ppf((1 + confidence) / 2)
            
            forecasts = []
            for i in range(horizon):
                future_x = n + i
                point = exp_func(future_x, a, b)
                
                # Simple uncertainty estimate
                margin = z_val * se_residuals * (1 + 0.1 * (i + 1))
                
                forecasts.append(ForecastPoint(
                    period=i + 1,
                    point_forecast=float(point),
                    lower_bound=float(max(0, point - margin)),
                    upper_bound=float(point + margin),
                ))
            
            fit_metrics = {"mape": float(mape), "rmse": float(rmse), "r_squared": float(r_squared)}
            return forecasts, fit_metrics, "exponential"
            
        except Exception as e:
            logger.warning(f"Exponential fit failed, falling back to linear: {e}")
            return self._forecast_linear(values, horizon, confidence)
    
    def _forecast_ets(
        self,
        values: np.ndarray,
        horizon: int,
        confidence: float,
        seasonal_period: Optional[int]
    ) -> tuple[list[ForecastPoint], dict, str]:
        """Exponential smoothing (ETS) forecast."""
        if not STATSMODELS_AVAILABLE:
            return self._forecast_linear(values, horizon, confidence)
        
        try:
            # Fit ETS model
            model = ExponentialSmoothing(
                values,
                trend='add',
                seasonal='add' if seasonal_period and len(values) >= 2 * seasonal_period else None,
                seasonal_periods=seasonal_period,
            )
            fitted_model = model.fit()
            
            # Generate forecast with confidence intervals
            forecast_result = fitted_model.forecast(horizon)
            
            # Calculate fit metrics on training data
            fitted_values = fitted_model.fittedvalues
            residuals = values - fitted_values
            mape = np.mean(np.abs(residuals / (values + 1e-10))) * 100
            rmse = np.sqrt(np.mean(residuals ** 2))
            
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - ss_res / (ss_tot + 1e-10)
            
            # Confidence interval estimate
            se = np.std(residuals)
            z_val = stats.norm.ppf((1 + confidence) / 2)
            
            forecasts = []
            for i, point in enumerate(forecast_result):
                margin = z_val * se * np.sqrt(1 + 0.1 * (i + 1))
                
                forecasts.append(ForecastPoint(
                    period=i + 1,
                    point_forecast=float(point),
                    lower_bound=float(point - margin),
                    upper_bound=float(point + margin),
                ))
            
            fit_metrics = {"mape": float(mape), "rmse": float(rmse), "r_squared": float(r_squared)}
            return forecasts, fit_metrics, "ets"
            
        except Exception as e:
            logger.warning(f"ETS fit failed, falling back to linear: {e}")
            return self._forecast_linear(values, horizon, confidence)
    
    def _forecast_arima(
        self,
        values: np.ndarray,
        horizon: int,
        confidence: float
    ) -> tuple[list[ForecastPoint], dict, str]:
        """ARIMA forecast."""
        if not STATSMODELS_AVAILABLE:
            return self._forecast_linear(values, horizon, confidence)
        
        try:
            # Simple ARIMA(1,1,1)
            model = ARIMA(values, order=(1, 1, 1))
            fitted_model = model.fit()
            
            # Forecast with confidence intervals
            forecast_result = fitted_model.get_forecast(steps=horizon)
            point_forecasts = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1 - confidence)
            
            # Fit metrics
            residuals = fitted_model.resid
            mape = np.mean(np.abs(residuals[1:] / (values[1:] + 1e-10))) * 100
            rmse = np.sqrt(np.mean(residuals ** 2))
            
            forecasts = []
            for i in range(horizon):
                forecasts.append(ForecastPoint(
                    period=i + 1,
                    point_forecast=float(point_forecasts.iloc[i]),
                    lower_bound=float(conf_int.iloc[i, 0]),
                    upper_bound=float(conf_int.iloc[i, 1]),
                ))
            
            fit_metrics = {"mape": float(mape), "rmse": float(rmse), "r_squared": 0.0}
            return forecasts, fit_metrics, "arima"
            
        except Exception as e:
            logger.warning(f"ARIMA fit failed, falling back to linear: {e}")
            return self._forecast_linear(values, horizon, confidence)
    
    def _analyze_trend(self, values: np.ndarray) -> tuple[str, float]:
        """Analyze trend direction and magnitude."""
        n = len(values)
        if n < 2:
            return "stable", 0.0
        
        x = np.arange(n)
        slope, _, r_value, _, _ = stats.linregress(x, values)
        
        # Calculate coefficient of variation
        cv = np.std(values) / (np.mean(values) + 1e-10)
        
        # Determine trend type
        if cv > 0.3 and r_value ** 2 < 0.5:
            trend = "volatile"
        elif abs(slope) < 0.01 * np.mean(np.abs(values)):
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        return trend, float(slope)
    
    def health_check(self) -> dict:
        """Check service health."""
        return {
            "service": "forecasting",
            "status": "healthy",
            "statsmodels_available": STATSMODELS_AVAILABLE,
            "gpu_id": self.gpu_id,
        }


# Example usage
if __name__ == "__main__":
    service = ForecastingService()
    
    # Example: Qatarization rate projection
    input_spec = ForecastingInput(
        historical_values=[0.35, 0.37, 0.39, 0.40, 0.42],  # 2019-2023
        time_labels=["2019", "2020", "2021", "2022", "2023"],
        forecast_horizon=5,  # Forecast to 2028
        method="auto",
        confidence_level=0.95,
    )
    
    result = service.forecast(input_spec)
    
    print(f"Trend: {result.trend} (slope: {result.trend_slope:.4f})")
    print(f"Method: {result.method_used}")
    print(f"MAPE: {result.mape:.1f}%, RMSE: {result.rmse:.4f}")
    print(f"\nForecasts (95% CI):")
    for fc in result.forecasts:
        print(f"  T+{fc.period}: {fc.point_forecast:.3f} [{fc.lower_bound:.3f}, {fc.upper_bound:.3f}]")
