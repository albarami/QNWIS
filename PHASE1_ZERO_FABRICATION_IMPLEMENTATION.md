# Phase 1: Zero Fabrication Foundation - Implementation Guide

## Overview

**Goal**: Establish absolute trust through strict citation enforcement and enhanced verification.

**Timeline**: Day 1 (5 hours total)
- Step 1A: Enforce inline citation format (2h)
- Step 1B: Enhance verification node (2h)
- Step 1C: Add reasoning chain (1h)

**Priority**: CRITICAL - This is the foundation. Without this, nothing else matters.

---

## Step 1A: Enforce Inline Citation Format (2 hours)

### The Problem
Current agents say: "Qatar unemployment is 0.1%"
**We need**: "Qatar unemployment was [Per extraction: '0.10%' from GCC-STAT Q1-2024]"

### The Solution: Strict Citation Requirement in Every LLM Prompt

### File 1: `src/qnwis/agents/base_llm.py`

**Add constant at top of file** (after line 20):

```python
# Zero Fabrication Citation Requirement
ZERO_FABRICATION_CITATION_RULES = """
═══════════════════════════════════════════════════════════════════════
MANDATORY CITATION FORMAT - ZERO FABRICATION GUARANTEE
═══════════════════════════════════════════════════════════════════════

RULE 1: Every metric, number, percentage, or statistic MUST include inline citation.

RULE 2: Citation format is EXACTLY:
  [Per extraction: '{exact_value}' from {source} {period}]

RULE 3: Example formats:
  ✅ CORRECT: "Qatar unemployment was [Per extraction: '0.10%' from GCC-STAT Q1-2024]"
  ✅ CORRECT: "Employment reached [Per extraction: '2.3M workers' from LMIS Database 2024-Q1]"
  ✅ CORRECT: "Qatarization rate stands at [Per extraction: '23.5%' from Ministry Report 2024]"

  ❌ WRONG: "Qatar unemployment is 0.10%" (no citation)
  ❌ WRONG: "Qatar unemployment is very low" (vague, no number)
  ❌ WRONG: "According to data, unemployment is 0.10%" (citation not inline)

RULE 4: If metric NOT in provided extraction:
  Write EXACTLY: "NOT IN DATA - cannot provide {metric_name} figure"

  Example: "Youth unemployment: NOT IN DATA - cannot provide youth unemployment figure"

RULE 5: NEVER round, estimate, or approximate without showing:
  "Approximately [Per extraction: '0.098%' from source] rounds to 0.1%"

═══════════════════════════════════════════════════════════════════════
VIOLATION CONSEQUENCES:
- Response will be flagged
- Confidence score reduced by 30%
- May be rejected entirely
═══════════════════════════════════════════════════════════════════════
"""
```

**Update `_build_prompt()` signature** (around line 250):

```python
@abstractmethod
def _build_prompt(
    self,
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build LLM prompt from question and data.

    MUST include ZERO_FABRICATION_CITATION_RULES in system prompt.

    Args:
        question: User's question
        data: Dict of QueryResult objects from deterministic layer
        context: Additional context (classification, prefetch, RAG)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    pass
```

### File 2: `src/qnwis/agents/labour_economist.py`

**Update `_build_prompt()` method**:

```python
def _build_prompt(
    self,
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """Build prompt for LabourEconomist with strict citation enforcement."""

    # Extract data into formatted text with sources
    data_text = self._format_data_with_sources(data)

    system_prompt = f"""You are a PhD-level Labour Economist specializing in Gulf labour markets.

{ZERO_FABRICATION_CITATION_RULES}

Your expertise:
- Employment dynamics and gender analysis
- Labour market efficiency
- Workforce participation patterns
- Cross-GCC comparative analysis

ANALYSIS FRAMEWORK:
1. Identify key metrics (with inline citations)
2. Provide comparative context (with inline citations)
3. Explain economic significance
4. Offer policy-relevant recommendations

CRITICAL: Every number must have inline citation. No exceptions.
"""

    user_prompt = f"""Question: {question}

Deterministic Data Extraction:
{data_text}

Provide structured analysis with:
1. Title (concise, descriptive)
2. Summary (2-3 sentences)
3. Key Metrics (with inline citations)
4. Detailed Analysis (with inline citations for every claim)
5. Recommendations (actionable, specific)

Format:
{{
  "title": "...",
  "summary": "...",
  "metrics": {{"metric_name": value}},
  "analysis": "Full text with [Per extraction: ...] citations",
  "recommendations": ["1. ...", "2. ...", "3. ..."],
  "confidence": 0.95
}}

Remember: EVERY number needs [Per extraction: ...] citation!
"""

    return system_prompt, user_prompt


def _format_data_with_sources(self, data: Dict) -> str:
    """Format query results with source attribution for citation."""
    lines = []

    for query_id, result in data.items():
        # Get source info
        source = result.provenance.source if hasattr(result, 'provenance') else "Unknown"
        dataset = result.provenance.dataset_id if hasattr(result, 'provenance') else ""
        period = result.freshness.asof_date if hasattr(result, 'freshness') else "Unknown period"

        lines.append(f"\\n--- Query: {query_id} ---")
        lines.append(f"Source: {source} {dataset}")
        lines.append(f"Period: {period}")
        lines.append(f"Rows:")

        # Format rows with values
        for i, row in enumerate(result.rows[:10], 1):  # Show first 10 rows
            row_text = ", ".join([f"{k}={v}" for k, v in row.data.items()])
            lines.append(f"  {i}. {row_text}")

        if len(result.rows) > 10:
            lines.append(f"  ... and {len(result.rows) - 10} more rows")

    return "\\n".join(lines)
```

**Do the same for all 5 LLM agents**:
- `src/qnwis/agents/nationalization.py`
- `src/qnwis/agents/skills.py`
- `src/qnwis/agents/pattern_detective_llm.py`
- `src/qnwis/agents/national_strategy_llm.py`

**Template for each**:
1. Add `ZERO_FABRICATION_CITATION_RULES` to system_prompt
2. Add `_format_data_with_sources()` method
3. Emphasize "EVERY number needs [Per extraction: ...] citation!"

---

## Step 1B: Enhance Verification Node (2 hours)

### The Problem
Current verification completes in 0ms - it's not actually checking anything.

### The Solution: Real Citation Validation

### File: `src/qnwis/orchestration/graph_llm.py`

**Replace `_verify_node()` method** (starting around line 416):

```python
async def _verify_node(self, state: WorkflowState) -> WorkflowState:
    """
    ENHANCED VERIFICATION: Actually check every number against citations.

    Checks:
    1. Every numeric claim has [Per extraction: ...] citation
    2. Cited numbers exist in source data
    3. No fabricated metrics
    4. No unsupported claims

    Args:
        state: Current workflow state

    Returns:
        Updated state with verification results and confidence adjustments
    """
    if state.get("event_callback"):
        await state["event_callback"]("verify", "running")

    start_time = datetime.now(timezone.utc)

    try:
        reports = state.get("agent_reports", [])
        prefetch_data = state.get("prefetch", {}).get("data", {})

        # Build allowed numbers from prefetch data
        allowed_numbers = set()
        for query_id, result in prefetch_data.items():
            for row in result.rows:
                for key, value in row.data.items():
                    try:
                        # Extract numeric value
                        if isinstance(value, (int, float)):
                            allowed_numbers.add(value)
                        elif isinstance(value, str):
                            # Try to parse percentages, numbers from strings
                            import re
                            numbers = re.findall(r'\\d+\\.?\\d*', value)
                            for num in numbers:
                                allowed_numbers.add(float(num))
                    except:
                        pass

        # Verification results
        all_violations = []
        citation_violations = []
        fabrication_violations = []

        for report in reports:
            if not report:
                continue

            agent_name = report.agent if hasattr(report, 'agent') else 'Unknown'

            # Get narrative text
            narrative = ""
            if hasattr(report, 'narrative') and report.narrative:
                narrative = report.narrative
            elif hasattr(report, 'findings') and report.findings:
                for finding in report.findings:
                    if isinstance(finding, dict):
                        narrative += finding.get('analysis', '')
                        narrative += finding.get('summary', '')

            # Extract all numbers from narrative
            import re
            numbers_in_text = re.findall(r'\\d+\\.?\\d*%?', narrative)

            for number_str in numbers_in_text:
                # Check if this number has a citation
                citation_pattern = f"\\\\[Per extraction:.*{re.escape(number_str)}.*\\\\]"
                has_citation = re.search(citation_pattern, narrative)

                if not has_citation:
                    citation_violations.append({
                        "agent": agent_name,
                        "number": number_str,
                        "issue": "Missing [Per extraction: ...] citation",
                        "severity": "high"
                    })
                    all_violations.append(citation_violations[-1])

                # Check if number exists in allowed set (with tolerance)
                try:
                    num_value = float(number_str.replace('%', ''))
                    found_in_data = False

                    for allowed in allowed_numbers:
                        if abs(num_value - allowed) < 0.02 * allowed:  # 2% tolerance
                            found_in_data = True
                            break

                    if not found_in_data:
                        fabrication_violations.append({
                            "agent": agent_name,
                            "number": number_str,
                            "issue": f"Number {number_str} not found in source data",
                            "severity": "critical"
                        })
                        all_violations.append(fabrication_violations[-1])

                except ValueError:
                    pass  # Not a number

        # Calculate confidence adjustment
        total_claims = len(set([v['number'] for v in all_violations]))
        citation_penalty = len(citation_violations) * 0.05  # -5% per missing citation
        fabrication_penalty = len(fabrication_violations) * 0.30  # -30% per fabrication

        confidence_adjustment = 1.0 - min(citation_penalty + fabrication_penalty, 0.70)

        verification_result = {
            "status": "complete",
            "total_violations": len(all_violations),
            "citation_violations": len(citation_violations),
            "fabrication_violations": len(fabrication_violations),
            "confidence_adjustment": confidence_adjustment,
            "severity": "critical" if fabrication_violations else ("high" if citation_violations else "ok"),
            "violations_detail": all_violations[:20],  # First 20 for logging
            "pass": len(fabrication_violations) == 0  # Pass if no fabrications
        }

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        logger.info(
            f"Verification complete: {len(citation_violations)} citation issues, "
            f"{len(fabrication_violations)} fabrications, "
            f"confidence adjustment: {confidence_adjustment:.2f}, "
            f"latency={latency_ms:.0f}ms"
        )

        # If fabrications detected, LOG LOUDLY
        if fabrication_violations:
            logger.error(
                f"FABRICATION DETECTED: {len(fabrication_violations)} numbers not in source data!"
            )
            for v in fabrication_violations:
                logger.error(f"  {v['agent']}: {v['number']} - {v['issue']}")

        if state.get("event_callback"):
            await state["event_callback"](
                "verify",
                "complete",
                verification_result,
                latency_ms
            )

        return {
            **state,
            "verification": {
                **verification_result,
                "latency_ms": latency_ms
            },
            "confidence_adjustment": confidence_adjustment
        }

    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        if state.get("event_callback"):
            await state["event_callback"]("verify", "error", {"error": str(e)})
        return {
            **state,
            "verification": {"status": "failed", "error": str(e)},
            "error": f"Verification error: {e}"
        }
```

---

## Step 1C: Add Reasoning Chain to State (1 hour)

### The Problem
Users can't see what the system is doing internally.

### The Solution: Track every step in `reasoning_chain`

### File: `src/qnwis/orchestration/graph_llm.py`

**Update WorkflowState TypedDict** (around line 26):

```python
class WorkflowState(TypedDict):
    """State passed between workflow nodes."""

    question: str
    classification: Optional[Dict[str, Any]]
    prefetch: Optional[Dict[str, Any]]
    rag_context: Optional[Dict[str, Any]]
    selected_agents: Optional[list]
    agent_reports: list  # List of AgentReport objects
    verification: Optional[Dict[str, Any]]
    synthesis: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    event_callback: Optional[Any]  # For streaming events

    # NEW: Reasoning chain
    reasoning_chain: list  # List of step descriptions
    confidence_adjustment: float  # From verification
```

**Update each node to append to reasoning_chain**:

**In `_classify_node()`** (after line 147):
```python
return {
    **state,
    "classification": {...},
    "reasoning_chain": [
        f"🔍 Classification: {classification.get('complexity')} complexity, "
        f"intent: {classification.get('intent')}"
    ]
}
```

**In `_prefetch_node()`** (after line 208):
```python
reasoning_chain = state.get("reasoning_chain", [])
reasoning_chain.append(
    f"💾 Prefetch: Fetched {len(prefetched_data)} deterministic queries "
    f"({', '.join(list(prefetched_data.keys())[:3])}...)"
)

return {
    **state,
    "prefetch": {...},
    "reasoning_chain": reasoning_chain
}
```

**In `_rag_node()`** (after line 259):
```python
reasoning_chain = state.get("reasoning_chain", [])
reasoning_chain.append(
    f"🔍 RAG: Retrieved {len(rag_result.get('snippets', []))} external snippets from "
    f"{', '.join(rag_result.get('sources', []))}"
)
```

**In `_select_agents_node()`** (after line 300):
```python
reasoning_chain = state.get("reasoning_chain", [])
reasoning_chain.append(
    f"🎯 Agent Selection: Selected {len(selected_agent_names)}/{len(self.agent_selector.AGENT_EXPERTISE)} agents "
    f"({', '.join(selected_agent_names)})"
)
```

**In `_agents_node()`** (after each agent completes, around line 390):
```python
reasoning_chain = state.get("reasoning_chain", [])
reasoning_chain.append(
    f"🤖 {agent_name}: Analysis completed ({latency_ms:.0f}ms)"
)
```

**In `_verify_node()`** (after line 475):
```python
reasoning_chain = state.get("reasoning_chain", [])
reasoning_chain.append(
    f"✅ Verification: {len(citation_violations)} citation issues, "
    f"{len(fabrication_violations)} fabrications detected, "
    f"confidence adjustment: {confidence_adjustment:.2f}"
)
```

**In `_synthesize_node()`** (after line 556):
```python
reasoning_chain = state.get("reasoning_chain", [])
reasoning_chain.append(
    f"📝 Synthesis: Generated {len(synthesis_text)} character response"
)

return {
    **state,
    "synthesis": synthesis_text,
    "reasoning_chain": reasoning_chain,
    ...
}
```

---

## Testing Phase 1

### Test 1: Citation Enforcement

**Query**: "What is Qatar's unemployment rate?"

**Expected Output**:
```
Qatar's unemployment rate was [Per extraction: '0.10%' from GCC-STAT Q1-2024],
significantly lower than the GCC average of [Per extraction: '2.73%' from GCC-STAT Q1-2024].
```

**Verification**:
- ✅ Every number has [Per extraction: ...] citation
- ✅ Verification node reports 0 violations
- ✅ Confidence adjustment = 1.0

### Test 2: Fabrication Detection

**Manually inject fabricated number**: Edit agent prompt to say "0.08%" (not in data)

**Expected Behavior**:
- ❌ Verification node detects fabrication
- ❌ Logs ERROR: "FABRICATION DETECTED"
- ❌ Confidence adjustment = 0.70 (30% penalty)
- ❌ Response flagged as "critical" severity

### Test 3: Reasoning Chain

**Query**: Any query

**Expected Output in logs**:
```
reasoning_chain: [
    "🔍 Classification: medium complexity, intent: comparison",
    "💾 Prefetch: Fetched 8 queries (syn_unemployment_gcc_latest, ...)",
    "🔍 RAG: Retrieved 3 snippets from GCC-STAT, World Bank",
    "🎯 Agent Selection: Selected 2/5 agents (LabourEconomist, Nationalization)",
    "🤖 LabourEconomist: Analysis completed (2340ms)",
    "🤖 Nationalization: Analysis completed (2180ms)",
    "✅ Verification: 0 citation issues, 0 fabrications, confidence: 1.00",
    "📝 Synthesis: Generated 1847 character response"
]
```

---

## Success Criteria - Phase 1 Complete

### Before Phase 1
- ❌ Citations: Generic or missing
- ❌ Verification: 0ms (not running)
- ❌ Reasoning: Invisible
- ❌ Fabrication risk: HIGH

### After Phase 1
- ✅ Citations: Every number has [Per extraction: ...] format
- ✅ Verification: Actually checks citations and numbers (>50ms)
- ✅ Reasoning: Full step-by-step chain visible
- ✅ Fabrication risk: ZERO (detected and flagged)

---

## Files Modified - Phase 1

1. **src/qnwis/agents/base_llm.py**
   - Add `ZERO_FABRICATION_CITATION_RULES` constant
   - Update `_build_prompt()` signature docs

2. **src/qnwis/agents/labour_economist.py**
   - Update `_build_prompt()` to include citation rules
   - Add `_format_data_with_sources()` method

3. **src/qnwis/agents/nationalization.py** (same as labour_economist)

4. **src/qnwis/agents/skills.py** (same as labour_economist)

5. **src/qnwis/agents/pattern_detective_llm.py** (same as labour_economist)

6. **src/qnwis/agents/national_strategy_llm.py** (same as labour_economist)

7. **src/qnwis/orchestration/graph_llm.py**
   - Add `reasoning_chain` to WorkflowState
   - Replace `_verify_node()` with enhanced version
   - Add reasoning_chain.append() to all nodes

**Total**: 7 files

**Time**: 5 hours

---

## Next: Phase 2 - Debate & Critique

Once Phase 1 is complete and tested, we move to Phase 2 where we add:
- Multi-agent debate node (3h)
- Critique/devil's advocate node (2h)

**These build on the citation foundation to create emergent intelligence.**

Without Phase 1's zero-fabrication guarantee, debate and critique would amplify errors. With it, they amplify truth.

---

## Ready to Implement

All code is specified above. Ready to execute Phase 1 Step 1A now.

**Do you want me to start implementing the citation enforcement in base_llm.py and the 5 agent files?**
