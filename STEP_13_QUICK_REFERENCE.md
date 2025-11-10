# Step 13: Quick Reference Guide

## 🚀 Quick Start

### Pattern Detective - Find Anomalies
```python
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent

client = DataClient()
agent = PatternDetectiveAgent(client)

# Find sectors with unusual attrition
report = agent.detect_anomalous_retention(z_threshold=2.5)
print(report.findings[0].summary)
```

### Pattern Detective - Discover Correlations
```python
# Are high qatarization sectors also high retention?
report = agent.find_correlations(method="spearman", min_correlation=0.5)
print(f"Correlation: {report.findings[0].metrics['spearman_correlation']:.3f}")
```

### National Strategy - GCC Benchmarking
```python
from src.qnwis.agents.national_strategy import NationalStrategyAgent

agent = NationalStrategyAgent(client)
report = agent.gcc_benchmark()

print(f"Qatar ranks {report.findings[0].metrics['qatar_rank']}/6 in GCC")
```

### National Strategy - Vision 2030 Tracking
```python
report = agent.vision2030_alignment()
print(f"Gap to target: {report.findings[0].metrics['gap_percentage_points']} pp")
print(f"Required growth: {report.findings[0].metrics['required_annual_growth']:.2f} pp/year")
```

---

## 📊 Method Catalog

### PatternDetectiveAgent

| Method | Purpose | Key Parameters |
|--------|---------|----------------|
| `detect_anomalous_retention()` | Find outlier sectors | `z_threshold=2.5` |
| `find_correlations()` | Discover relationships | `method="spearman"`, `min_correlation=0.5` |
| `identify_root_causes()` | Compare high vs low performers | `top_n=3` |
| `best_practices()` | Identify leaders | `metric="qatarization"`, `top_n=5` |

### NationalStrategyAgent

| Method | Purpose | Key Parameters |
|--------|---------|----------------|
| `gcc_benchmark()` | Regional ranking | `min_countries=3` |
| `talent_competition_assessment()` | Competitive pressure | `focus_metric="attrition_percent"` |
| `vision2030_alignment()` | Strategic tracking | `target_year=2030`, `current_year=2024` |

---

## 🔧 Statistical Utilities

```python
from src.qnwis.agents.utils.statistics import pearson, spearman, z_scores, winsorize

# Correlation
r = pearson([1, 2, 3, 4], [2, 4, 6, 8])  # → 1.0 (perfect)
rho = spearman([1, 2, 3, 100], [2, 4, 6, 8])  # → 0.9+ (robust to outlier)

# Anomaly detection
z = z_scores([10, 12, 14, 100])  # → [-0.76, -0.57, -0.38, 1.71]
clipped = winsorize([1, 2, 3, 4, 100], p=0.10)  # → [1, 2, 3, 4, 4]
```

---

## ✅ Testing

### Run Tests
```bash
# All Step 13 tests
pytest tests/unit/test_utils_statistics.py -v
pytest tests/unit/test_utils_derived_results.py -v
pytest tests/unit/test_agent_pattern_detective_enhanced.py -v
pytest tests/unit/test_agent_national_strategy_enhanced.py -v

# Quick verification
pytest tests/unit/test_*enhanced.py -v --tb=short
```

### Expected: 85 tests pass ✅

---

## 📁 File Structure

```
src/qnwis/agents/
├── pattern_detective.py          # Agent 4 (467 lines)
├── national_strategy.py           # Agent 5 (385 lines)
├── utils/
│   ├── statistics.py              # Pure Python stats (185 lines)
│   └── derived_results.py         # QueryResult wrapper (98 lines)
└── prompts/
    ├── pattern_detective_prompts.py
    └── national_strategy_prompts.py

tests/unit/
├── test_utils_statistics.py               # 268 lines, 30 tests
├── test_utils_derived_results.py          # 240 lines, 22 tests
├── test_agent_pattern_detective_enhanced.py   # 340 lines, 15 tests
└── test_agent_national_strategy_enhanced.py   # 380 lines, 18 tests

docs/agents/
└── step13_agents.md               # Full documentation (1,050 lines)
```

---

## 🎯 Key Principles

1. **No SQL/HTTP in agents** - Only `DataClient.run(query_id)`
2. **Every number traceable** - All metrics linked to QueryResult
3. **Computed data wrapped** - Use `make_derived_query_result()`
4. **Correlation ≠ causation** - Always acknowledged in findings
5. **Privacy first** - Aggregates only, no person_id

---

## 🔍 Troubleshooting

### "Insufficient data" warning
→ Check `min_sample_size` parameter (default 3-5)
→ Verify query returns data: `client.run("query_id")`

### Zero correlation when expected high
→ Try `method="spearman"` (more robust than Pearson)
→ Check for zero variance: all values identical?

### Query not found
→ Ensure query YAML exists in `src/qnwis/data/queries/`
→ Check `DataClient(queries_dir="...")` path

---

## 📞 Support

**Documentation:** `docs/agents/step13_agents.md`  
**Implementation Summary:** `STEP_13_IMPLEMENTATION_COMPLETE.md`  
**Tests:** `tests/unit/test_*enhanced.py`
