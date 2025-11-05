# Orchestration V1 – Deterministic Multi-Agent Council

## Overview

The orchestration layer provides a **deterministic, non-LLM** framework for running a council of 5 agents with numeric verification and consensus synthesis. All operations run on synthetic data from the deterministic data layer with **no network, no SQL, no RAG**.

## Architecture

### Components

1. **Verification Harness** (`verification.py`)
   - Validates metric bounds (percentages, YoY growth)
   - Checks sum-to-one constraints
   - Returns structured warnings/errors

2. **Synthesis Engine** (`synthesis.py`)
   - Merges findings from all agents
   - Computes consensus metrics (simple averages)
   - Deduplicates warnings

3. **Council Orchestrator** (`council.py`)
   - Sequential execution of 5 agents
   - Per-agent verification
   - Council report generation

4. **HTTP API** (`api/routers/council.py`)
   - `POST /v1/council/run` endpoint
   - JSON request/response

### Agent Council

The default council consists of 5 agents:

1. **LabourEconomistAgent** – Employment trends and gender distribution
2. **NationalizationAgent** – Qatarization metrics and workforce composition
3. **SkillsAgent** – Skills distribution and sector analysis
4. **PatternDetectiveAgent** – Anomaly detection and trend analysis
5. **NationalStrategyAgent** – Policy alignment and strategic insights

## Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│  POST /v1/council/run                                       │
│  { queries_dir: str?, ttl_s: int }                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  CouncilConfig                                              │
│  - queries_dir: Path to deterministic queries              │
│  - ttl_s: Cache TTL (default 300s)                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  DataClient Initialization                                  │
│  - Load query registry from queries_dir                     │
│  - Initialize cache with ttl_s                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Sequential Agent Execution                                 │
│  for agent in [LabourEconomist, Nationalization, Skills,    │
│                PatternDetective, NationalStrategy]:         │
│    report = agent.run()                                     │
│    reports.append(report)                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Per-Agent Verification                                     │
│  for report in reports:                                     │
│    issues = verify_report(report)                           │
│    verification[report.agent] = issues                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Council Synthesis                                          │
│  - Collect all findings from agents                         │
│  - Compute consensus metrics (mean of 2+ values)            │
│  - Deduplicate warnings                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  JSON Response                                              │
│  { council: CouncilReport, verification: {...} }            │
└─────────────────────────────────────────────────────────────┘
```

## Numeric Invariants

### Percent Bounds
All metrics ending in `_percent` must satisfy:
```
0.0 ≤ value ≤ 100.0
```
**Violation**: `warn` level with code `percent_range`

### Year-over-Year Growth
YoY percent change must be within sane bounds:
```
-100.0 ≤ yoy_percent ≤ 200.0
```
**Violation**: `warn` level with code `yoy_outlier`

### Sum-to-One Constraint
For gender distribution metrics:
```
|male_percent + female_percent - total_percent| ≤ 0.5
```
**Violation**: `warn` level with code `sum_to_one`

## API Specification

### POST /v1/council/run

Execute the multi-agent council with deterministic data access.

**Request Body (optional query parameters)**:
```json
{
  "queries_dir": "data/queries",  // optional, defaults to data/queries
  "ttl_s": 300                     // optional, cache TTL in seconds
}
```

**Response Structure**:
```json
{
  "council": {
    "agents": ["LabourEconomist", "Nationalization", "Skills", "PatternDetective", "NationalStrategy"],
    "findings": [
      {
        "title": "Employment share (latest & YoY)",
        "summary": "Latest employment split and YoY percentage change for total.",
        "metrics": {
          "male_percent": 72.5,
          "female_percent": 27.5,
          "total_percent": 100.0,
          "yoy_percent": 2.3
        },
        "evidence": [
          {
            "query_id": "q_employment_share_by_gender_2023",
            "dataset_id": "qatar_lfs_2023",
            "locator": "data/raw/lfs_2023.csv",
            "fields": ["year", "gender", "male_percent", "female_percent", "total_percent"]
          }
        ],
        "warnings": [],
        "confidence_score": 1.0
      }
      // ... more findings from all agents
    ],
    "consensus": {
      "male_percent": 71.8,      // average across agents
      "female_percent": 28.2,
      "total_percent": 100.0,
      "yoy_percent": 2.1
    },
    "warnings": [
      "stale_data_60d",
      "synthetic_source"
    ]
  },
  "verification": {
    "LabourEconomist": [],        // no issues
    "Nationalization": [
      {
        "level": "warn",
        "code": "percent_range",
        "detail": "qatari_percent=105.2"
      }
    ],
    "Skills": [],
    "PatternDetective": [],
    "NationalStrategy": []
  }
}
```

## Usage Examples

### Python Client
```python
from qnwis.orchestration import CouncilConfig, run_council

# Basic usage with defaults
config = CouncilConfig()
result = run_council(config)

print(f"Council agents: {result['council']['agents']}")
print(f"Total findings: {len(result['council']['findings'])}")
print(f"Consensus metrics: {result['council']['consensus']}")

# Check verification issues
for agent, issues in result['verification'].items():
    if issues:
        print(f"{agent} has {len(issues)} verification issues")
```

### HTTP Request
```bash
# Using curl
curl -X POST "http://localhost:8000/v1/council/run" \
  -H "Content-Type: application/json" \
  -d '{"queries_dir": "data/queries", "ttl_s": 300}'

# Using httpie
http POST localhost:8000/v1/council/run queries_dir=data/queries ttl_s=300
```

### Custom Agent Factory
```python
from qnwis.agents.base import DataClient
from qnwis.orchestration import CouncilConfig, run_council

def custom_agents(client: DataClient):
    # Use only a subset of agents
    from qnwis.agents.labour_economist import LabourEconomistAgent
    from qnwis.agents.skills import SkillsAgent
    return [
        LabourEconomistAgent(client),
        SkillsAgent(client),
    ]

config = CouncilConfig(queries_dir="data/queries", ttl_s=600)
result = run_council(config, make_agents=custom_agents)
```

## Testing

### Unit Tests
```bash
# Run all orchestration tests
pytest tests/unit/test_orchestration_*.py -v

# Test verification harness
pytest tests/unit/test_orchestration_verification.py -v

# Test synthesis
pytest tests/unit/test_orchestration_synthesis.py -v

# Test council execution
pytest tests/unit/test_orchestration_council.py -v
```

### Integration Tests
```bash
# Test full council execution with synthetic data
pytest tests/integration/test_council_e2e.py -v

# Test API endpoint
pytest tests/integration/test_api_council.py -v
```

## Determinism Guarantees

### Data Access
- **Only** uses `DataClient` with deterministic query registry
- **No** SQL queries or database connections
- **No** network requests or external APIs
- **No** LLM or RAG system calls

### Execution Order
- Agents execute in **fixed sequence**
- No parallelism or race conditions
- Verification runs after each agent
- Synthesis operates on complete report set

### Numeric Operations
- All metrics are `float` type
- Consensus uses simple arithmetic mean
- No random sampling or stochastic algorithms
- Tolerances are fixed constants (SUM_TOL = 0.5)

### Output Format
- JSON-serializable dictionaries only
- No timestamps (unless from source data)
- Warnings are sorted alphabetically and deduplicated
- Findings preserve agent insertion order

## Performance Characteristics

### Latency
- Agent execution: ~10-50ms per agent
- Verification: <1ms per report
- Synthesis: <5ms
- **Total**: ~50-300ms for 5 agents (excludes cache misses)

### Memory
- Each agent report: ~1-5KB
- Council report: ~5-25KB
- Verification results: <1KB
- **Total**: <100KB for typical execution

### Cache Behavior
- DataClient uses in-memory cache with TTL
- Cache keys derived from query_id and parameters
- Cache misses trigger deterministic data loading
- No cache invalidation during council run

## Error Handling

### Missing Queries
If a query definition is not found:
```python
MissingQueryDefinitionError: Deterministic query 'q_employment_share_by_gender_2023' 
is not registered in 'data/queries'. No YAML definition was loaded for 'q_employment_share_by_gender_2023'.
```

### Validation Failures
Verification issues are **non-blocking warnings**:
- `percent_range`: Percent value outside [0, 100]
- `yoy_outlier`: YoY growth outside [-100, 200]
- `sum_to_one`: Gender percentages don't sum to total

### Agent Failures
If an agent raises an exception:
- Exception propagates to caller
- No partial results are returned
- Subsequent agents do not run

## Extension Points

### Custom Agents
Implement agents with the protocol:
```python
class CustomAgent:
    def __init__(self, client: DataClient):
        self.client = client
    
    def run(self) -> AgentReport:
        # Your logic here
        return AgentReport(
            agent="CustomAgent",
            findings=[...],
            warnings=[...]
        )
```

### Custom Verification
Add verification rules to `verification.py`:
```python
def _check_custom_rule(metrics: dict[str, Any]) -> list[VerificationIssue]:
    # Your validation logic
    return issues
```

### Custom Synthesis
Override synthesis behavior:
```python
from qnwis.orchestration.synthesis import synthesize

def custom_synthesize(reports: list[AgentReport]) -> CouncilReport:
    # Your synthesis logic
    return CouncilReport(...)
```

## Migration from LangGraph

This implementation provides a **sequential fallback** for the planned LangGraph DAG. When LangGraph integration is ready:

1. Keep existing `run_council()` as fallback
2. Add `run_council_graph()` with LangGraph orchestration
3. Use feature flag to toggle between implementations
4. Maintain identical output schema

## References

- Agent Base Classes: `src/qnwis/agents/base.py`
- Deterministic Data Layer: `docs/DETERMINISTIC_DATA_LAYER_SPECIFICATION.md`
- Agent Implementations: `src/qnwis/agents/*.py`
- API Specification: `docs/API_SPECIFICATION.md`
