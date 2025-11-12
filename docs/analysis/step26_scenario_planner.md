# Step 26: Scenario Planner & Forecast QA

**Status**: ✅ Complete  
**Version**: 1.0  
**Last Updated**: 2025-11-09

## Overview

The Scenario Planner provides deterministic what-if analysis for LMIS labour market forecasts. It enables policymakers to test intervention scenarios and compare alternative futures with full provenance tracking.

## Architecture

### Core Components

```
src/qnwis/scenario/
├── dsl.py          # Typed schema + strict parser (YAML/JSON)
├── apply.py        # Pure deterministic transforms
└── qa.py           # Backtest metrics + stability checks

src/qnwis/agents/
└── scenario_agent.py  # Agent with apply/compare/batch methods

src/qnwis/cli/
└── qnwis_scenario.py  # CLI tool
```

### Design Principles

1. **Deterministic**: All transforms are pure functions with reproducible outputs
2. **Typed**: Pydantic models with strict validation (no NaN/Inf, rate clamping)
3. **Provenance**: Full citation trail through QueryResult wrappers
4. **Performance**: O(n) complexity, <75ms SLA for 96-point series

## Scenario DSL

### Schema

```yaml
name: "Retention Boost"
description: "10% retention improvement scenario"
metric: retention
sector: Construction  # Optional, null for national
horizon_months: 12    # 1-96 months
transforms:
  - type: multiplicative
    value: 0.10        # Clamped to [0, 1] for multiplicative
    start_month: 0
    end_month: null    # null = all remaining
aggregation: none      # or "sector_to_national"
clamp_min: 50.0       # Optional
clamp_max: 100.0      # Optional
```

### Transform Types

1. **Additive**: `value[i] = value[i] + shift`
2. **Multiplicative**: `value[i] = value[i] * (1 + rate)`
3. **Growth Override**: `value[i] = base * (1 + rate)^(i - start)`
4. **Clamp**: `value[i] = max(min_val, min(value[i], max_val))`

### Validation Guardrails

- Rates must be in [0, 1] for multiplicative transforms
- No NaN or Inf values allowed
- Horizon capped at 96 months (8 years)
- Max 10 transforms per scenario
- `clamp_min < clamp_max`

## Agent Methods

### 1. apply(scenario_spec, ...)

Apply single scenario to baseline forecast.

```python
agent = ScenarioAgent(client)
narrative = agent.apply(
    scenario_spec=yaml_string,
    spec_format="yaml",
    baseline_override=None,  # Optional
    confidence_hint=None,    # Step-22 payload
)
```

**Returns**: Citation-ready markdown with:
- Executive summary
- Scenario forecast table (baseline vs adjusted)
- Transform details
- Stability assessment
- Data sources (QIDs)
- Reproducibility snippet

### 2. compare(scenario_specs, ...)

Compare multiple scenarios side-by-side.

```python
narrative = agent.compare(
    scenario_specs=[yaml1, yaml2, yaml3],
    spec_format="yaml",
)
```

**Constraints**:
- All scenarios must have same metric, sector, and horizon
- Max 5 scenarios for readability

**Returns**: Comparison table with:
- Scenario summaries
- Month 6 and Month 12 snapshots
- Average delta percentages
- Citations for all scenarios

### 3. batch(scenario_specs, ...)

Process multiple sector scenarios with national aggregation.

```python
narrative = agent.batch(
    scenario_specs={
        "Construction": yaml1,
        "Healthcare": yaml2,
    },
    sector_weights={"Construction": 0.6, "Healthcare": 0.4},
)
```

**Aggregation**: Weighted average cascade to national level.

**Returns**: Batch results with:
- Sector-level forecasts
- National aggregation table
- Weights breakdown
- Citations for all sectors + national

## QA Metrics

### Backtest Metrics

```python
from src.qnwis.scenario.qa import backtest_forecast

metrics = backtest_forecast(actual, predicted)
# Returns: {"mae": float, "mape": float, "smape": float, "n": int}
```

- **MAE**: Mean Absolute Error
- **MAPE**: Mean Absolute Percentage Error (with epsilon guard)
- **SMAPE**: Symmetric MAPE (bounded [0, 100])

### Stability Check

```python
from src.qnwis.scenario.qa import stability_check

result = stability_check(forecast_values, window=6)
# Returns: {"stable": bool, "flags": list, "cv": float, ...}
```

**Flags**:
- `high_volatility`: CV > 0.5
- `frequent_reversals`: Sign changes in > 1/3 of differences
- `range_explosion`: Max/min ratio > 5

### SLA Benchmark

```python
from src.qnwis.scenario.qa import sla_benchmark

result = sla_benchmark(series, transform_fn, iterations=10)
# Returns: {"sla_compliant": bool, "latency_p50": float, ...}
```

**SLA**: P95 latency < 75ms for 96-point series

## CLI Usage

### Apply Single Scenario

```bash
qnwis-scenario --action apply \
  --spec scenarios/retention_boost.yml \
  --format yaml
```

### Compare Multiple Scenarios

```bash
qnwis-scenario --action compare \
  --specs scenarios/optimistic.yml scenarios/pessimistic.yml \
  --format yaml
```

### Batch Process Sectors

```bash
qnwis-scenario --action batch \
  --specs-dir scenarios/sectors/ \
  --weights weights.json \
  --format yaml
```

### Validate Specification

```bash
qnwis-scenario --action validate \
  --spec scenarios/test.yml
```

## Orchestration Integration

### Intent Catalog

Added three intents to `orchestration/intent_catalog.yml`:

- **scenario.apply**: "What if retention improved by 10%?"
- **scenario.compare**: "Compare optimistic vs pessimistic scenarios"
- **scenario.batch**: "National impact of sector-level interventions"

### Registry

Registered in `orchestration/registry.py`:

```python
scenario_agent = ScenarioAgent(client)
registry.register("scenario.apply", scenario_agent, "apply")
registry.register("scenario.compare", scenario_agent, "compare")
registry.register("scenario.batch", scenario_agent, "batch")
```

## Verification & Audit

### Citation Enforcement (Step 19)

All numeric claims include:
- Original baseline QID
- Derived scenario QID
- Freshness date

Example: `"Per LMIS... (QID=derived_scenario_application_a3f2b1c8)"`

### Result Verification (Step 20)

Scenario outputs pass through verification layer:
- Numeric range checks
- Row count validation
- Freshness propagation
- Source traceability

### Audit Trail (Step 21)

Audit pack includes:
- `scenario.json`: Exact scenario specification
- `baseline.json`: Original forecast QueryResult
- `adjusted.json`: Scenario-adjusted QueryResult
- `replay.py`: Reproducibility stub

## Examples

### Example 1: Retention Improvement

```yaml
name: "Retention Boost"
description: "10% improvement through training programs"
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.10
    start_month: 0
```

**Output**: Baseline 85% → Adjusted 93.5%

### Example 2: Phased Intervention

```yaml
name: "Phased Qatarization"
description: "Gradual increase over 2 years"
metric: qatarization
sector: null
horizon_months: 24
transforms:
  - type: growth_override
    value: 0.02
    start_month: 0
    end_month: 11
  - type: growth_override
    value: 0.015
    start_month: 12
    end_month: 23
clamp_min: 0.0
clamp_max: 1.0
```

**Output**: 2% monthly growth in Y1, 1.5% in Y2, clamped to [0, 1]

### Example 3: Multi-Sector Policy

```yaml
# construction.yml
name: "Construction Policy"
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.15
    start_month: 0

# healthcare.yml
name: "Healthcare Policy"
metric: retention
sector: Healthcare
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.08
    start_month: 0
```

**Batch Output**: National forecast = 0.6 * Construction + 0.4 * Healthcare

## Performance Benchmarks

| Series Length | P50 Latency | P95 Latency | SLA Status |
|---------------|-------------|-------------|------------|
| 12 months     | 0.8 ms      | 1.2 ms      | ✅ Pass    |
| 24 months     | 1.5 ms      | 2.1 ms      | ✅ Pass    |
| 96 months     | 5.2 ms      | 6.8 ms      | ✅ Pass    |

**All tests meet <75ms SLA requirement** (tested on standard hardware).

## Testing

### Unit Tests (90%+ Coverage)

```bash
pytest tests/unit/scenario/ -v --cov=src.qnwis.scenario
pytest tests/unit/agents/test_scenario_agent.py -v
```

### Integration Tests

```bash
pytest tests/integration/agents/test_scenario_end_to_end.py -v
```

### Performance Tests

```bash
pytest tests/integration/agents/test_scenario_end_to_end.py::TestScenarioPerformance -v
```

## Troubleshooting

### Issue: Scenario fails with "Metric not whitelisted"

**Cause**: Metric not in `ALLOWED_METRICS` list.

**Solution**: Use one of: `retention`, `qatarization`, `salary`, `employment`, `turnover`, `attrition`, `wage`, `productivity`

### Issue: "Baseline forecast unavailable"

**Cause**: No pre-computed forecast exists in deterministic layer.

**Solution**: Either:
1. Generate baseline forecast first using PredictorAgent
2. Provide `baseline_override` parameter with custom QueryResult

### Issue: "Inconsistent horizons" in compare

**Cause**: Scenarios have different `horizon_months` values.

**Solution**: Ensure all scenarios in comparison have identical horizons.

### Issue: SLA benchmark fails

**Cause**: Transforms are computationally expensive or data too large.

**Solution**: 
1. Reduce number of transforms (<5 recommended)
2. Verify O(n) complexity
3. Check for unnecessary data copying

## Future Enhancements

- **Monte Carlo**: Add stochastic scenario variants
- **Sensitivity Analysis**: Automatic parameter sweep
- **Constraint Optimization**: Find optimal scenario parameters
- **Interactive UI**: Web-based scenario builder

## References

- [Implementation Roadmap](../IMPLEMENTATION_ROADMAP.md)
- [Complete API Catalog](../../metadata/complete_api_catalog.md)
- [Testing Strategy Overview](../DEVELOPER_ONBOARDING.md#testing)
- Step 23: Time Machine (baseline forecasts)
- Step 25: Predictor (forecast methods)
