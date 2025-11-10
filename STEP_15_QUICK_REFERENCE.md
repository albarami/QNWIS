# Step 15 Quick Reference: Query Classification & Routing

## Quick Start

### Natural Language Queries (NEW)
```bash
# Simple anomaly detection
qnwis workflow --query "Detect salary spikes in Healthcare"

# Multi-sector analysis
qnwis workflow --query "Compare retention in Construction and Finance"

# GCC benchmark
qnwis workflow --query "How does Qatar wage growth compare to UAE?"

# Crisis alert
qnwis workflow --query "Urgent: sudden turnover spike in Hospitality"
```

### Explicit Intent (Backward Compatible)
```bash
qnwis workflow --intent pattern.anomalies --sector Healthcare
```

## Architecture

```
Natural Language Query
         ↓
  QueryClassifier
  - Load lexicons
  - Extract entities  
  - Score intents
  - Determine complexity
         ↓
   Classification
  - intents: [...]
  - complexity: simple|medium|complex|crisis
  - entities: {sectors, metrics, time}
  - confidence: 0.0-1.0
         ↓
    Router Node
  - Filter to registered intents
  - Select primary intent
  - Determine mode
  - Generate prefetch
         ↓
  RoutingDecision
  - agents: [...]
  - mode: single|parallel|sequential
  - prefetch: [...]
         ↓
   Agent Execution
```

## Key Files

```
src/qnwis/orchestration/
├── classifier.py              # QueryClassifier implementation
├── intent_catalog.yml         # Intent patterns and keywords
├── keywords/
│   ├── sectors.txt           # 100+ sectors
│   └── metrics.txt           # 150+ metrics
├── examples/
│   └── routing_samples.jsonl # 40 test samples
├── schemas.py                # Extended types
└── nodes/
    └── router.py             # Upgraded router

tests/
├── unit/
│   ├── test_classifier.py
│   ├── test_classifier_entities.py
│   └── test_router_classification.py
└── integration/
    └── test_routing_samples.py
```

## Supported Intents

1. **pattern.anomalies** - Detect outliers, spikes, unusual patterns
2. **pattern.correlation** - Find relationships between variables
3. **pattern.root_causes** - Identify underlying drivers
4. **pattern.best_practices** - Identify high performers
5. **strategy.gcc_benchmark** - Compare Qatar to GCC countries
6. **strategy.talent_competition** - Analyze talent flows and competition
7. **strategy.vision2030** - Assess Vision 2030 alignment

## Complexity Levels

| Level | Criteria | Example |
|-------|----------|---------|
| **simple** | 1 intent, 1 sector, ≤24 months | "Retention in Finance" |
| **medium** | ≤3 intents OR 2+ datasets | "Turnover in Finance and Healthcare" |
| **complex** | ≥4 intents OR multi-sector synthesis | "Retention across 5 sectors" |
| **crisis** | Urgency + fresh horizon ≤3 months | "Urgent: spike now" |

## Entity Extraction

### Sectors
- Matches against 100+ sector terms
- Case-insensitive
- Example: "Construction and Healthcare"

### Metrics
- Matches against 150+ labour metrics
- Includes variations (e.g., "retention", "retention rate")
- Example: "salary and turnover"

### Time Horizons
- **Relative**: "last 24 months", "past 3 years"
- **Absolute**: "2020-2024", "since 2022", "in 2023"
- Converts all to months for comparison

## Programmatic API

```python
from qnwis.orchestration.schemas import OrchestrationTask
from qnwis.orchestration.graph import create_graph

# Natural language
task = OrchestrationTask(
    query_text="Which companies show unusual retention?",
    user_id="analyst@mol.gov.qa"
)

# Execute
result = graph.run(task)

# Access classification
if result.task.classification:
    print(f"Intents: {result.task.classification.intents}")
    print(f"Complexity: {result.task.classification.complexity}")
    print(f"Confidence: {result.task.classification.confidence}")
    print(f"Entities: {result.task.classification.entities}")
```

## Configuration

### Adjust Confidence Threshold
```python
# In router.py, modify:
min_confidence=0.55  # Default
min_confidence=0.70  # Stricter
min_confidence=0.40  # More lenient
```

### Add New Intent
1. Update `intent_catalog.yml`:
   ```yaml
   pattern.seasonal:
     keywords: ["seasonal", "cyclical", "quarterly"]
     sectors_hint: true
     metrics_hint: ["employment", "hiring"]
   ```
2. Update `schemas.py` Intent literal
3. Register in `registry.py`

### Extend Lexicons
- Edit `keywords/sectors.txt` - add one sector per line
- Edit `keywords/metrics.txt` - add one metric per line

## Testing

```bash
# Unit tests (65 tests)
python -m pytest tests/unit/test_classifier*.py tests/unit/test_router_classification.py -v

# Integration tests (14 tests)  
python -m pytest tests/integration/test_routing_samples.py -v

# All Step 15 tests (79 tests)
python -m pytest tests/unit/test_classifier*.py tests/unit/test_router_classification.py tests/integration/test_routing_samples.py -v
```

## Performance Characteristics

- **Classification time:** <10ms
- **Memory:** ~2MB
- **No external calls** during classification
- **Deterministic** - same query always produces same result

## Security Features

✅ PII redaction (emails, IDs)  
✅ Intent allowlist (only registered intents)  
✅ No database/HTTP access  
✅ Explainable (reasons provided)

## Troubleshooting

### Low Confidence Error
```
Classification confidence too low: 0.35 < 0.55
```
**Solution:** Make query more specific with keywords:
- Instead of: "Show retention"
- Try: "Detect unusual retention anomalies in Construction"

### No Intents Found
```
No valid intents found
```
**Solution:** Use keywords from intent_catalog.yml:
- anomaly, spike, outlier → pattern.anomalies
- correlation, relationship → pattern.correlation
- gcc, benchmark, regional → strategy.gcc_benchmark

### Wrong Intent Classified
**Solution:** Add more specific keywords to your query
- Include sector names explicitly
- Use metric names from metrics.txt
- Add intent-specific keywords

## Common Query Patterns

```bash
# Anomaly detection
--query "Detect outliers in retention"
--query "Unusual spikes in salary in Construction"

# Correlation
--query "Correlation between salary and retention"
--query "What drives high turnover?"

# GCC benchmarking
--query "Qatar vs UAE wage growth"
--query "Regional comparison of qatarization"

# Vision 2030
--query "Qatarization progress toward Vision 2030 targets"
--query "National employment goals alignment"
```

## Documentation

- Full design doc: `src/qnwis/docs/orchestration/step15_routing.md`
- Implementation summary: `STEP15_ROUTING_IMPLEMENTATION_COMPLETE.md`
- Intent catalog: `src/qnwis/orchestration/intent_catalog.yml`

## Next Steps

After Step 15, proceed to:
- **Step 16:** Multi-agent coordination & parallel execution
- **Step 17:** Result synthesis & aggregation
- **Step 18:** Crisis escalation & real-time monitoring

---

**Status:** ✅ Production Ready  
**Tests:** 79/79 Passing  
**Coverage:** >90%
