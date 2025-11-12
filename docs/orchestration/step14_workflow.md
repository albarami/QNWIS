# QNWIS Orchestration Workflow - Step 14

**Status**: ✓ Complete  
**Date**: 2025-01-06  
**Component**: LangGraph-based Orchestration System

---

## Overview

The QNWIS Orchestration Workflow is a LangGraph-based system that routes analytical tasks to specialized agents, validates outputs, and formats consistent reports. The system enforces deterministic data access, security controls, and PII redaction while maintaining full observability.

### Key Principles

1. **Deterministic Access**: Graph never issues SQL/HTTP directly—all data access via agents
2. **Security**: Whitelist-based registry prevents arbitrary method execution
3. **PII Safety**: Automatic redaction of sensitive information
4. **Observability**: Structured logging with execution metrics
5. **Idempotency**: Same task → same output (data unchanged)
6. **Graceful Degradation**: Missing data produces warnings, not crashes

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     QNWIS Orchestration                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│  │ Router  │───▶│ Invoke  │───▶│ Verify  │               │
│  └─────────┘    └─────────┘    └─────────┘               │
│       │              │              │                      │
│       │              │              ▼                      │
│       │              │         ┌─────────┐                │
│       │              │         │ Format  │                │
│       │              │         └─────────┘                │
│       │              │              │                      │
│       │              │              ▼                      │
│       │              │         ┌─────────────┐            │
│       │              │         │   Result    │            │
│       │              │         └─────────────┘            │
│       │              │                                     │
│       ▼              ▼                                     │
│  ┌──────────────────────────────┐                        │
│  │       Error Handler          │                        │
│  └──────────────────────────────┘                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant Graph
    participant Router
    participant Registry
    participant Agent
    participant DataClient
    participant Verify
    participant Format

    Client->>Graph: OrchestrationTask
    Graph->>Router: route_intent()
    Router->>Registry: validate intent
    Registry-->>Router: agent, method
    Router-->>Graph: route resolved
    
    Graph->>Agent: invoke method(params)
    Agent->>DataClient: run(query_id)
    DataClient-->>Agent: QueryResult
    Agent-->>Graph: AgentReport
    
    Graph->>Verify: verify_structure()
    Verify-->>Graph: validated
    
    Graph->>Format: format_report()
    Format-->>Graph: OrchestrationResult
    
    Graph-->>Client: OrchestrationResult
```

---

## Components

### 1. Schemas (`schemas.py`)

#### OrchestrationTask

Input task specification:

```python
task = OrchestrationTask(
    intent="pattern.correlation",
    params={
        "sector": "Construction",
        "months": 36
    },
    user_id="analyst [at] mol.qa",
    request_id="req-20250106-001"
)
```

**Supported Intents**:
- `pattern.anomalies` - Statistical anomaly detection
- `pattern.correlation` - Correlation analysis
- `pattern.root_causes` - Root cause investigation
- `pattern.best_practices` - Best practices discovery
- `strategy.gcc_benchmark` - GCC competitiveness benchmarking
- `strategy.talent_competition` - Talent competition assessment
- `strategy.vision2030` - Vision 2030 alignment tracking

#### OrchestrationResult

Structured output with mandatory sections:

```python
result = OrchestrationResult(
    ok=True,
    intent="pattern.correlation",
    sections=[
        ReportSection(title="Executive Summary", body_md="..."),
        ReportSection(title="Key Findings", body_md="..."),
        ReportSection(title="Evidence", body_md="..."),
    ],
    citations=[...],
    freshness={...},
    reproducibility=Reproducibility(...),
    warnings=[],
    request_id="req-20250106-001",
    timestamp="2025-01-06T10:30:00Z"
)
```

### 2. Registry (`registry.py`)

Secure intent-to-method mapping:

```python
from qnwis.orchestration.registry import AgentRegistry, create_default_registry

# Create registry
registry = create_default_registry(client)

# Check registration
assert registry.is_registered("pattern.correlation")

# Resolve intent
agent, method = registry.resolve("pattern.correlation")
callable_method = registry.get_method("pattern.correlation")
```

**Security Features**:
- Explicit registration required
- No reflective attribute access
- Method existence verification
- Callable validation

### 3. Graph (`graph.py`)

LangGraph state machine orchestrator:

```python
from qnwis.orchestration.graph import create_graph

# Create and build graph
graph = create_graph(registry, config)

# Execute workflow
result = graph.run(task)
```

**Conditional Routing**:
- Error state → Error handler
- Success path → Router → Invoke → Verify → Format
- Any node can transition to Error handler

### 4. Nodes

#### Router (`nodes/router.py`)

Validates intent and resolves routing:

```python
def route_intent(state, registry):
    # Validates intent is registered
    # Returns updated state with route or error
```

#### Invoke (`nodes/invoke.py`)

Executes agent method with safe parameter binding:

```python
def invoke_agent(state, registry, timeout_ms):
    # Inspects method signature
    # Binds only valid parameters
    # Tracks execution time
```

**Parameter Safety**:
- Signature inspection
- Type-safe binding
- Default value handling
- Required parameter validation

#### Verify (`nodes/verify.py`)

Lightweight structural validation:

```python
def verify_structure(state, strict=False):
    # Checks AgentReport structure
    # Validates evidence presence
    # Non-blocking by default
```

**Validation Checks**:
- AgentReport type
- Findings presence
- Evidence with query_id
- Citation completeness

#### Format (`nodes/format.py`)

Creates uniform, PII-safe reports:

```python
def format_report(state):
    # Redacts PII
    # Formats sections
    # Extracts citations
    # Adds reproducibility metadata
```

**PII Redaction**:
- Names → `[REDACTED_NAME]`
- IDs → `[REDACTED_ID]` + hash
- Emails → `[REDACTED_EMAIL]`

#### Error (`nodes/error.py`)

Converts errors to safe OrchestrationResult:

```python
def error_handler(state):
    # Sanitizes error messages
    # Removes stack traces
    # Preserves request_id
```

---

## Configuration

### orchestration.yml

```yaml
timeouts:
  agent_call_ms: 30000

retries:
  agent_call: 1

validation:
  strict: false
  require_evidence: true

enabled_intents:
  - pattern.anomalies
  - pattern.correlation
  # ... etc

logging:
  level: INFO
  log_params: true
  log_elapsed: true

formatting:
  max_findings: 10
  redact_pii: true
```

### Loading Configuration

```python
from qnwis.config.orchestration_loader import load_config

config = load_config("custom.yml")
```

---

## CLI Usage

### Installation

```bash
# Already installed via pyproject.toml dependencies
python -m pip install -e .
```

### Basic Usage

```bash
# Pattern correlation analysis
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.correlation \
  --sector Construction \
  --months 36

# GCC benchmarking
python -m qnwis.cli.qnwis_workflow \
  --intent strategy.gcc_benchmark \
  --min-countries 4

# Anomaly detection with custom threshold
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.anomalies \
  --z-threshold 2.5 \
  --min-sample-size 5

# Output to file
python -m qnwis.cli.qnwis_workflow \
  --intent strategy.vision2030 \
  --output vision_report.json \
  --format json

# Markdown output
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.best_practices \
  --output best_practices.md \
  --format markdown
```

### Advanced Usage

```bash
# Custom configuration
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.correlation \
  --config production.yml \
  --log-level DEBUG

# Custom queries directory
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.anomalies \
  --queries-dir /path/to/queries

# With audit trail
python -m qnwis.cli.qnwis_workflow \
  --intent strategy.gcc_benchmark \
  --user-id analyst [at] mol.qa \
  --request-id REQ-2025-001
```

---

## Programmatic Usage

### Basic Example

```python
from qnwis.agents.base import DataClient
from qnwis.orchestration.graph import create_graph
from qnwis.orchestration.registry import create_default_registry
from qnwis.orchestration.schemas import OrchestrationTask

# Initialize components
client = DataClient()
registry = create_default_registry(client)
graph = create_graph(registry)

# Create task
task = OrchestrationTask(
    intent="pattern.correlation",
    params={"sector": "Construction", "months": 36}
)

# Execute
result = graph.run(task)

# Check result
if result.ok:
    for section in result.sections:
        print(f"\n## {section.title}")
        print(section.body_md)
else:
    print("Error:", result.warnings)
```

### Custom Agent Registration

```python
from qnwis.orchestration.registry import AgentRegistry

registry = AgentRegistry()

# Register custom agent
class CustomAgent:
    def analyze(self, threshold: float = 0.5):
        # Custom logic
        pass

custom_agent = CustomAgent()
registry.register("custom.analysis", custom_agent, "analyze")
```

### Error Handling

```python
try:
    result = graph.run(task)
    
    if not result.ok:
        print(f"Workflow failed: {result.warnings}")
        # Inspect sections for error details
        for section in result.sections:
            if section.title == "Error Summary":
                print(section.body_md)
except Exception as exc:
    print(f"Fatal error: {exc}")
```

---

## Performance

### Latency Targets

| Stage | Target | Typical |
|-------|--------|---------|
| Router | <5ms | 2-3ms |
| Invoke | <30s | 5-15s |
| Verify | <10ms | 3-5ms |
| Format | <50ms | 20-30ms |
| **Total** | **<60s** | **10-20s** |

### Optimization Tips

1. **Enable Query Caching**:
   ```yaml
   performance:
     cache_ttl_seconds: 300
   ```

2. **Batch Related Queries**: Agents should batch queries where possible

3. **Monitor Timeouts**: Check logs for timeout warnings

4. **Profile Slow Agents**:
   ```python
   result = graph.run(task)
   elapsed = result.metadata.get("elapsed_ms", 0)
   ```

---

## Security

### Threat Mitigation

| Threat | Mitigation |
|--------|------------|
| Arbitrary code execution | Whitelist-based registry |
| PII exposure | Automatic redaction |
| SQL injection | No direct SQL access |
| Path traversal | Sandboxed file access |
| Stack trace leaks | Error sanitization |

### Audit Trail

```python
task = OrchestrationTask(
    intent="pattern.correlation",
    user_id="analyst [at] mol.qa",  # Who
    request_id="REQ-2025-001"  # What
)

result = graph.run(task)
# result.timestamp → When
# result.reproducibility → How
```

---

## Testing

### Unit Tests

```python
# tests/unit/test_orchestration_graph.py
import pytest
from qnwis.orchestration.schemas import OrchestrationTask

def test_pattern_correlation(mock_client):
    registry = create_default_registry(mock_client)
    graph = create_graph(registry)
    
    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"sector": "Construction", "months": 36}
    )
    
    result = graph.run(task)
    
    assert result.ok
    assert len(result.sections) >= 3
    assert result.citations
```

### Integration Tests

```python
# tests/integration/test_workflow_e2e.py
def test_full_workflow_with_real_data():
    client = DataClient()
    registry = create_default_registry(client)
    graph = create_graph(registry)
    
    for intent in registry.intents():
        task = OrchestrationTask(intent=intent, params={})
        result = graph.run(task)
        
        # Should not crash
        assert result is not None
        assert isinstance(result, OrchestrationResult)
```

---

## Troubleshooting

### Common Issues

#### 1. Unknown Intent Error

```
ERROR: Unknown intent: pattern.custom. Available intents: pattern.anomalies, ...
```

**Solution**: Check `enabled_intents` in config or register the intent

#### 2. Missing Query Definition

```
ERROR: Query definition not found: q_custom_query
```

**Solution**: Verify query YAML exists in `data/queries/`

#### 3. Agent Timeout

```
WARNING: Agent execution exceeded timeout: 35000 ms > 30000 ms
```

**Solution**: Increase `timeouts.agent_call_ms` in config

#### 4. PII in Output

```
John Smith appears in report
```

**Solution**: Enable `formatting.redact_pii: true` in config

### Debug Mode

```bash
python -m qnwis.cli.qnwis_workflow \
  --intent pattern.anomalies \
  --log-level DEBUG
```

---

## Future Enhancements

### Planned Features

1. **Parallel Agent Execution**: Run multiple intents concurrently
2. **Streaming Results**: Progressive output for long-running workflows
3. **Agent Chaining**: Composite workflows (e.g., detect → investigate → recommend)
4. **Result Caching**: Cache formatted results based on task hash
5. **Multi-language Support**: Arabic report formatting
6. **Advanced Metrics**: NDCG@10, MRR for ranking quality

### Extension Points

```python
# Custom node
def custom_enrichment(state):
    # Add business logic
    return state

# Add to graph
workflow.add_node("enrich", custom_enrichment)
workflow.add_edge("verify", "enrich")
workflow.add_edge("enrich", "format")
```

---

## References

### Related Documentation

- [Agent Implementation Guide](../../AGENTS_V1_IMPLEMENTATION_COMPLETE.md)
- [Data Layer Specification](../DETERMINISTIC_DATA_LAYER_SPECIFICATION.md)
- [API Documentation](../API_REFERENCE.md)

### External Dependencies

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Summary

The QNWIS Orchestration Workflow provides a production-ready system for routing analytical tasks through specialized agents with security, observability, and PII protection built-in. The LangGraph-based architecture ensures deterministic execution, graceful error handling, and consistent report formatting.

**Key Deliverables**:
- ✓ Complete LangGraph workflow implementation
- ✓ 7 supported intents with agent mappings
- ✓ CLI tool with comprehensive examples
- ✓ Configuration system with sensible defaults
- ✓ Full test coverage (unit + integration)
- ✓ Production-ready error handling
- ✓ PII redaction and security controls
- ✓ Comprehensive documentation

**Status**: Production-ready for Qatar Ministry of Labour deployment.
