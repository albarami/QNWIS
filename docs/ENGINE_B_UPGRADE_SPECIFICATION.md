# ENGINE B UPGRADE: From LLM Debates to GPU Compute

**FOR:** AI CODER  
**SCOPE:** ONLY Engine B changes + feedback loop to Engine A  
**CRITICAL:** DO NOT touch existing architecture

---

## What You Are Changing

| Change | Description |
|--------|-------------|
| **Engine B** | Replace Llama-based agents with GPU compute services |
| **Feedback Loop** | Engine B results feed back to Engine A for validation |

### DO NOT TOUCH:
- ✅ Deterministic extraction layer
- ✅ Scenario generation  
- ✅ Engine A (GPT-5 debates)
- ✅ Data APIs (LMIS, World Bank, etc.)
- ✅ Final synthesis (but will receive Engine B compute results)

---

## Architecture Overview

### Current Flow (KEEP)
```
Query → Deterministic Extraction → Scenarios → Engine A (debate) → Engine B [CHANGE] → Synthesis
```

### Engine B: Before vs After

**BEFORE (Delete):**
- Llama 3.3 70B on 8 GPUs
- 3 agents (Dr. Rashid, Dr. Noor, Dr. Hassan)  
- 24 scenarios analyzed independently
- Output: Text analysis duplicating Engine A

**AFTER (Build):**
- Pure Python/CUDA compute (NO LLM)
- 7 domain-agnostic compute services
- Mathematical validation of Engine A's recommendations
- Output: Numbers, probabilities, thresholds

---

## The 7 Compute Services

| GPU | Service | What It Computes |
|-----|---------|------------------|
| 0-1 | Monte Carlo | 10,000 simulations → probability distributions |
| 2 | Sensitivity | Parameter sweeps → tornado chart data |
| 3 | Optimization | Constrained optimization → optimal allocation |
| 4 | Forecasting | Time series → projections with confidence bands |
| 5 | Thresholds | Breaking point analysis → where policy fails |
| 6 | Benchmarking | Peer comparison → rankings, gaps |
| 7 | Correlation | Driver analysis → what causes what |

**CRITICAL:** Services are domain-agnostic. GPT-5 provides data and interprets results.

---

## New Feedback Loop

```
Engine A (150 turns)
      ↓
Engine B (compute validation)
      ↓
Compare Results
      ↓
┌─────┴─────┐
↓           ↓
CONFIRMS    CONFLICTS → Engine A Prime (30-50 turns)
↓                            ↓
└────────────────────────────┘
              ↓
       Final Synthesis
  (Qualitative + Quantitative)
```

---

## Implementation Files

Create in `src/nsic/engine_b/`:

```
engine_b/
├── __init__.py
├── api.py                    # FastAPI main app
├── services/
│   ├── __init__.py
│   ├── monte_carlo.py        # GPU 0-1
│   ├── sensitivity.py        # GPU 2
│   ├── optimization.py       # GPU 3
│   ├── forecasting.py        # GPU 4
│   ├── thresholds.py         # GPU 5
│   ├── benchmarking.py       # GPU 6
│   └── correlation.py        # GPU 7
└── integration/
    ├── __init__.py
    ├── hybrid_flow.py        # Orchestration with feedback
    └── conflict_detector.py  # Compare Engine A vs B
```

---

## Testing Strategy

### Unit Tests (Per Service)

**File:** `tests/engine_b/test_monte_carlo.py`
```python
import pytest
from src.nsic.engine_b.services.monte_carlo import MonteCarloService, MonteCarloRequest

class TestMonteCarloService:
    
    def test_basic_simulation(self):
        """Test basic Monte Carlo with normal distribution."""
        service = MonteCarloService()
        result = service.run(MonteCarloRequest(
            variables=[{"name": "x", "distribution": "normal", "mean": 100, "std": 10}],
            outcome_formula="x * 2",
            n_simulations=10000
        ))
        
        assert 195 < result.mean < 205  # Should be ~200
        assert result.n_simulations == 10000
        assert "x" in result.sensitivity
    
    def test_success_rate_calculation(self):
        """Test success rate with condition."""
        service = MonteCarloService()
        result = service.run(MonteCarloRequest(
            variables=[{"name": "x", "distribution": "uniform", "min": 0, "max": 100}],
            outcome_formula="x",
            n_simulations=10000,
            success_condition="outcome > 50"
        ))
        
        assert 0.45 < result.success_rate < 0.55  # Should be ~50%
    
    def test_qatarization_policy_scenario(self):
        """Real policy test: Qatarization feasibility."""
        service = MonteCarloService()
        result = service.run(MonteCarloRequest(
            variables=[
                {"name": "qatari_growth", "distribution": "normal", "mean": 0.021, "std": 0.005},
                {"name": "jobs_growth", "distribution": "normal", "mean": 0.043, "std": 0.01},
                {"name": "current_qataris", "distribution": "normal", "mean": 33300, "std": 1000},
                {"name": "current_jobs", "distribution": "normal", "mean": 1850000, "std": 50000}
            ],
            outcome_formula="(current_qataris * (1 + qatari_growth)**5) / (current_jobs * (1 + jobs_growth)**5) * 100",
            n_simulations=10000,
            success_condition="outcome >= 15"
        ))
        
        print(f"📊 Qatarization 2029: mean={result.mean:.2f}%")
        print(f"   P(≥15%) = {result.success_rate:.1%}")
        print(f"   95% range: [{result.p5:.2f}%, {result.p95:.2f}%]")
        print(f"   Sensitivity: {result.sensitivity}")
        
        assert result.mean > 0  # Sanity check
        assert result.success_rate is not None
```

**File:** `tests/engine_b/test_forecasting.py`
```python
import pytest
from src.nsic.engine_b.services.forecasting import ForecastService, ForecastRequest

class TestForecastService:
    
    def test_workforce_forecast(self):
        """Test forecasting Qatar workforce to 2030."""
        service = ForecastService()
        result = service.run(ForecastRequest(
            time_series=[
                {"date": "2015-01-01", "value": 1950000},
                {"date": "2016-01-01", "value": 2010000},
                {"date": "2017-01-01", "value": 2080000},
                {"date": "2018-01-01", "value": 2120000},
                {"date": "2019-01-01", "value": 2150000},
                {"date": "2020-01-01", "value": 2050000},
                {"date": "2021-01-01", "value": 2080000},
                {"date": "2022-01-01", "value": 2150000},
                {"date": "2023-01-01", "value": 2200000},
            ],
            horizon=7,
            frequency="annual"
        ))
        
        assert result.trend in ["increasing", "decreasing", "stable"]
        assert len(result.forecasts) == 7
        assert result.data_points_used == 9
        
        print(f"📈 Workforce forecast to 2030:")
        for f in result.forecasts:
            print(f"   {f.date[:4]}: {f.forecast:,.0f} [{f.lower:,.0f} - {f.upper:,.0f}]")
    
    def test_trend_detection(self):
        """Test trend detection accuracy."""
        service = ForecastService()
        
        # Clear upward trend
        result = service.run(ForecastRequest(
            time_series=[{"date": f"202{i}-01-01", "value": 100 + i*10} for i in range(5)],
            horizon=3
        ))
        assert result.trend == "increasing"
```

**File:** `tests/engine_b/test_thresholds.py`
```python
import pytest
from src.nsic.engine_b.services.thresholds import ThresholdService, ThresholdRequest, Constraint

class TestThresholdService:
    
    def test_qatarization_threshold(self):
        """Find Qatarization threshold where labor shortage occurs."""
        service = ThresholdService()
        result = service.run(ThresholdRequest(
            variable_name="qatarization_target",
            variable_range=[0.10, 0.30],
            steps=100,
            constraints=[
                Constraint(
                    name="labor_shortage",
                    condition="qatari_supply < private_jobs * qatarization_target",
                    description="Not enough Qatari workers"
                )
            ],
            context={
                "qatari_supply": 47000,
                "private_jobs": 1850000
            }
        ))
        
        threshold = result.thresholds[0]
        print(f"🚨 Qatarization Threshold:")
        print(f"   Breaks at: {threshold.threshold:.1%}")
        print(f"   Safe range: {threshold.safe_range[0]:.1%} - {threshold.safe_range[1]:.1%}")
        
        # 47000 / 1850000 = 2.54%, so threshold should be around there
        assert threshold.threshold is not None
        assert threshold.breached == True
```

**File:** `tests/engine_b/test_sensitivity.py`
```python
import pytest
from src.nsic.engine_b.services.sensitivity import SensitivityService, SensitivityRequest

class TestSensitivityService:
    
    def test_qatarization_drivers(self):
        """Test which factors drive Qatarization outcomes."""
        service = SensitivityService()
        result = service.run(SensitivityRequest(
            base_case={
                "qatari_workforce": 33300,
                "workforce_growth_rate": 0.021,
                "total_private_jobs": 1850000,
                "job_growth_rate": 0.043
            },
            outcome_formula="(qatari_workforce * (1 + workforce_growth_rate)**5) / (total_private_jobs * (1 + job_growth_rate)**5) * 100",
            vary_by=0.20,
            outcome_name="Qatarization Rate 2029 (%)"
        ))
        
        print(f"📊 Sensitivity Analysis:")
        print(f"   Base outcome: {result.base_outcome:.2f}%")
        print(f"   Top driver: {result.top_driver}")
        for s in result.sensitivity:
            print(f"   {s.rank}. {s.parameter}: ±{s.impact_pct:.1f}% impact")
        
        assert result.top_driver is not None
        assert len(result.sensitivity) == 4
```

### Integration Tests

**File:** `tests/engine_b/test_integration.py`
```python
import pytest
import httpx
import asyncio

ENGINE_B_URL = "http://localhost:8001"

class TestEngineB_Integration:
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=ENGINE_B_URL, timeout=30.0)
    
    def test_health_check(self, client):
        """Test Engine B health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "monte_carlo" in data["services"]
    
    def test_monte_carlo_api(self, client):
        """Test Monte Carlo via API."""
        response = client.post("/compute/monte_carlo", json={
            "variables": [{"name": "x", "distribution": "normal", "mean": 100, "std": 10}],
            "outcome_formula": "x * 2",
            "n_simulations": 1000
        })
        assert response.status_code == 200
        data = response.json()
        assert 190 < data["mean"] < 210
    
    def test_all_services_respond(self, client):
        """Verify all 7 services respond."""
        endpoints = [
            ("/compute/monte_carlo", {"variables": [{"name": "x", "distribution": "normal", "mean": 100, "std": 10}], "outcome_formula": "x", "n_simulations": 100}),
            ("/compute/sensitivity", {"base_case": {"x": 100, "y": 50}, "outcome_formula": "x + y", "vary_by": 0.1}),
            ("/compute/thresholds", {"variable_name": "x", "variable_range": [0, 100], "constraints": [{"name": "test", "condition": "x > 50"}], "context": {}}),
            ("/compute/benchmark", {"metric_name": "test", "qatar_value": 100, "peers": {"UAE": 90, "Saudi": 80}}),
            ("/compute/correlation", {"target": "y", "data": {"x": [1,2,3,4,5], "y": [2,4,6,8,10]}}),
        ]
        
        for endpoint, payload in endpoints:
            response = client.post(endpoint, json=payload)
            assert response.status_code == 200, f"Failed: {endpoint}"
            print(f"✅ {endpoint} working")
```

### Data Gathering Tests

**File:** `tests/engine_b/test_data_gathering.py`
```python
"""
Tests to verify Engine B can receive and process real data correctly.
"""
import pytest
from src.nsic.engine_b.services.monte_carlo import MonteCarloService, MonteCarloRequest
from src.nsic.engine_b.services.forecasting import ForecastService, ForecastRequest

class TestDataGathering:
    
    def test_historical_distribution(self):
        """Test Monte Carlo with historical data (bootstrap)."""
        service = MonteCarloService()
        
        # Historical oil prices
        result = service.run(MonteCarloRequest(
            variables=[
                {
                    "name": "oil_price",
                    "distribution": "historical",
                    "values": [65, 70, 75, 80, 85, 72, 68, 78, 82, 77]
                },
                {
                    "name": "demand_factor",
                    "distribution": "normal",
                    "mean": 1.0,
                    "std": 0.05
                }
            ],
            outcome_formula="oil_price * demand_factor * 1000000",
            n_simulations=10000
        ))
        
        # Mean should be around 75 * 1.0 * 1M = 75M
        assert 70_000_000 < result.mean < 80_000_000
        print(f"✅ Historical distribution: mean={result.mean:,.0f}")
    
    def test_forecast_with_irregular_data(self):
        """Test forecasting handles irregular dates."""
        service = ForecastService()
        
        result = service.run(ForecastRequest(
            time_series=[
                {"date": "2020-03-15", "value": 100},
                {"date": "2020-06-20", "value": 105},
                {"date": "2020-09-10", "value": 110},
                {"date": "2020-12-25", "value": 115},
                {"date": "2021-04-01", "value": 120},
            ],
            horizon=4,
            frequency="quarterly"
        ))
        
        assert len(result.forecasts) == 4
        assert result.trend == "increasing"
        print(f"✅ Irregular data handled: trend={result.trend}")
    
    def test_edge_case_zero_values(self):
        """Test services handle zero/near-zero values."""
        service = MonteCarloService()
        
        result = service.run(MonteCarloRequest(
            variables=[
                {"name": "x", "distribution": "uniform", "min": 0, "max": 10},
                {"name": "y", "distribution": "constant", "value": 0}
            ],
            outcome_formula="x + y",
            n_simulations=1000
        ))
        
        assert result.mean > 0  # x contributes
        print(f"✅ Zero values handled: mean={result.mean:.2f}")
    
    def test_large_simulation_count(self):
        """Test performance with large simulation count."""
        import time
        service = MonteCarloService()
        
        start = time.time()
        result = service.run(MonteCarloRequest(
            variables=[
                {"name": "x", "distribution": "normal", "mean": 100, "std": 20},
                {"name": "y", "distribution": "normal", "mean": 50, "std": 10},
                {"name": "z", "distribution": "uniform", "min": 0, "max": 1}
            ],
            outcome_formula="x * y * z",
            n_simulations=100000
        ))
        elapsed = time.time() - start
        
        assert elapsed < 10  # Should complete in <10 seconds
        print(f"✅ 100k simulations in {elapsed:.2f}s (GPU: {result.gpu_accelerated})")
```

### Math Accuracy Tests

**File:** `tests/engine_b/test_math_accuracy.py`
```python
"""
Tests to verify mathematical computations are accurate.
"""
import pytest
import numpy as np
from src.nsic.engine_b.services.monte_carlo import MonteCarloService, MonteCarloRequest
from src.nsic.engine_b.services.sensitivity import SensitivityService, SensitivityRequest
from src.nsic.engine_b.services.correlation import CorrelationService, CorrelationRequest

class TestMathAccuracy:
    
    def test_normal_distribution_properties(self):
        """Verify normal distribution has correct mean and std."""
        service = MonteCarloService()
        result = service.run(MonteCarloRequest(
            variables=[{"name": "x", "distribution": "normal", "mean": 100, "std": 15}],
            outcome_formula="x",
            n_simulations=100000
        ))
        
        # With 100k samples, should be very close
        assert abs(result.mean - 100) < 0.5  # Within 0.5 of expected mean
        assert abs(result.std - 15) < 0.5    # Within 0.5 of expected std
        
        # Check percentiles match normal distribution
        # P5 should be around mean - 1.645*std = 100 - 24.7 = 75.3
        assert abs(result.p5 - 75.3) < 2
        # P95 should be around mean + 1.645*std = 100 + 24.7 = 124.7
        assert abs(result.p95 - 124.7) < 2
        
        print(f"✅ Normal distribution accurate: mean={result.mean:.2f}, std={result.std:.2f}")
    
    def test_uniform_distribution_properties(self):
        """Verify uniform distribution properties."""
        service = MonteCarloService()
        result = service.run(MonteCarloRequest(
            variables=[{"name": "x", "distribution": "uniform", "min": 0, "max": 100}],
            outcome_formula="x",
            n_simulations=100000
        ))
        
        # Uniform mean = (max + min) / 2 = 50
        assert abs(result.mean - 50) < 1
        # Uniform std = (max - min) / sqrt(12) ≈ 28.87
        assert abs(result.std - 28.87) < 1
        
        print(f"✅ Uniform distribution accurate: mean={result.mean:.2f}, std={result.std:.2f}")
    
    def test_sensitivity_direction(self):
        """Verify sensitivity correctly identifies positive/negative impacts."""
        service = SensitivityService()
        
        # y = x - z, so x is positive driver, z is negative driver
        result = service.run(SensitivityRequest(
            base_case={"x": 100, "z": 50},
            outcome_formula="x - z",
            vary_by=0.20
        ))
        
        x_sens = next(s for s in result.sensitivity if s.parameter == "x")
        z_sens = next(s for s in result.sensitivity if s.parameter == "z")
        
        assert x_sens.direction == "positive"  # Higher x = higher outcome
        assert z_sens.direction == "negative"  # Higher z = lower outcome
        
        print(f"✅ Sensitivity directions correct: x={x_sens.direction}, z={z_sens.direction}")
    
    def test_correlation_perfect_linear(self):
        """Verify correlation detects perfect linear relationship."""
        service = CorrelationService()
        
        # Perfect positive correlation
        result = service.run(CorrelationRequest(
            target="y",
            data={
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10]  # y = 2x
            }
        ))
        
        x_driver = result.drivers[0]
        assert abs(x_driver.correlation - 1.0) < 0.001  # Perfect correlation
        assert x_driver.direction == "positive"
        
        print(f"✅ Perfect correlation detected: r={x_driver.correlation:.4f}")
    
    def test_correlation_negative(self):
        """Verify correlation detects negative relationship."""
        service = CorrelationService()
        
        result = service.run(CorrelationRequest(
            target="y",
            data={
                "x": [1, 2, 3, 4, 5],
                "y": [10, 8, 6, 4, 2]  # y = 12 - 2x (negative relationship)
            }
        ))
        
        x_driver = result.drivers[0]
        assert x_driver.correlation < -0.99  # Strong negative
        assert x_driver.direction == "negative"
        
        print(f"✅ Negative correlation detected: r={x_driver.correlation:.4f}")
    
    def test_success_rate_accuracy(self):
        """Verify success rate calculation is accurate."""
        service = MonteCarloService()
        
        # Uniform 0-100, condition > 75 should give ~25% success
        result = service.run(MonteCarloRequest(
            variables=[{"name": "x", "distribution": "uniform", "min": 0, "max": 100}],
            outcome_formula="x",
            n_simulations=100000,
            success_condition="outcome > 75"
        ))
        
        assert abs(result.success_rate - 0.25) < 0.02  # Within 2% of expected
        
        print(f"✅ Success rate accurate: {result.success_rate:.1%} (expected ~25%)")
```

---

## Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all Engine B tests
pytest tests/engine_b/ -v

# Run specific test file
pytest tests/engine_b/test_monte_carlo.py -v

# Run with coverage
pytest tests/engine_b/ --cov=src/nsic/engine_b --cov-report=html
```

---

## Git Workflow

```bash
# After each service
git add src/nsic/engine_b/services/monte_carlo.py tests/engine_b/test_monte_carlo.py
git commit -m "Engine B: Monte Carlo service with tests"

# After all services
git add .
git commit -m "Engine B: All 7 compute services implemented"

# After API
git add src/nsic/engine_b/api.py
git commit -m "Engine B: FastAPI application"

# After integration tests
git add tests/engine_b/test_integration.py
git commit -m "Engine B: Integration tests"

# Final commit
git add .
git commit -m "Engine B v5.0: Complete upgrade from LLM to compute services"
git push origin main
```

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Monte Carlo | Build | GPU 0-1, probability distributions |
| Sensitivity | Build | GPU 2, tornado charts |
| Optimization | Build | GPU 3, constrained solver |
| Forecasting | Build | GPU 4, time series |
| Thresholds | Build | GPU 5, breaking points |
| Benchmarking | Build | GPU 6, peer comparison |
| Correlation | Build | GPU 7, driver analysis |
| API | Build | Single FastAPI app |
| Feedback Loop | Build | Compare → Validate → Revise |
| Tests | Required | Unit + Integration + Math accuracy |

**Key Principle:** Engine B computes, GPT-5 interprets. The compute services are domain-agnostic mathematical tools.
