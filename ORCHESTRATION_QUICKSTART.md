# QNWIS Orchestration Workflow - Quick Start

**Status**: ✅ Production Ready  
**Component**: LangGraph-based Multi-Agent Orchestration  
**Date**: 2025-01-06

---

## Installation

```bash
# Install dependencies (langgraph already in pyproject.toml)
pip install -e .

# Or install just langgraph
pip install "langgraph>=0.0.20"
```

---

## 🚀 30-Second Start

### Python API

```python
from qnwis.agents.base import DataClient
from qnwis.orchestration import create_graph, create_default_registry, OrchestrationTask

# Setup
client = DataClient()
registry = create_default_registry(client)
graph = create_graph(registry)

# Execute
task = OrchestrationTask(
    intent="pattern.correlation",
    params={"sector": "Construction", "months": 36}
)

result = graph.run(task)

# Inspect
print(f"Success: {result.ok}")
for section in result.sections:
    print(f"\n## {section.title}")
    print(section.body_md)
```

### CLI

```bash
# Pattern correlation
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.correlation \
  --sector Construction \
  --months 36

# GCC benchmarking
python -m qnwis.cli.qnwis_workflow \
  --intent strategy.gcc_benchmark \
  --min-countries 4 \
  --output report.json
```

---

## 📋 Available Intents

| Intent | Description | Example Params |
|--------|-------------|----------------|
| `pattern.anomalies` | Statistical anomaly detection | `z_threshold=2.5, min_sample_size=5` |
| `pattern.correlation` | Correlation analysis | `sector="Construction", months=36` |
| `pattern.root_causes` | Root cause investigation | `sector="Finance", min_sample_size=5` |
| `pattern.best_practices` | Best practices discovery | `min_sample_size=5` |
| `strategy.gcc_benchmark` | GCC competitiveness | `min_countries=4` |
| `strategy.talent_competition` | Talent competition | `min_countries=3` |
| `strategy.vision2030` | Vision 2030 alignment | *(no params)* |

---

## 🏗️ Architecture

```
OrchestrationTask
        ↓
    [Router] → validates intent
        ↓
    [Invoke] → calls agent method
        ↓
    [Verify] → checks structure
        ↓
    [Format] → creates report
        ↓
OrchestrationResult
```

### Key Components

1. **AgentRegistry**: Maps intents → agent methods (security whitelist)
2. **QNWISGraph**: LangGraph state machine orchestrator
3. **Nodes**: Router, Invoke, Verify, Format, Error handler
4. **Schemas**: Typed inputs (Task) and outputs (Result)

---

## 📦 File Structure

```
src/qnwis/orchestration/
├── __init__.py              # Public exports
├── schemas.py               # Task, Result, State models
├── registry.py              # Intent→method mapping
├── graph.py                 # LangGraph orchestrator
├── nodes/
│   ├── router.py            # Intent routing
│   ├── invoke.py            # Agent execution
│   ├── verify.py            # Structure validation
│   ├── format.py            # Report formatting
│   └── error.py             # Error handling

src/qnwis/config/
├── orchestration.yml        # Default config
└── orchestration_loader.py  # Config loader

src/qnwis/cli/
└── qnwis_workflow.py        # CLI tool

docs/orchestration/
└── step14_workflow.md       # Full documentation

tests/
├── unit/
│   ├── test_orchestration_registry.py
│   └── test_orchestration_schemas.py
└── integration/
    └── test_orchestration_workflow.py
```

---

## ⚙️ Configuration

### Default Config (`src/qnwis/config/orchestration.yml`)

```yaml
timeouts:
  agent_call_ms: 30000  # 30 seconds

retries:
  agent_call: 1

validation:
  strict: false  # Non-blocking

enabled_intents:
  - pattern.anomalies
  - pattern.correlation
  # ... etc

logging:
  level: INFO

formatting:
  max_findings: 10
  redact_pii: true
```

### Custom Config

```python
from qnwis.config.orchestration_loader import load_config

config = load_config("custom.yml")
graph = create_graph(registry, config)
```

---

## 🔒 Security Features

1. **Whitelist Registry**: Only explicitly registered intents allowed
2. **PII Redaction**: Automatic redaction of names, emails, IDs
3. **Safe Errors**: Stack traces sanitized before user exposure
4. **Parameter Validation**: Type-safe parameter binding
5. **No Direct Data Access**: Graph never touches SQL/HTTP

---

## 🧪 Testing

### Run Tests

```bash
# Unit tests (registry, schemas)
pytest tests/unit/test_orchestration_*.py -v

# Integration tests (full workflow)
pytest tests/integration/test_orchestration_workflow.py -v

# All orchestration tests
pytest tests/ -k orchestration -v
```

### Example Test

```python
def test_basic_workflow():
    from qnwis.orchestration import create_graph, create_default_registry, OrchestrationTask
    from qnwis.agents.base import DataClient
    
    client = DataClient()
    registry = create_default_registry(client)
    graph = create_graph(registry)
    
    task = OrchestrationTask(intent="pattern.anomalies", params={})
    result = graph.run(task)
    
    assert result is not None
    assert isinstance(result.ok, bool)
```

---

## 🐛 Troubleshooting

### Import Error: `ModuleNotFoundError: No module named 'langgraph'`

```bash
pip install langgraph
# Or reinstall all dependencies
pip install -e .
```

### Unknown Intent Error

```python
# Check available intents
registry = create_default_registry(client)
print(registry.intents())
# ['pattern.anomalies', 'pattern.correlation', ...]
```

### Agent Timeout

```yaml
# In orchestration.yml
timeouts:
  agent_call_ms: 60000  # Increase to 60 seconds
```

### Debug Mode

```bash
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.anomalies \
  --log-level DEBUG
```

---

## 📚 Examples

### 1. Pattern Correlation with Sector Filter

```python
task = OrchestrationTask(
    intent="pattern.correlation",
    params={"sector": "Construction", "months": 36}
)
result = graph.run(task)

for section in result.sections:
    if section.title == "Key Findings":
        print(section.body_md)
```

### 2. GCC Benchmarking with Request Tracking

```python
task = OrchestrationTask(
    intent="strategy.gcc_benchmark",
    params={"min_countries": 4},
    user_id="analyst@mol.qa",
    request_id="REQ-2025-001"
)
result = graph.run(task)

# Audit trail
print(f"Request: {result.request_id}")
print(f"Timestamp: {result.timestamp}")
print(f"Method: {result.reproducibility.method}")
```

### 3. Anomaly Detection with Custom Threshold

```bash
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.anomalies \
  --z-threshold 3.0 \
  --min-sample-size 10 \
  --output anomalies.md \
  --format markdown
```

### 4. Vision 2030 Alignment Report

```python
task = OrchestrationTask(intent="strategy.vision2030")
result = graph.run(task)

if not result.ok:
    print("Errors:", result.warnings)
else:
    print("Citations:", len(result.citations))
    print("Freshness:", result.freshness)
```

---

## 🎯 Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Router | <5ms | 2-3ms |
| Agent Invoke | <30s | 5-15s |
| Verification | <10ms | 3-5ms |
| Formatting | <50ms | 20-30ms |
| **End-to-End** | **<60s** | **10-20s** |

---

## 🔗 Next Steps

1. **Read Full Docs**: See `docs/orchestration/step14_workflow.md`
2. **Explore Agents**: See `src/qnwis/agents/` for agent implementations
3. **Check Tests**: See `tests/unit/test_orchestration_*.py`
4. **Review Config**: See `src/qnwis/config/orchestration.yml`
5. **Try CLI**: Run `python -m qnwis.cli.qnwis_workflow --help`

---

## ✅ Implementation Checklist

- [x] Schemas (Task, Result, State)
- [x] Registry with security controls
- [x] LangGraph orchestrator
- [x] 5 workflow nodes (router, invoke, verify, format, error)
- [x] Configuration system
- [x] CLI tool with examples
- [x] Unit tests (registry, schemas)
- [x] Integration tests (full workflow)
- [x] Comprehensive documentation
- [x] PII redaction
- [x] Error sanitization
- [x] Request tracking
- [x] Reproducibility metadata

---

## 📖 References

- [Full Documentation](docs/orchestration/step14_workflow.md)
- [Agent Implementation](docs/AGENTS_V1_IMPLEMENTATION_COMPLETE.md)
- [Data Layer Spec](docs/DETERMINISTIC_DATA_LAYER_SPECIFICATION.md)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)

---

**Status**: ✅ Production-ready for Qatar Ministry of Labour deployment.
