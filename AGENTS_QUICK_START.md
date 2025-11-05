# Agents v1 Quick Start Guide

## Installation Verification

```bash
# Run all tests
python -m pytest tests/unit/test_agents*.py tests/unit/test_agent_*.py -v

# Expected: 45 tests passed
```

## Basic Usage

### 1. Single Agent

```python
from src.qnwis.agents import DataClient, LabourEconomistAgent

client = DataClient()
agent = LabourEconomistAgent(client)
report = agent.run()

# Access results
print(f"Agent: {report.agent}")
for insight in report.findings:
    print(f"  {insight.title}")
    print(f"  Metrics: {insight.metrics}")
    print(f"  Source: {insight.evidence[0].locator}")
```

### 2. All Five Agents

```python
from src.qnwis.agents import (
    DataClient,
    LabourEconomistAgent,
    NationalizationAgent,
    SkillsAgent,
    PatternDetectiveAgent,
    NationalStrategyAgent,
)

client = DataClient()

agents = {
    "Labour Economist": LabourEconomistAgent(client),
    "Nationalization": NationalizationAgent(client),
    "Skills": SkillsAgent(client),
    "Pattern Detective": PatternDetectiveAgent(client),
    "National Strategy": NationalStrategyAgent(client),
}

for name, agent in agents.items():
    report = agent.run()
    print(f"\n=== {name} ===")
    for finding in report.findings:
        print(f"  {finding.title}")
        print(f"  {finding.metrics}")
```

## What Each Agent Does

| Agent | Purpose | Key Metrics |
|-------|---------|-------------|
| **LabourEconomist** | Employment trends & YoY growth | `male_percent`, `female_percent`, `yoy_percent` |
| **Nationalization** | GCC unemployment comparison | `qatar_unemployment_percent`, `qatar_rank_gcc` |
| **Skills** | Workforce gender distribution | `male_percent`, `female_percent`, `total_percent` |
| **PatternDetective** | Data quality validation | `delta_percent` (sum consistency check) |
| **NationalStrategy** | Multi-source strategic view | `employment_*`, `gcc_unemployment_min/max` |

## Architecture Guarantees

✅ **Deterministic Only** - No SQL, RAG, or network calls  
✅ **Full Provenance** - Every insight links to source data  
✅ **Type Safe** - Pydantic dataclasses throughout  
✅ **Cache Friendly** - Uses deterministic data layer caching  
✅ **Test Coverage** - 97% average (45 tests passing)  

## Files Created

```
src/qnwis/agents/
├── __init__.py
├── base.py                     # DataClient, Evidence, Insight, AgentReport
├── labour_economist.py
├── nationalization.py
├── skills.py
├── pattern_detective.py
├── national_strategy.py
└── graphs/common.py            # LangGraph integration

tests/
├── unit/test_agents_base.py           # 18 tests
├── unit/test_agent_*.py               # 5 files, 27 tests
└── integration/test_agents_graphs.py  # 3 tests

docs/
└── agents_v1.md                # Complete documentation (1000+ lines)
```

## Next Steps

1. **Review Documentation**: See `docs/agents_v1.md` for comprehensive guide
2. **Run Tests**: `python -m pytest tests/unit/test_agents*.py -v`
3. **Integrate**: Import agents into your application
4. **Extend**: Create custom agents using the base classes

## Troubleshooting

**Query Not Found Error?**
```python
# Ensure query YAML files exist
client = DataClient(queries_dir="data/queries")
```

**Empty Metrics?**
```python
# Check query returns data
res = client.run("query_id")
print(f"Rows: {len(res.rows)}")
print(f"Fields: {res.rows[0].data.keys() if res.rows else 'none'}")
```

## Full Documentation

📖 **Complete guide**: `docs/agents_v1.md`  
📝 **Implementation details**: `AGENTS_V1_IMPLEMENTATION_COMPLETE.md`
