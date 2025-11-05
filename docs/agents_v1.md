# Agents v1 (Deterministic)

## Overview

The QNWIS agent system provides five production-grade agents that analyze labour market data using **only deterministic data sources**. These agents are designed with strict architectural constraints to ensure reproducibility, testability, and data provenance.

## Architecture Guarantees

### ✅ What Agents DO

- **Deterministic data access**: All agents use `DataClient.run(query_id)` which calls `execute_cached()` exclusively
- **Structured insights**: Every finding includes quantitative metrics and full provenance
- **LangGraph orchestration**: Optional simple workflows for multi-step analysis
- **Complete provenance**: Every `Insight` carries `Evidence` linking back to source datasets
- **Cache-friendly**: All queries use the deterministic data layer's caching system

### ❌ What Agents NEVER DO

- **No SQL queries**: Agents never construct or execute SQL directly
- **No RAG/LLM calls**: No external AI models or retrieval-augmented generation
- **No network requests**: No direct HTTP calls or API access
- **No database clients**: No psycopg, SQLAlchemy connections, or database engines

## Five Production Agents

### 1. LabourEconomistAgent

**Focus**: Employment trends and year-over-year growth analysis

**Data Sources**:
- `q_employment_share_by_gender_2023` (employment distribution by gender)

**Metrics Produced**:
- Latest employment percentages (male/female/total)
- Year-over-year growth rates
- Gender distribution trends

**Example**:
```python
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.labour_economist import LabourEconomistAgent

client = DataClient()
report = LabourEconomistAgent(client).run()
for insight in report.findings:
    print(f"{insight.title}: {insight.metrics}")
    for ev in insight.evidence:
        print(f"  Source: {ev.dataset_id} at {ev.locator}")
```

### 2. NationalizationAgent

**Focus**: GCC unemployment comparison and Qatar's competitive position

**Data Sources**:
- `q_unemployment_rate_gcc_latest` (World Bank unemployment data for GCC countries)

**Metrics Produced**:
- Qatar's unemployment rate
- Qatar's rank among GCC countries (1 = best/lowest unemployment)
- Comparative unemployment values

**Key Insight**: Determines Qatar's position relative to regional peers for nationalization policy planning.

### 3. SkillsAgent

**Focus**: Skills pipeline analysis using gender distribution as a proxy

**Data Sources**:
- `q_employment_share_by_gender_2023`

**Metrics Produced**:
- Gender distribution percentages
- Workforce composition metrics

**Note**: Uses employment gender distribution as a deterministic proxy for broader skills availability analysis.

### 4. PatternDetectiveAgent

**Focus**: Data quality validation and consistency checks

**Data Sources**:
- `q_employment_share_by_gender_2023`

**Validations Performed**:
- Sum consistency: Verifies `male_percent + female_percent ≈ total_percent` (tolerance: 0.5%)
- Detects arithmetic discrepancies in reported values
- Reports anomalies via warnings and delta metrics

**Example Output**:
```python
rep = PatternDetectiveAgent(client).run()
if rep.warnings:
    print(f"Data quality issues detected: {rep.warnings}")
if "delta_percent" in rep.findings[0].metrics:
    print(f"Sum mismatch: {rep.findings[0].metrics['delta_percent']}%")
```

### 5. NationalStrategyAgent

**Focus**: Strategic overview combining employment and GCC data

**Data Sources**:
- `q_employment_share_by_gender_2023`
- `q_unemployment_rate_gcc_latest`

**Metrics Produced**:
- Combined employment metrics (prefixed with `employment_`)
- GCC unemployment range (min/max across all countries)
- Integrated view for policy planning

**Use Case**: Provides comprehensive strategic snapshot for national workforce planning decisions.

## Core Data Structures

### Evidence

```python
@dataclass
class Evidence:
    query_id: str        # Deterministic query identifier
    dataset_id: str      # Source dataset (e.g., "employed-persons-*.csv")
    locator: str         # File path or API endpoint
    fields: list[str]    # List of fields in the result
```

### Insight

```python
@dataclass
class Insight:
    title: str                     # Human-readable title
    summary: str                   # Brief description
    metrics: dict[str, float]      # Quantitative measurements
    evidence: list[Evidence]       # Provenance information
    warnings: list[str]            # Data quality warnings
```

### AgentReport

```python
@dataclass
class AgentReport:
    agent: str                # Agent name
    findings: list[Insight]   # Discovered insights
    warnings: list[str]       # Agent-level warnings
```

## DataClient: Strict Gateway to Deterministic Layer

```python
class DataClient:
    def __init__(self, queries_dir: str = "data/queries", ttl_s: int = 300):
        """
        Initialize data client.
        
        Args:
            queries_dir: Path to YAML query definitions
            ttl_s: Cache TTL in seconds (default: 5 minutes)
        """
    
    def run(self, query_id: str) -> QueryResult:
        """
        Execute cached query with normalized results.
        
        Returns:
            QueryResult with normalized row keys, enriched provenance,
            and freshness warnings
        """
```

**Key Features**:
- Enforces deterministic access patterns
- Normalizes row keys to snake_case
- Enriches results with catalog metadata
- Handles cache automatically via `execute_cached()`

## LangGraph Integration

### Simple Workflow Pattern

```python
from src.qnwis.agents.graphs.common import build_simple_graph

# Define query plan
plan_ids = ["q_employment_share_by_gender_2023", "q_unemployment_rate_gcc_latest"]

# Build graph with client runner
graph = build_simple_graph(
    agent_name="CustomAgent",
    plan_ids=plan_ids,
    runner=client.run
)

# Execute workflow
state = graph.invoke({})
report = state["report"]
```

**Workflow Steps**:
1. **plan**: Define list of queries to execute
2. **fetch**: Execute all queries via runner
3. **analyze**: Convert results to structured insights
4. **report**: Aggregate into AgentReport

## Usage Patterns

### Basic Agent Execution

```python
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.labour_economist import LabourEconomistAgent

client = DataClient()
agent = LabourEconomistAgent(client)
report = agent.run()

for finding in report.findings:
    print(f"\n{finding.title}")
    print(f"Summary: {finding.summary}")
    print(f"Metrics: {finding.metrics}")
    print(f"Evidence: {[e.locator for e in finding.evidence]}")
    if finding.warnings:
        print(f"Warnings: {finding.warnings}")
```

### Multi-Agent Pipeline

```python
agents = [
    LabourEconomistAgent(client),
    NationalizationAgent(client),
    SkillsAgent(client),
    PatternDetectiveAgent(client),
    NationalStrategyAgent(client),
]

reports = [agent.run() for agent in agents]

for report in reports:
    print(f"\n=== {report.agent} ===")
    for finding in report.findings:
        print(f"  {finding.title}: {finding.metrics}")
```

### Custom Agent Development

```python
from src.qnwis.agents.base import DataClient, AgentReport, Insight, evidence_from

class CustomAnalysisAgent:
    def __init__(self, client: DataClient):
        self.client = client
    
    def run(self) -> AgentReport:
        # Execute deterministic query
        res = self.client.run("your_query_id")
        
        # Extract metrics
        latest = res.rows[-1].data if res.rows else {}
        metrics = {k: float(v) for k, v in latest.items() 
                   if isinstance(v, (int, float))}
        
        # Build insight with provenance
        insight = Insight(
            title="Your Analysis",
            summary="Description of findings",
            metrics=metrics,
            evidence=[evidence_from(res)],
            warnings=res.warnings
        )
        
        return AgentReport(
            agent="CustomAnalysis",
            findings=[insight]
        )
```

## Testing Strategy

### Unit Tests

All agents have comprehensive unit tests covering:
- Initialization and basic execution
- Metric computation accuracy
- Evidence and provenance tracking
- Warning propagation
- Edge cases (empty data, missing fields, partial data)

**Security Tests**:
- `test_no_sql_strings_in_agents`: Scans source code for SQL keywords
- `test_no_network_calls_in_agents`: Verifies no HTTP client usage

### Integration Tests

- LangGraph workflow execution
- Multi-query orchestration
- State management across workflow steps

### Running Tests

```bash
# Run all agent tests
pytest tests/unit/test_agents*.py tests/unit/test_agent_*.py -v

# Run with coverage
pytest tests/unit/test_agents*.py tests/unit/test_agent_*.py --cov=src/qnwis/agents --cov-report=term-missing

# Run integration tests
pytest tests/integration/test_agents_graphs.py -v
```

## Coverage Requirements

**Target**: ≥90% coverage for `src/qnwis/agents`

**Critical Paths**:
- All `.run()` methods
- Evidence creation and provenance tracking
- Metric computation logic
- Warning propagation
- LangGraph workflow nodes

## Extension Points

### Adding a New Agent

1. **Create agent module** in `src/qnwis/agents/your_agent.py`:
```python
from .base import DataClient, AgentReport, Insight, evidence_from

class YourAgent:
    def __init__(self, client: DataClient):
        self.client = client
    
    def run(self) -> AgentReport:
        # Implement analysis logic
        pass
```

2. **Export from package** in `src/qnwis/agents/__init__.py`:
```python
from .your_agent import YourAgent
__all__ = [..., "YourAgent"]
```

3. **Create unit tests** in `tests/unit/test_agent_your_agent.py`

4. **Verify no SQL/network usage**:
```python
def test_no_sql_in_your_agent():
    import inspect
    from src.qnwis.agents.your_agent import YourAgent
    src = inspect.getsource(YourAgent)
    assert "SELECT " not in src
    assert "psycopg" not in src
```

### Adding a Custom LangGraph Workflow

```python
from langgraph.graph import StateGraph, END
from src.qnwis.agents.graphs.common import AgentState

def build_advanced_workflow(client):
    def custom_analysis(state: AgentState) -> AgentState:
        # Custom logic here
        return {"insights": [...]}
    
    sg = StateGraph(AgentState)
    sg.add_node("custom", custom_analysis)
    sg.set_entry_point("custom")
    sg.add_edge("custom", END)
    return sg.compile()
```

## Deployment Considerations

### Environment Configuration

```bash
# Query registry location
export QNWIS_QUERIES_DIR="data/queries"

# Cache backend (defaults to in-memory)
export QNWIS_CACHE_BACKEND="redis"  # or "memory"
export QNWIS_REDIS_URL="redis://localhost:6379"

# Cache TTL
export QNWIS_CACHE_TTL_SECONDS=300
```

### Performance Characteristics

- **Cache hit latency**: <5ms (in-memory), <10ms (Redis)
- **Cache miss latency**: Depends on data source (CSV: 10-50ms, API: 100-500ms)
- **Agent execution time**: 10-100ms (cached), 100-1000ms (cold)

### Monitoring

Track these metrics in production:
- Cache hit/miss ratio (target: >80% hits)
- Agent execution time percentiles (p50, p95, p99)
- Warning frequency by agent
- Data freshness violations

## Troubleshooting

### "Query not found in registry"

**Cause**: YAML query definition missing or not loaded

**Solution**:
```python
client = DataClient(queries_dir="path/to/queries")
# Ensure YAML files exist in specified directory
```

### "Empty metrics returned"

**Cause**: Query returned no rows or rows missing expected fields

**Solution**: Check query result structure and field names
```python
res = client.run("query_id")
print(f"Rows: {len(res.rows)}")
if res.rows:
    print(f"Fields: {res.rows[0].data.keys()}")
```

### High cache miss rate

**Cause**: TTL too short or invalidation too frequent

**Solution**: Increase TTL for stable data sources
```python
client = DataClient(ttl_s=3600)  # 1 hour
```

## Security Considerations

### Input Validation

All query IDs are validated against the registry. Agents cannot execute arbitrary queries.

### No Injection Risks

Since agents use pre-registered queries only, SQL injection is not possible at the agent layer.

### Rate Limiting

Implement rate limiting at the API layer, not in agents (agents are deterministic, rate limits are non-deterministic).

## Future Enhancements

- [ ] Multi-agent collaboration patterns
- [ ] Conditional workflow branching in LangGraph
- [ ] Streaming insights for long-running analyses
- [ ] Agent health checks and self-diagnostics
- [ ] Automated anomaly detection across multiple agents

## Changelog

### v1.0.0 (Current)
- Initial release with five production agents
- LangGraph integration for simple workflows
- Comprehensive test suite with ≥90% coverage
- Full provenance tracking
- Deterministic-only data access

---

## Quick Reference

**Import Agents**:
```python
from src.qnwis.agents import (
    LabourEconomistAgent,
    NationalizationAgent,
    SkillsAgent,
    PatternDetectiveAgent,
    NationalStrategyAgent,
    DataClient
)
```

**Run Agent**:
```python
client = DataClient()
report = LabourEconomistAgent(client).run()
```

**Access Metrics**:
```python
metrics = report.findings[0].metrics
print(f"Latest value: {metrics.get('total_percent')}")
```

**Check Provenance**:
```python
evidence = report.findings[0].evidence[0]
print(f"Data from: {evidence.dataset_id} @ {evidence.locator}")
```

**Verify No Warnings**:
```python
if not report.warnings and not report.findings[0].warnings:
    print("Data quality checks passed ✓")
```
