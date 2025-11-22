# LangGraph Intelligence Nodes

This directory contains the **modular node architecture** for the QNWIS Multi-Agent Intelligence System.

## Architecture Overview

The intelligence workflow is decomposed into **10 specialized nodes**, each with a single responsibility:

```
┌─────────────┐
│ Classifier  │ ← Entry point: Analyze query complexity
└──────┬──────┘
       │
┌──────▼──────┐
│ Extraction  │ ← Fetch data from cache/APIs (cache-first <100ms)
└──────┬──────┘
       │
       ├─→ [Simple queries skip to Synthesis]
       │
┌──────▼──────┐
│  Financial  │ ← MicroEconomist + MacroEconomist analysis
└──────┬──────┘
       │
┌──────▼──────┐
│   Market    │ ← GCC competitive analysis, regional benchmarking
└──────┬──────┘
       │
┌──────▼──────┐
│ Operations  │ ← Nationalization feasibility, implementation analysis
└──────┬──────┘
       │
┌──────▼──────┐
│  Research   │ ← Research scientist + Semantic Scholar evidence
└──────┬──────┘
       │
┌──────▼──────┐
│   Debate    │ ← Multi-agent contradiction resolution
└──────┬──────┘
       │
┌──────▼──────┐
│  Critique   │ ← Devil's advocate stress-testing
└──────┬──────┘
       │
┌──────▼──────┐
│Verification │ ← Fact checking, citation validation
└──────┬──────┘
       │
┌──────▼──────┐
│  Synthesis  │ ← Final ministerial-grade intelligence
└──────┬──────┘
       │
      END
```

## Node Descriptions

### 1. Classifier (`classifier.py`)

**Purpose:** Analyze query complexity for intelligent routing

**Logic:**
- **Critical**: Urgent/emergency keywords → Parallel execution
- **Complex**: Strategic decisions, multi-domain → Full analysis
- **Medium**: Single domain → Standard flow
- **Simple**: Fact lookup → Fast path (skip agents)

**Output:** Sets `state["complexity"]`

### 2. Extraction (`extraction.py`)

**Purpose:** Fetch data using cache-first strategy

**Integration:**
- Wraps `prefetch_apis.get_complete_prefetch()`
- Uses PostgreSQL cache (World Bank: 128 cached indicators, <100ms)
- Falls back to 12+ live APIs when needed

**Output:** Sets `extracted_facts`, `data_sources`, `data_quality_score`

### 3. Financial (`financial.py`)

**Purpose:** Financial impact analysis

**Agents:**
- Financial Economist (PhD-level cost-benefit, ROI, NPV)
- Uses IMF, World Bank, UNCTAD data

**Output:** Sets `financial_analysis`, appends to `agent_reports`

### 4. Market (`market.py`)

**Purpose:** Market intelligence and competitive analysis

**Analysis:**
- GCC regional comparisons
- Tourism sector trends (UNWTO)
- Labor market benchmarking (ILO)

**Output:** Sets `market_analysis`, appends to `agent_reports`

### 5. Operations (`operations.py`)

**Purpose:** Operational feasibility assessment

**Analysis:**
- Nationalization implementation timelines
- Workforce planning scenarios
- Resource constraint identification

**Output:** Sets `operations_analysis`, appends to `agent_reports`

### 6. Research (`research.py`)

**Purpose:** Evidence-based research grounding

**Integration:**
- Research Scientist agent
- Semantic Scholar academic papers (200M+ papers)
- Citation quality analysis

**Output:** Sets `research_analysis`, appends to `agent_reports`

### 7. Debate (`debate.py`)

**Purpose:** Multi-agent contradiction resolution

**Logic:**
- Detects contradictions between agent narratives
- Sentiment analysis heuristics
- Confidence-weighted resolution
- Can integrate with `legendary_debate_orchestrator.py` for full 80-125 turn debates

**Output:** Sets `debate_synthesis`, `debate_results`

### 8. Critique (`critique.py`)

**Purpose:** Devil's advocate stress-testing

**Analysis:**
- Challenges all agent assumptions
- Identifies weaknesses in reasoning
- Generates independent critical perspective

**Output:** Sets `critique_report`

### 9. Verification (`verification.py`)

**Purpose:** Fact checking and citation validation

**Integration:**
- Uses `verification/` subsystem (L2-L4 layers)
- Citation enforcement
- Numeric claim validation
- Fabrication detection

**Output:** Sets `fact_check_results`, `fabrication_detected`

### 10. Synthesis (`synthesis.py`)

**Purpose:** Final ministerial-grade intelligence brief

**Logic:**
- Combines all agent findings
- Incorporates debate consensus
- Applies critique insights
- Calculates final confidence score

**Output:** Sets `final_synthesis`, `confidence_score`

## State Management

All nodes operate on the shared `IntelligenceState` TypedDict (defined in `state.py`):

```python
class IntelligenceState(TypedDict, total=False):
    # Input
    query: str
    complexity: str
    
    # Data
    extracted_facts: List[Dict[str, Any]]
    data_sources: List[str]
    data_quality_score: float
    
    # Agent Outputs
    agent_reports: List[Dict[str, Any]]
    financial_analysis: Optional[str]
    market_analysis: Optional[str]
    operations_analysis: Optional[str]
    research_analysis: Optional[str]
    
    # Multi-agent processing
    debate_synthesis: Optional[str]
    debate_results: Optional[Dict[str, Any]]
    critique_report: Optional[str]
    
    # Verification
    fact_check_results: Optional[Dict[str, Any]]
    fabrication_detected: bool
    
    # Final output
    final_synthesis: Optional[str]
    confidence_score: float
    reasoning_chain: List[str]
    
    # Metadata
    nodes_executed: List[str]
    execution_time: Optional[float]
    warnings: List[str]
    errors: List[str]
```

## Helper Utilities

### `_helpers.py`

Shared utilities for node implementations:

- **`create_llm_client(state)`**: Create LLM client with feature-flag support
- **`record_agent_report(state, name, report)`**: Store agent output
- **`execute_agent_analysis(state, ...)`**: Execute agent with error handling

## Performance Characteristics

**Simple queries** (e.g., "What is unemployment rate?"):
- Nodes executed: 3 (classifier → extraction → synthesis)
- Execution time: 2-5 seconds
- Cached data: < 100ms

**Medium queries** (e.g., "Analyze employment trends"):
- Nodes executed: 10 (all nodes)
- Execution time: 20-40 seconds
- Includes full agent analysis

**Complex queries** (e.g., "Should Qatar invest $15B in..."):
- Nodes executed: 10 (all nodes)
- Execution time: 30-60 seconds
- Includes extended debate resolution

## Testing

**Unit tests**: Test each node independently
```bash
pytest tests/unit/orchestration/nodes/
```

**Integration tests**: Test full workflow
```bash
python test_langgraph_basic.py  # 2-node workflow
python test_langgraph_full.py   # 10-node workflow
```

## Migration from Legacy Architecture

The old `graph_llm.py` (2016 lines) is being replaced by this modular architecture.

**Feature flag** (in `.env` or environment):
```bash
# Use new modular workflow
export QNWIS_WORKFLOW_IMPL=langgraph

# Use legacy monolithic workflow (default during migration)
export QNWIS_WORKFLOW_IMPL=legacy
```

**Migration timeline:**
1. **Week 1-2**: Implement all 10 nodes (✅ COMPLETE)
2. **Week 3**: Testing and hardening
3. **Week 4**: Gradual rollout with feature flag
4. **Week 5**: Default to new workflow
5. **Week 6**: Deprecate and remove graph_llm.py

## Code Quality Standards

Each node must:
- Be **< 200 lines** (down from 2016-line monolith)
- Have **single responsibility**
- Be **independently testable**
- Have **comprehensive docstrings**
- Follow **type safety** (strict mypy)
- Handle **errors gracefully**

## Extension Points

To add a new node:

1. Create `nodes/your_node.py`:
```python
from ..state import IntelligenceState

def your_node(state: IntelligenceState) -> IntelligenceState:
    """Brief description."""
    # Your logic here
    state.setdefault("nodes_executed", []).append("your_node")
    return state
```

2. Export in `nodes/__init__.py`:
```python
from .your_node import your_node

__all__ = [..., "your_node"]
```

3. Wire in `workflow.py`:
```python
workflow.add_node("your_node", your_node)
workflow.add_edge("previous_node", "your_node")
```

## References

- **State Schema**: `src/qnwis/orchestration/state.py`
- **Main Workflow**: `src/qnwis/orchestration/workflow.py`
- **Streaming Adapter**: `src/qnwis/orchestration/streaming.py`
- **Feature Flags**: `src/qnwis/orchestration/feature_flags.py`
- **Legacy Implementation**: `src/qnwis/orchestration/graph_llm.py` (deprecated)

