# LangGraph Multi-Agent System - Quick Start Guide

## 🚀 Getting Started

### Run the New Modular Workflow

```bash
# Set environment variable to use new workflow
$env:QNWIS_WORKFLOW_IMPL = "langgraph"  # PowerShell
# OR
export QNWIS_WORKFLOW_IMPL=langgraph    # Bash

# Run basic test (2-node fast path)
python test_langgraph_basic.py

# Run full test (all 10 nodes)
python test_langgraph_full.py
```

### Use from Python Code

```python
from qnwis.orchestration.workflow import run_intelligence_query

# Execute query
result = await run_intelligence_query(
    "What is Qatar's GDP growth from 2010 to 2024?"
)

# Access results
print(f"Complexity: {result['complexity']}")
print(f"Nodes executed: {result['nodes_executed']}")
print(f"Data quality: {result['data_quality_score']:.2f}")
print(f"Confidence: {result['confidence_score']:.2f}")
print(f"\nFinal synthesis:\n{result['final_synthesis']}")
```

### Use via Streaming API

```python
from qnwis.orchestration.streaming import run_workflow_stream

async for event in run_workflow_stream(question="Your query here"):
    print(f"{event.stage}: {event.status}")
    if event.status == "complete":
        print(f"  Latency: {event.latency_ms}ms")
        print(f"  Payload: {event.payload}")
```

---

## 🔧 Configuration

### Feature Flags

Control which workflow implementation to use:

| Environment Variable | Values | Default |
|---------------------|--------|---------|
| `QNWIS_WORKFLOW_IMPL` | `legacy`, `langgraph` | `legacy` |

### LLM Provider

Control which LLM provider nodes use:

| Environment Variable | Values | Default |
|---------------------|--------|---------|
| `QNWIS_LANGGRAPH_LLM_PROVIDER` | `anthropic`, `openai`, `stub` | `stub` |
| `QNWIS_LANGGRAPH_LLM_MODEL` | Model name | Provider default |

### Example Configuration

```bash
# .env file
QNWIS_WORKFLOW_IMPL=langgraph
QNWIS_LANGGRAPH_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## 📊 Understanding the Workflow

### Query Flow

```
User Query
    ↓
┌────────────────┐
│  Classifier    │ ← Analyzes complexity (simple/medium/complex/critical)
└────────┬───────┘
         │
┌────────▼───────┐
│  Extraction    │ ← Fetches data (cache-first <100ms + 12 APIs)
└────────┬───────┘
         │
    ┌────┴─────┐
    │          │
Simple    Medium/Complex
    │          │
    │    ┌─────▼─────┐
    │    │ Financial │ ← Financial economist analysis
    │    └─────┬─────┘
    │          │
    │    ┌─────▼─────┐
    │    │  Market   │ ← Market intelligence + GCC benchmarking
    │    └─────┬─────┘
    │          │
    │    ┌─────▼─────┐
    │    │Operations │ ← Implementation feasibility
    │    └─────┬─────┘
    │          │
    │    ┌─────▼─────┐
    │    │ Research  │ ← Semantic Scholar + academic evidence
    │    └─────┬─────┘
    │          │
    │    ┌─────▼─────┐
    │    │  Debate   │ ← Contradiction resolution
    │    └─────┬─────┘
    │          │
    │    ┌─────▼─────┐
    │    │ Critique  │ ← Devil's advocate
    │    └─────┬─────┘
    │          │
    │    ┌─────▼─────┐
    │    │Verification│ ← Fact checking + citations
    │    └─────┬─────┘
    │          │
    └────┬─────┘
         │
    ┌────▼────┐
    │Synthesis│ ← Final ministerial brief
    └────┬────┘
         │
        END
```

### Performance by Complexity

| Complexity | Nodes | Time | Use Case |
|-----------|-------|------|----------|
| **Simple** | 3 | 2-5s | "What is unemployment rate?" |
| **Medium** | 10 | 20-40s | "Analyze employment trends" |
| **Complex** | 10 | 30-60s | "Should Qatar invest $15B in..." |

---

## 🧪 Testing

### Run All Tests

```bash
# Basic workflow (fast)
python test_langgraph_basic.py

# Full workflow (comprehensive)
python test_langgraph_full.py

# Verify cache performance
python verify_cache.py
```

### Expected Output

**Basic Test (Simple Query):**
```
Complexity: simple
Nodes executed: ['classifier', 'extraction', 'synthesis']
Facts extracted: 20+
Data quality: 0.70+
Execution time: <30s
```

**Full Test (Complex Query):**
```
Complexity: medium
Nodes executed: ['classifier', 'extraction', 'financial', 'market',
                 'operations', 'research', 'debate', 'critique',
                 'verification', 'synthesis']
Facts extracted: 145+
Data quality: 0.96+
Confidence score: 0.40-0.80
```

---

## 🔍 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Which Workflow Is Active

```python
from qnwis.orchestration.feature_flags import get_workflow_implementation

print(f"Active workflow: {get_workflow_implementation()}")
# Output: "legacy" or "langgraph"
```

### Inspect State at Each Node

```python
from qnwis.orchestration.workflow import run_intelligence_query

result = await run_intelligence_query("Your query")

# Check reasoning chain
for step in result["reasoning_chain"]:
    print(f"  - {step}")

# Check nodes executed
print(f"Nodes: {result['nodes_executed']}")

# Check warnings/errors
if result["warnings"]:
    print(f"Warnings: {result['warnings']}")
if result["errors"]:
    print(f"Errors: {result['errors']}")
```

---

## 📁 File Structure

```
src/qnwis/orchestration/
├── state.py                   # State schema (IntelligenceState)
├── workflow.py                # Main workflow (10-node graph)
├── feature_flags.py           # Migration feature flags
├── streaming.py               # Streaming adapter (legacy compat)
├── nodes/                     # Modular nodes
│   ├── __init__.py           # Node exports
│   ├── README.md             # Architecture docs
│   ├── _helpers.py           # Shared utilities
│   ├── classifier.py         # Node 1: Complexity routing
│   ├── extraction.py         # Node 2: Data prefetch
│   ├── financial.py          # Node 3: Financial analysis
│   ├── market.py             # Node 4: Market intelligence
│   ├── operations.py         # Node 5: Operations feasibility
│   ├── research.py           # Node 6: Research evidence
│   ├── debate.py             # Node 7: Contradiction resolution
│   ├── critique.py           # Node 8: Devil's advocate
│   ├── verification.py       # Node 9: Fact checking
│   └── synthesis.py          # Node 10: Final synthesis
├── prefetch_apis.py           # Data prefetch (reused)
├── legendary_debate_orchestrator.py  # 6-phase debates (available)
└── graph_llm.py              # Legacy workflow (deprecated)
```

---

## 🎯 Common Use Cases

### Query Classification

```python
# Simple fact lookup
"What is Qatar's current unemployment rate?"
→ Nodes: classifier → extraction → synthesis
→ Time: 2-5s

# Medium analysis
"Analyze Qatar's employment trends over the last 5 years"
→ Nodes: All 10
→ Time: 20-40s

# Complex strategic decision
"Should Qatar invest QAR 15B in green hydrogen by 2030?"
→ Nodes: All 10 + extended debate
→ Time: 30-60s
```

### Data Source Integration

The extraction node automatically uses:
- **PostgreSQL cache**: 128 World Bank + 1 ILO indicators (<100ms)
- **IMF API**: Economic dashboard (free tier)
- **World Bank API**: 1400+ development indicators
- **GCC-STAT**: Regional labor statistics
- **Perplexity AI**: Real-time synthesis
- **Semantic Scholar**: 200M+ academic papers
- **Brave Search**: Recent news articles

### Error Recovery

The workflow gracefully handles:
- LLM timeout errors → Logs warning, continues
- Missing data → Records gap, continues
- API failures → Uses cached data, continues
- Agent failures → Stores error, continues

---

## 📚 Additional Resources

- **Node Architecture**: `src/qnwis/orchestration/nodes/README.md`
- **State Schema**: `src/qnwis/orchestration/state.py`
- **Feature Flags**: `src/qnwis/orchestration/feature_flags.py`
- **Migration Plan**: `LANGGRAPH_REFACTOR_COMPLETE.md`
- **Original Article**: `ARTICLE_QNWIS_SYSTEM.md`

---

## 🆘 Troubleshooting

### Issue: "No module named 'langgraph'"
**Solution:**
```bash
pip install langgraph>=0.0.20
```

### Issue: "ANTHROPIC_API_KEY is required"
**Solution:**
```bash
# Use stub provider for testing
$env:QNWIS_LANGGRAPH_LLM_PROVIDER = "stub"
```

### Issue: "legacy workflow still running"
**Solution:**
```bash
# Explicitly enable new workflow
$env:QNWIS_WORKFLOW_IMPL = "langgraph"
```

### Issue: Tests run but show old behavior
**Solution:**
```bash
# Clear Python cache
Remove-Item -Recurse -Force src/qnwis/orchestration/__pycache__
Remove-Item -Recurse -Force src/qnwis/orchestration/nodes/__pycache__

# Re-run test
python test_langgraph_full.py
```

---

**Last Updated:** November 22, 2025  
**Version:** 1.0.0 (Modular LangGraph Architecture)

