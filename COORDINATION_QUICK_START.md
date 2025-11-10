# Coordination Layer Quick Start

**Status**: ✅ Production Ready  
**Last Updated**: November 6, 2024

## What is the Coordination Layer?

The coordination layer orchestrates multi-agent execution with:
- **Declarative prefetch** via DataClient
- **Flexible execution modes** (single/parallel/sequential)
- **Deterministic result merging** with PII safety
- **Policy-based resource management**

---

## Quick Usage

### 1. Import Components

```python
from src.qnwis.orchestration import (
    Coordinator,
    Prefetcher,
    merge_results,
    CoordinationPolicy,
    get_policy_for_complexity,
    PrefetchSpec,
    AgentCallSpec,
)
from src.qnwis.agents.base import DataClient
from src.qnwis.orchestration.registry import AgentRegistry
```

### 2. Setup Coordinator

```python
# Create components
client = DataClient("data/queries")
registry = AgentRegistry()  # or use create_default_registry(client)
policy = CoordinationPolicy(max_parallel=3, per_agent_timeout_ms=30000)

# Initialize coordinator
coordinator = Coordinator(registry, policy)
```

### 3. Execute Multi-Agent Workflow

```python
# Define agent calls
specs = [
    AgentCallSpec(
        intent="pattern.anomalies",
        method="detect_anomalous_retention",
        params={"months": 12},
    ),
    AgentCallSpec(
        intent="pattern.correlation",
        method="find_correlations",
        params={"months": 12},
    ),
]

# Plan execution (mode: single, parallel, or sequential)
waves = coordinator.plan("pattern.anomalies", specs, mode="parallel")

# Execute with prefetch cache
prefetch_cache = {}  # Populated by Prefetcher if needed
results = coordinator.execute(waves, prefetch_cache)

# Merge into final report
final = coordinator.aggregate(results)
```

---

## Execution Modes

### Single Mode
```python
# Execute exactly one agent
waves = coordinator.plan(route, [spec1], "single")
# → [[spec1]]
```

### Parallel Mode
```python
# Execute multiple agents with bounded concurrency
waves = coordinator.plan(route, [spec1, spec2, spec3], "parallel")
# With max_parallel=2:
# → [[spec1, spec2], [spec3]]
```

### Sequential Mode
```python
# Execute agents one at a time
waves = coordinator.plan(route, [spec1, spec2], "sequential")
# → [[spec1], [spec2]]
```

---

## Prefetch Usage

### Basic Prefetch

```python
from src.qnwis.orchestration import Prefetcher, generate_cache_key

# Initialize prefetcher
prefetcher = Prefetcher(client, timeout_ms=25000)

# Define prefetch specs
specs = [
    PrefetchSpec(
        fn="run",  # DataClient method name
        params={"query_id": "retention_by_sector"},
        cache_key=generate_cache_key("run", {"query_id": "retention_by_sector"}),
    ),
]

# Execute prefetch
cache = prefetcher.run(specs)
# → {"abc123...": QueryResult(...)}
```

### In Graph Workflow

The graph automatically runs prefetch if `RoutingDecision.prefetch` is populated:

```python
from src.qnwis.orchestration import create_graph

graph = create_graph(
    registry=registry,
    data_client=client,  # Required for prefetch
    config={
        "timeouts": {
            "prefetch_ms": 25000,
        },
    },
)

# Router populates RoutingDecision.prefetch
# Graph executes prefetch before invoke node
# Agents receive prefetch_cache in state
```

---

## Policy Configuration

### Policy Basics

```python
from src.qnwis.orchestration import CoordinationPolicy

policy = CoordinationPolicy(
    max_parallel=3,           # Normal mode parallelism
    crisis_parallel=5,        # Crisis mode parallelism
    per_agent_timeout_ms=30000,
    total_timeout_ms=60000,
    strict_merge=False,       # Allow missing sections
    retry_transient=1,        # Retry count for transient failures
)
```

### Complexity-Based Policies

```python
from src.qnwis.orchestration import get_policy_for_complexity

# Automatically select policy based on query complexity
simple_policy = get_policy_for_complexity("simple")
# → max_parallel=1, timeout=25000ms

crisis_policy = get_policy_for_complexity("crisis")
# → max_parallel=5, timeout=20000ms
```

| Complexity | max_parallel | per_agent_timeout_ms | total_timeout_ms |
|------------|--------------|----------------------|------------------|
| simple     | 1            | 25000                | 40000            |
| medium     | 2            | 30000                | 50000            |
| complex    | 3            | 30000                | 60000            |
| crisis     | 5            | 20000                | 45000            |

---

## Result Merging

### Basic Merge

```python
from src.qnwis.orchestration import merge_results

# Merge multiple OrchestrationResult objects
merged = merge_results([result1, result2, result3])

# Features:
# ✅ Deterministic section ordering
# ✅ Deduplication (sections, citations)
# ✅ PII masking
# ✅ Freshness tracking
# ✅ Reproducibility metadata
```

### Merge Behavior

**Section Ordering** (canonical):
1. Executive Summary
2. Key Findings
3. Evidence
4. Citations & Freshness
5. Reproducibility
6. Warnings

**Deduplication**:
- Sections: By (title, first 40 chars)
- Citations: By (query_id, dataset_id)
- Warnings: By exact text

**PII Masking**:
- Names (e.g., "John Smith" → "***")
- Emails (e.g., "user@example.com" → "***")
- IDs (long numeric sequences → "***")

---

## Graph Integration

### Full Workflow Example

```python
from src.qnwis.orchestration import create_graph, OrchestrationTask
from src.qnwis.agents.base import DataClient
from src.qnwis.orchestration.registry import create_default_registry

# Setup
client = DataClient("data/queries")
registry = create_default_registry(client)

# Create graph with coordination
graph = create_graph(
    registry=registry,
    data_client=client,
    config={
        "timeouts": {
            "agent_call_ms": 30000,
            "prefetch_ms": 25000,
        },
        "coordination": {
            "enabled": True,
        },
    },
)

# Run task
task = OrchestrationTask(
    intent="pattern.anomalies",
    params={"months": 12},
    request_id="req_123",
)

result = graph.run(task)
# → OrchestrationResult with merged findings
```

---

## Testing

### Run Coordination Tests

```bash
# All coordination tests
python -m pytest tests/unit/orchestration/test_coordination.py -v

# Specific test class
python -m pytest tests/unit/orchestration/test_coordination.py::TestCoordinator -v

# Specific test
python -m pytest tests/unit/orchestration/test_coordination.py::TestMergeResults::test_merge_multiple_results -v
```

### Run Demo

```bash
python demo_coordination.py
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                       │
├─────────────────────────────────────────────────────────────┤
│  Router → Prefetch → Invoke → Verify → Format → Merge      │
│     ↓         ↓         ↓                          ↓        │
│  Routing   Prefetcher  Coordinator            merge_results │
│  Decision              + Registry                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
                      DataClient Only
```

### Data Flow

1. **Router** → Produces `RoutingDecision` with:
   - `mode` (single/parallel/sequential)
   - `agents` (list of agent methods)
   - `prefetch` (list of PrefetchSpec)
   - `execution_hints` (complexity, priority)

2. **Prefetch** → Executes specs via DataClient:
   - Returns `prefetch_cache: Dict[cache_key, QueryResult]`
   - Deduplicates by cache_key
   - Enforces timeout

3. **Invoke** → Coordinator executes agents:
   - Plans execution waves
   - Runs agents with prefetch_cache available
   - Collects OrchestrationResult per agent

4. **Merge** → Combines results:
   - Deterministic section ordering
   - Deduplicates citations/sections
   - Masks PII
   - Tracks freshness

---

## Best Practices

### 1. Always Use Policies
```python
# ❌ Bad: Hardcoded values
coordinator = Coordinator(registry, CoordinationPolicy(max_parallel=99))

# ✅ Good: Complexity-based
policy = get_policy_for_complexity(task.classification.complexity)
coordinator = Coordinator(registry, policy)
```

### 2. Handle Missing DataClient
```python
# Prefetch degrades gracefully if DataClient not available
graph = create_graph(
    registry=registry,
    data_client=None,  # OK: Prefetch skipped, agents fetch on demand
)
```

### 3. Use Cache Keys Correctly
```python
from src.qnwis.orchestration import generate_cache_key

# ✅ Good: Deterministic cache key
cache_key = generate_cache_key("run", {"query_id": "abc"})

# ❌ Bad: Manual key (not deterministic)
cache_key = f"run_abc_{random.randint(1, 100)}"
```

### 4. Validate Merged Results
```python
merged = merge_results(partials)

# Always check ok status
if not merged.ok:
    logger.warning("Merged result has failures: %s", merged.warnings)

# Verify expected sections present
required = {"Executive Summary", "Key Findings"}
present = {s.title for s in merged.sections}
if not required.issubset(present):
    logger.warning("Missing sections: %s", required - present)
```

---

## Troubleshooting

### Prefetch Fails
```python
# Check logs for:
# - "Prefetch failed: ..."
# - "DataClient not available"

# Workflow continues without prefetch
# Agents fetch data on demand via DataClient
```

### Agents Timeout
```python
# Adjust policy timeouts
policy = CoordinationPolicy(
    per_agent_timeout_ms=60000,  # Increase to 60s
    total_timeout_ms=120000,     # Increase total
)
```

### Merge Produces No Sections
```python
# Check that agent results have sections
for result in partials:
    if not result.sections:
        logger.warning("Agent %s returned no sections", result.intent)

# Ensure at least one successful result
if all(not r.ok for r in partials):
    raise ValueError("All agent results failed")
```

---

## API Reference

### Core Classes

- **`Coordinator`**: Plans and executes multi-agent workflows
- **`Prefetcher`**: Executes declarative prefetch specs
- **`CoordinationPolicy`**: Controls parallelism and timeouts
- **`merge_results()`**: Deterministically merges results

### Type Definitions

- **`PrefetchSpec`**: `{fn: str, params: dict, cache_key: str}`
- **`AgentCallSpec`**: `{intent: str, method: str, params: dict}`
- **`ExecutionTrace`**: Agent execution metadata

### Functions

- **`get_policy_for_complexity(complexity)`**: Returns policy for complexity level
- **`generate_cache_key(fn, params)`**: Generates deterministic cache key

---

## Next Steps

1. **Router Integration**: Update router to generate `prefetch` and `execution_hints`
2. **Async Execution**: Replace sequential wave execution with true parallelism
3. **Performance Monitoring**: Add metrics for prefetch hit rates and merge timing
4. **Crisis Detection**: Automatic policy adjustment based on system state

---

## Summary

✅ **DataClient-only access** (no raw SQL/HTTP)  
✅ **Flexible execution modes** (single/parallel/sequential)  
✅ **Deterministic merging** with PII safety  
✅ **Policy-based resource management**  
✅ **Backward compatible** with existing workflows  
✅ **Production ready** with tests and demos  

**Documentation**: See `COORDINATION_LAYER_IMPLEMENTATION.md` for full details.
