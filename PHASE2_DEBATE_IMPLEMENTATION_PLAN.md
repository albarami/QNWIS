# Phase 2 Step 2A: Multi-Agent Debate Implementation Plan

## Objective

Implement a **Multi-Agent Debate Node** that creates emergent intelligence through structured cross-examination of agent findings.

**Key Insight**: "Adding agents ≠ better intelligence. Debate creates emergent intelligence."

---

## Design Principles

1. **Identify Real Contradictions**: Not superficial differences, but actual conflicts in conclusions
2. **Structured Deliberation**: Formal debate process, not chaos
3. **Evidence-Based**: All debate must reference specific citations
4. **Confidence Weighting**: Higher-confidence agents have more influence
5. **Convergence**: Must produce actionable consensus

---

## Architecture

### Debate Node Flow
```
Agent Reports → Contradiction Detection → Structured Debate → Consensus Building → Resolution
```

### Node Placement
Insert between `_agents_node` and `_verify_node`:
```
classify → prefetch → rag → agents → DEBATE → verify → synthesize → done
```

---

## Implementation Specifications

### 1. Contradiction Detection

**Function**: `_detect_contradictions(reports: list) -> list[Contradiction]`

**Logic**:
```python
class Contradiction:
    metric_name: str
    agent1_name: str
    agent1_value: float
    agent1_citation: str
    agent1_confidence: float
    agent2_name: str
    agent2_value: float
    agent2_citation: str
    agent2_confidence: float
    severity: str  # "high", "medium", "low"
```

**Detection Rules**:
- Same metric name, different values (>5% difference)
- Conflicting interpretations (e.g., "improving" vs "declining")
- Different confidence levels for same claim
- Source data conflicts

**Example**:
```python
Contradiction(
    metric_name="qatar_unemployment_rate",
    agent1_name="LabourEconomist",
    agent1_value=0.10,
    agent1_citation="[Per extraction: '0.10%' from GCC-STAT Q1-2024]",
    agent1_confidence=0.90,
    agent2_name="NationalStrategy",
    agent2_value=0.12,
    agent2_citation="[Per extraction: '0.12%' from World Bank 2024]",
    agent2_confidence=0.85,
    severity="high"
)
```

### 2. Structured Debate

**Function**: `_conduct_debate(contradiction: Contradiction, llm: LLMClient) -> DebateResolution`

**Debate Prompt**:
```python
DEBATE_PROMPT = """
You are a neutral arbitrator conducting a structured debate between two agents who have conflicting findings.

CONTRADICTION:
- Metric: {metric_name}
- Agent 1 ({agent1_name}): {agent1_value} {agent1_citation} (confidence: {agent1_confidence})
- Agent 2 ({agent2_name}): {agent2_value} {agent2_citation} (confidence: {agent2_confidence})

TASK:
1. Analyze both citations to determine source reliability
2. Check if values are actually measuring the same thing (e.g., same time period, same definition)
3. Determine if both can be correct (different methodologies/sources)
4. If only one can be correct, determine which based on:
   - Source authority (GCC-STAT > World Bank > other)
   - Data freshness (more recent > older)
   - Citation completeness
   - Agent confidence

OUTPUT FORMAT (JSON):
{{
  "resolution": "agent1_correct" | "agent2_correct" | "both_valid" | "neither_valid",
  "explanation": "Detailed explanation of why",
  "recommended_value": value or null,
  "recommended_citation": "citation" or null,
  "confidence": 0.0-1.0,
  "action": "use_agent1" | "use_agent2" | "use_both" | "flag_for_review"
}}
"""
```

**Debate Process**:
1. LLM analyzes contradiction with neutral perspective
2. Evaluates evidence quality
3. Determines resolution
4. Outputs structured decision

### 3. Consensus Building

**Function**: `_build_consensus(resolutions: list[DebateResolution]) -> ConsensusResult`

**Logic**:
- Weight resolutions by confidence
- If majority agree → accept
- If split decision → flag for human review
- If multiple "both_valid" → include all with context

**Output**:
```python
class ConsensusResult:
    resolved_contradictions: int
    flagged_for_review: int
    consensus_narrative: str
    adjusted_reports: list[AgentReport]  # With debate outcomes incorporated
```

### 4. Integration with Workflow

**Add debate node**:
```python
async def _debate_node(self, state: WorkflowState) -> WorkflowState:
    """
    Conduct multi-agent debate to resolve contradictions.

    Args:
        state: Current workflow state with agent_reports

    Returns:
        Updated state with debate_results and adjusted reports
    """
    if state.get("event_callback"):
        await state["event_callback"]("debate", "running")

    start_time = datetime.now(timezone.utc)
    reports = state.get("agent_reports", [])

    # 1. Detect contradictions
    contradictions = self._detect_contradictions(reports)

    if not contradictions:
        logger.info("No contradictions detected - skipping debate")
        return {
            **state,
            "debate_results": {
                "contradictions_found": 0,
                "status": "skipped",
                "latency_ms": 0
            }
        }

    logger.info(f"Detected {len(contradictions)} contradictions - starting debate")

    # 2. Conduct structured debates
    resolutions = []
    for contradiction in contradictions:
        resolution = await self._conduct_debate(contradiction, self.llm)
        resolutions.append(resolution)

    # 3. Build consensus
    consensus = self._build_consensus(resolutions)

    # 4. Adjust agent reports based on debate
    adjusted_reports = self._apply_debate_resolutions(reports, resolutions)

    latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    logger.info(
        f"Debate complete: {consensus.resolved_contradictions} resolved, "
        f"{consensus.flagged_for_review} flagged, latency={latency_ms:.0f}ms"
    )

    if state.get("event_callback"):
        await state["event_callback"](
            "debate",
            "complete",
            {
                "contradictions": len(contradictions),
                "resolved": consensus.resolved_contradictions,
                "flagged": consensus.flagged_for_review
            },
            latency_ms
        )

    return {
        **state,
        "agent_reports": adjusted_reports,
        "debate_results": {
            "contradictions_found": len(contradictions),
            "resolved": consensus.resolved_contradictions,
            "flagged_for_review": consensus.flagged_for_review,
            "consensus_narrative": consensus.consensus_narrative,
            "latency_ms": latency_ms,
            "status": "complete"
        }
    }
```

### 5. Update WorkflowState

Add to TypedDict:
```python
debate_results: Optional[Dict[str, Any]]
```

### 6. Update Graph

Add debate node to workflow:
```python
# In _build_graph()
self.graph.add_node("debate", self._debate_node)
self.graph.add_edge("agents", "debate")
self.graph.add_edge("debate", "verify")
```

---

## Example Scenario

### Input: Two Agent Reports
```python
Report 1 (LabourEconomist):
- Finding: "Qatar unemployment is [Per extraction: '0.10%' from GCC-STAT Q1-2024]"
- Confidence: 0.90

Report 2 (NationalStrategy):
- Finding: "Qatar unemployment is [Per extraction: '0.12%' from World Bank 2024]"
- Confidence: 0.85
```

### Contradiction Detection
```python
Contradiction detected:
- Metric: qatar_unemployment_rate
- Difference: 0.02% (20% relative difference)
- Severity: medium
```

### Debate Process
```
Arbitrator Analysis:
1. Source comparison: GCC-STAT (regional authority) vs World Bank (global)
2. Time period: Q1-2024 (specific) vs 2024 (annual average)
3. Measurement: Both measure unemployment but different periods/methods

Resolution: both_valid (different time periods)
Action: use_both with context
```

### Consensus Output
```python
ConsensusResult:
- resolved_contradictions: 1
- flagged_for_review: 0
- consensus_narrative: "Qatar unemployment ranges 0.10-0.12% depending on source and period. GCC-STAT reports 0.10% for Q1-2024, while World Bank estimates 0.12% for full year 2024."
- adjusted_reports: [includes context about both values]
```

---

## Success Criteria

### Functional
- ✅ Detects real contradictions (not false positives)
- ✅ Conducts structured debate with LLM arbitration
- ✅ Produces actionable consensus
- ✅ Adjusts agent reports with debate outcomes
- ✅ Logs debate process for transparency

### Performance
- ✅ Completes in <60s for 3 contradictions
- ✅ Handles 0 contradictions gracefully (skip debate)
- ✅ Handles 10+ contradictions (batch processing)

### Quality
- ✅ Evidence-based resolutions (cites sources)
- ✅ Confidence-weighted decisions
- ✅ Clear explanation of reasoning
- ✅ No hallucination (uses only provided data)

---

## Testing Plan

### Test Cases

1. **No Contradictions**
   - Input: 3 agreeing agents
   - Expected: Skip debate, 0ms latency

2. **Simple Contradiction**
   - Input: 2 agents, same metric, different values, same source
   - Expected: Resolve to higher-confidence agent

3. **Source Conflict**
   - Input: 2 agents, different sources (GCC-STAT vs World Bank)
   - Expected: Prefer authoritative source (GCC-STAT)

4. **Both Valid**
   - Input: 2 agents, different time periods
   - Expected: both_valid resolution with context

5. **Complex Multi-Way**
   - Input: 3 agents, 3 different values
   - Expected: Resolve via confidence + source authority

---

## Timeline

- **Hour 1**: Implement contradiction detection + data structures
- **Hour 2**: Implement debate node + LLM arbitration
- **Hour 3**: Integration with workflow + testing

---

## Dependencies

- ✅ Phase 1 complete (citations available for comparison)
- ✅ LLMClient available for arbitration
- ✅ WorkflowState extensible

---

## Deliverables

1. Debate node implementation in [graph_llm.py](src/qnwis/orchestration/graph_llm.py)
2. Helper functions for contradiction detection and consensus
3. Integration with workflow graph
4. Test suite for debate scenarios
5. Documentation of debate process

---

**Ready to implement**: Phase 2 Step 2A
**Estimated Duration**: 3 hours
**Next**: Step 2B (Critique/Devil's Advocate Node)
