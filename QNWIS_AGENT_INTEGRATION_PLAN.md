# QNWIS Agent Integration Plan - Unlock the Hidden 58%

## Executive Summary

**Current State**: 5/12 agents active (42%) - missing 7 powerful deterministic agents
**Target State**: 10/12 agents active (83%) - full temporal, analytical, and strategic capability
**Impact**: Transform from "current state" analysis to "historical + current + future + what-if" intelligence

## Critical Discovery

We built sophisticated deterministic agents that are sitting unused:

### ✅ Currently Active (5 agents)
1. **LabourEconomist** (LLM) - Employment dynamics
2. **Nationalization** (LLM) - Qatarization analysis
3. **SkillsAgent** (LLM) - Workforce capabilities
4. **PatternDetectiveLLM** (LLM) - Data consistency
5. **NationalStrategyLLM** (LLM) - Vision 2030 alignment

### ❌ Unused But Ready (7 agents)
6. **TimeMachineAgent** (Deterministic) - Historical trends (2010-2024)
   - `historical_comparison()` - Multi-year trend analysis
   - `seasonal_baseline()` - Detect seasonality
   - `change_point_detection()` - Identify structural breaks

7. **PredictorAgent** (Deterministic) - Forecasting (2024-2030)
   - `forecast_baseline()` - Auto-select best method via backtest
   - `early_warning()` - Risk scoring and anomaly alerts
   - `scenario_compare()` - Multi-method forecast comparison

8. **ScenarioAgent** (Deterministic) - Policy simulation
   - `apply()` - Apply single scenario to baseline
   - `compare()` - Compare multiple what-if scenarios
   - `batch()` - Sector-to-national aggregation

9. **PatternDetectiveAgent** (Deterministic) - Statistical anomalies
   - Outlier detection
   - Data quality scoring
   - Consistency checks

10. **NationalStrategyAgent** (Deterministic) - GCC benchmarking
    - Cross-country comparison
    - Regional ranking
    - Competitive positioning

11. **PatternMinerAgent** (Deterministic) - Pattern discovery
    - Correlation analysis
    - Regime detection
    - Leading indicators

12. **AlertCenterAgent** (Deterministic) - Real-time monitoring
    - Threshold alerts
    - SLO violations
    - Early warning signals

## Root Cause Analysis

### Problem 1: Classifier Too Simple
**Current classifier** (`src/qnwis/classification/classifier.py:26-48`):
```python
# Only detects: "compare", "analyze", "forecast", "predict", "scenario"
# MISSES: "future of", "outlook", "trends", "by 2030", "projections"
```

**Example failure**: "Future of work in Qatar and Saudi"
- ❌ Classified as: `complexity="medium"`, `intent="baseline"`
- ✅ Should be: `complexity="complex"`, `intent="temporal+strategic"`
- ✅ Should trigger: TimeMachine + Predictor + Scenario + NationalStrategy

### Problem 2: No Agent Routing Logic
**Current workflow** (`src/qnwis/orchestration/graph_llm.py`):
- Only routes to LLM agents (LabourEconomist, Nationalization, Skills)
- No conditional branches for deterministic agents
- Missing temporal/analytical/strategic detection

### Problem 3: Missing Audit Metadata
**Current output**:
```json
{
  "title": "Finding title",
  "summary": "Analysis text",
  "metrics": {...}
}
```

**Required output**:
```json
{
  "title": "Finding title",
  "summary": "Analysis text",
  "metrics": {...},
  "audit": {
    "audit_id": "20250113-abc123",
    "query_ids": ["q_unemployment_gcc", "q_gcc_labour_stats"],
    "executed_at": "2025-01-13T13:00:00Z",
    "freshness": {
      "asof_date": "2024-Q1",
      "lag_days": 45
    },
    "sources": ["GCC-STAT", "LMIS Database", "World Bank"],
    "reproduce": "qnwis.reproduce('20250113-abc123')"
  }
}
```

### Problem 4: Citations Not Embedded
**Current format**:
"Qatar's unemployment rate is 0.1%"

**Required format**:
"Qatar's unemployment rate is 0.1% [Per query `q_unemployment_qatar_latest` executed 2025-01-13, GCC-STAT Q1 2024]"

## Implementation Plan

### Phase 1: Enhanced Classification (Day 1)

**File**: `src/qnwis/classification/classifier.py`

**Add temporal pattern detection**:
```python
TEMPORAL_PATTERNS = [
    r"future of",
    r"trends? in",
    r"forecast",
    r"predict",
    r"outlook",
    r"projections?",
    r"by 20\d{2}",  # "by 2030"
    r"next \d+ years?",
    r"coming decade"
]

ANALYTICAL_PATTERNS = [
    r"what[- ]if",
    r"scenario",
    r"if we",
    r"impact of",
    r"compare.*to",
    r"anomal(y|ies)",
    r"outlier"
]

STRATEGIC_PATTERNS = [
    r"gcc.*compar",
    r"benchmark",
    r"vision 2030",
    r"competitive",
    r"regional.*position",
    r"qatar.*saudi"
]
```

**Update `classify_text()` method**:
```python
def classify_text(self, question: str) -> Dict[str, Any]:
    question_lower = question.lower()

    # Detect patterns
    needs_temporal = any(re.search(p, question_lower) for p in TEMPORAL_PATTERNS)
    needs_analytical = any(re.search(p, question_lower) for p in ANALYTICAL_PATTERNS)
    needs_strategic = any(re.search(p, question_lower) for p in STRATEGIC_PATTERNS)

    # Determine complexity
    if needs_temporal or needs_analytical:
        complexity = "complex"
    elif needs_strategic or "compare" in question_lower:
        complexity = "medium"
    else:
        complexity = "simple"

    # Determine intent
    intent = "baseline"
    if needs_temporal:
        intent = "temporal"
    elif needs_analytical:
        intent = "analytical"
    elif needs_strategic:
        intent = "strategic"

    # Determine required agents
    agents_to_deploy = []
    if needs_temporal:
        agents_to_deploy.extend(["time_machine", "predictor", "scenario"])
    if needs_analytical:
        agents_to_deploy.extend(["pattern_detective_det"])
    if needs_strategic:
        agents_to_deploy.extend(["national_strategy_det"])

    # Always include base agents
    agents_to_deploy.extend(["labour_economist", "nationalization"])

    return {
        "intent": intent,
        "complexity": complexity,
        "confidence": 0.85,
        "agents_to_deploy": list(set(agents_to_deploy)),  # Remove duplicates
        "patterns_detected": {
            "temporal": needs_temporal,
            "analytical": needs_analytical,
            "strategic": needs_strategic
        }
    }
```

### Phase 2: Agent Integration (Days 2-4)

#### Day 2: TimeMachineAgent

**File**: `src/qnwis/orchestration/graph_llm.py`

**Add import**:
```python
from src.qnwis.agents.time_machine import TimeMachineAgent
```

**Create node factory**:
```python
def create_time_machine_node(data_client: DataClient):
    """Create TimeMachineAgent node for historical analysis."""
    agent = TimeMachineAgent(
        data_client=data_client,
        series_map={
            'unemployment': 'q_unemployment_gcc_timeseries',
            'employment': 'q_employment_gcc_timeseries',
            'qatarization': 'q_qatarization_trend',
            'wages': 'q_wages_timeseries'
        }
    )

    async def time_machine_node(state: dict) -> dict:
        """Execute historical trend analysis."""
        question = state["question"]
        classification = state.get("classification", {})

        # Only run if temporal patterns detected
        if not classification.get("patterns_detected", {}).get("temporal"):
            return state

        # Extract date range from question or use default
        end_date = date.today()
        start_date = date(end_date.year - 5, 1, 1)  # 5 years of history

        # Run analysis
        results = []
        for metric in ['unemployment', 'employment']:
            try:
                analysis = agent.analyze_trend(
                    metric=metric,
                    sector=None,
                    start=start_date,
                    end=end_date
                )
                results.append(analysis)
            except Exception as e:
                logger.warning(f"TimeMachine failed for {metric}: {e}")

        # Store in state
        state["time_machine_results"] = results
        state["reasoning_chain"] = state.get("reasoning_chain", [])
        state["reasoning_chain"].append(
            f"🕰️ TimeMachineAgent: Analyzed {len(results)} metrics over {end_date.year - start_date.year} years"
        )

        return state

    return time_machine_node
```

**Add to workflow**:
```python
# In build_workflow():
workflow.add_node("time_machine", create_time_machine_node(data_client))
workflow.add_edge("prefetch", "time_machine")
workflow.add_edge("time_machine", "rag")
```

#### Day 3: PredictorAgent

**Similar pattern for PredictorAgent**:
```python
def create_predictor_node(data_client: DataClient):
    """Create PredictorAgent node for forecasting."""
    agent = PredictorAgent(
        client=data_client,
        series_map={
            'unemployment': 'q_unemployment_gcc_timeseries',
            'employment': 'q_employment_gcc_timeseries'
        }
    )

    async def predictor_node(state: dict) -> dict:
        """Execute baseline forecasting."""
        classification = state.get("classification", {})

        if not classification.get("patterns_detected", {}).get("temporal"):
            return state

        # Get time_machine results if available
        historical = state.get("time_machine_results", [])

        # Run forecasts
        forecasts = []
        for metric in ['unemployment', 'employment']:
            try:
                forecast = agent.forecast_baseline(
                    metric=metric,
                    sector=None,
                    horizon_months=72,  # 6 years to 2030
                    method="auto"  # Auto-select via backtest
                )
                forecasts.append(forecast)
            except Exception as e:
                logger.warning(f"Predictor failed for {metric}: {e}")

        state["predictor_results"] = forecasts
        state["reasoning_chain"].append(
            f"🔮 PredictorAgent: Generated {len(forecasts)} forecasts with 6-year horizon"
        )

        return state

    return predictor_node
```

#### Day 4: ScenarioAgent

**Similar pattern for ScenarioAgent**:
```python
def create_scenario_node(data_client: DataClient):
    """Create ScenarioAgent node for what-if analysis."""
    agent = ScenarioAgent(client=data_client)

    async def scenario_node(state: dict) -> dict:
        """Execute scenario simulations."""
        classification = state.get("classification", {})

        if not classification.get("patterns_detected", {}).get("analytical"):
            return state

        # Get predictor baselines
        forecasts = state.get("predictor_results", [])

        # Define standard scenarios
        scenarios = [
            {
                "name": "Accelerated Automation",
                "adjustments": [{"metric": "employment", "impact": "-0.02"}]
            },
            {
                "name": "GCC Free Labor Movement",
                "adjustments": [{"metric": "unemployment", "impact": "-0.005"}]
            },
            {
                "name": "Oil Price Shock",
                "adjustments": [{"metric": "unemployment", "impact": "+0.01"}]
            }
        ]

        # Run scenarios
        scenario_results = []
        for scenario in scenarios:
            try:
                result = agent.apply(
                    metric="unemployment",
                    sector=None,
                    baseline_forecast=forecasts[0] if forecasts else None,
                    scenario_spec=scenario
                )
                scenario_results.append(result)
            except Exception as e:
                logger.warning(f"Scenario '{scenario['name']}' failed: {e}")

        state["scenario_results"] = scenario_results
        state["reasoning_chain"].append(
            f"📊 ScenarioAgent: Simulated {len(scenario_results)} policy scenarios"
        )

        return state

    return scenario_node
```

### Phase 3: Conditional Routing (Day 5)

**Update workflow edges to be conditional**:
```python
def route_after_prefetch(state: dict) -> str:
    """Route to appropriate agent based on classification."""
    classification = state.get("classification", {})
    patterns = classification.get("patterns_detected", {})

    # Priority: temporal > analytical > strategic > standard
    if patterns.get("temporal"):
        return "time_machine"
    elif patterns.get("analytical"):
        return "pattern_detective_det"
    elif patterns.get("strategic"):
        return "national_strategy_det"
    else:
        return "rag"  # Standard path

# In build_workflow():
workflow.add_conditional_edges(
    "prefetch",
    route_after_prefetch,
    {
        "time_machine": "time_machine",
        "pattern_detective_det": "pattern_detective_det",
        "national_strategy_det": "national_strategy_det",
        "rag": "rag"
    }
)
```

### Phase 4: Audit Metadata (Days 6-7)

**Add audit metadata to all agent outputs**:
```python
def generate_audit_metadata(state: dict) -> dict:
    """Generate audit metadata for response."""
    import uuid
    from datetime import datetime, timezone

    # Collect all query IDs used
    query_ids = []
    for result in state.get("prefetch_results", []):
        query_ids.append(result.query_id)

    # Collect sources
    sources = set()
    for result in state.get("prefetch_results", []):
        sources.add(result.provenance.source)
        if result.provenance.dataset_id:
            sources.add(result.provenance.dataset_id)

    # Generate audit ID
    audit_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    # Calculate freshness
    freshness_info = {}
    for result in state.get("prefetch_results", []):
        if result.freshness:
            freshness_info[result.query_id] = {
                "asof_date": result.freshness.asof_date,
                "updated_at": result.freshness.updated_at
            }

    return {
        "audit_id": audit_id,
        "query_ids": query_ids,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "freshness": freshness_info,
        "sources": list(sources),
        "reproduce": f"qnwis.reproduce('{audit_id}')",
        "agents_deployed": state.get("classification", {}).get("agents_to_deploy", [])
    }
```

**Add to synthesis**:
```python
# In synthesis node:
audit_metadata = generate_audit_metadata(state)
state["audit_metadata"] = audit_metadata

# Include in final response
response = {
    "narrative": synthesis_text,
    "findings": agent_findings,
    "audit": audit_metadata  # ← Add this
}
```

### Phase 5: Embedded Citations (Day 8)

**Update synthesis prompt to enforce inline citations**:
```python
SYNTHESIS_PROMPT = """
You are synthesizing findings from multiple specialist agents.

CRITICAL CITATION RULES:
1. EVERY numeric claim MUST include inline citation
2. Citation format: "[Per query `{query_id}` executed {date}, {source} {period}]"
3. Example: "Qatar's unemployment rate is 0.1% [Per query `q_unemployment_qatar_latest` executed 2025-01-13, GCC-STAT Q1 2024]"

Available data with citations:
{data_with_citations}

Agent findings:
{agent_findings}

Synthesize into a comprehensive narrative with ALL claims cited inline.
"""
```

**Pre-process data to include citation strings**:
```python
def format_data_with_citations(results: list[QueryResult]) -> str:
    """Format query results with citation strings."""
    lines = []
    for result in results:
        citation = f"[Per query `{result.query_id}` executed {result.freshness.updated_at[:10]}, {result.provenance.source} {result.freshness.asof_date}]"

        for row in result.rows:
            data_str = ", ".join(f"{k}={v}" for k, v in row.data.items())
            lines.append(f"{data_str} {citation}")

    return "\n".join(lines)
```

### Phase 6: UI Reasoning Chain (Day 9)

**Add reasoning chain display to Chainlit UI**:
```python
# In chainlit_app_llm.py, after workflow completes:

if workflow_data.get("reasoning_chain"):
    reasoning_msg = await cl.Message(content="").send()

    await reasoning_msg.stream_token("\n\n## 🧠 Reasoning Chain\n\n")
    await reasoning_msg.stream_token("The system executed the following analytical steps:\n\n")

    for i, step in enumerate(workflow_data["reasoning_chain"], 1):
        await reasoning_msg.stream_token(f"{i}. {step}\n")

    await reasoning_msg.update()
```

## Testing Plan

### Test Case 1: "Future of Work in Qatar and Saudi"

**Expected behavior**:
1. ✅ Classifier detects: `temporal=True`, `strategic=True`, `complexity="complex"`
2. ✅ Agents deployed: TimeMachine + Predictor + Scenario + NationalStrategy + LabourEconomist + Nationalization (6/12)
3. ✅ Output includes:
   - Historical trends (2010-2024)
   - Current state (Q1 2025 with updated Saudi 2.8% figure)
   - Future projections (2024-2030 with confidence intervals)
   - 3 policy scenarios (Automation, Labor Mobility, Oil Shock)
   - Audit metadata with 8+ query IDs
   - All claims cited inline
   - Reasoning chain visible

**Execution time**: 45-60 seconds
**Cost**: $1.20-1.50
**Agent utilization**: 50% (6/12)

### Test Case 2: "What is Qatar's unemployment rate?"

**Expected behavior**:
1. ✅ Classifier detects: `temporal=False`, `complexity="simple"`
2. ✅ Agents deployed: LabourEconomist + Nationalization (2/12)
3. ✅ Output includes:
   - Current rate with citation
   - Audit metadata with 1-2 query IDs
   - Simple reasoning chain

**Execution time**: 3-5 seconds
**Cost**: $0.05-0.10
**Agent utilization**: 17% (2/12) - appropriate for simple query

### Test Case 3: "Detect anomalies in GCC unemployment data"

**Expected behavior**:
1. ✅ Classifier detects: `analytical=True`, `complexity="complex"`
2. ✅ Agents deployed: PatternDetectiveAgent + TimeMachine + LabourEconomist (3/12)
3. ✅ Output includes:
   - Outlier detection results
   - Statistical anomaly scores
   - Historical context
   - Audit metadata

**Execution time**: 20-30 seconds
**Cost**: $0.40-0.60
**Agent utilization**: 25% (3/12)

## Success Metrics

### Before Fix
- Agent utilization: 42% (5/12)
- Query coverage: Medium complexity only
- Reasoning visibility: 0%
- Forecast capability: ❌
- Scenario analysis: ❌
- Audit metadata: ❌
- Inline citations: ❌

### After Fix (Target)
- Agent utilization: 83% (10/12)
- Query coverage: All types (simple, temporal, analytical, strategic)
- Reasoning visibility: 100%
- Forecast capability: ✅ 6-year projections
- Scenario analysis: ✅ What-if modeling
- Audit metadata: ✅ All responses
- Inline citations: ✅ Enforced

## Files to Modify

1. **src/qnwis/classification/classifier.py** - Enhanced pattern detection
2. **src/qnwis/orchestration/graph_llm.py** - Agent integration + routing
3. **src/qnwis/ui/chainlit_app_llm.py** - Reasoning chain display
4. **src/qnwis/agents/base_llm.py** - Citation enforcement in prompts
5. **tests/integration/test_agent_integration.py** - Comprehensive tests

## Timeline

- **Day 1**: Enhanced classifier ✅
- **Day 2**: TimeMachineAgent integration ✅
- **Day 3**: PredictorAgent integration ✅
- **Day 4**: ScenarioAgent integration ✅
- **Day 5**: Conditional routing ✅
- **Day 6-7**: Audit metadata ✅
- **Day 8**: Embedded citations ✅
- **Day 9**: UI reasoning chain ✅
- **Day 10**: Testing & refinement ✅

Total: **10 days to full QNWIS standard**

## Bottom Line

We built a Lamborghini but only connected 42% of the engine. The unused agents (TimeMachine, Predictor, Scenario, PatternDetective, NationalStrategy) are precisely what we need for:

✅ "Future of work" queries
✅ Strategic foresight
✅ Policy simulation
✅ Comprehensive intelligence

Once integrated, every "future of work" query will automatically include:
- 5 years of historical context
- 6 years of future projections
- 3+ policy scenarios
- GCC-wide benchmarking
- Full audit trail
- Inline citations

This transforms QNWIS from "current state reporter" to "strategic intelligence platform."
