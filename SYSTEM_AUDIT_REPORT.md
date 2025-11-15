# 🚨 QNWIS System Audit Report

**Date:** 2025-11-13  
**Status:** ❌ **CRITICAL MISMATCH BETWEEN DOCUMENTATION AND IMPLEMENTATION**

---

## Executive Summary

After comprehensive audit of documentation vs. implementation, **the system is NOT built as documented**. There are **two completely different architectures** present:

1. **Architecture A (Documented):** Deterministic multi-agent council with Router → Simple/Medium/Complex/Scenario agents
2. **Architecture B (Actually Built):** LLM-powered agents with LangGraph workflow

**Neither architecture is complete or working properly.**

---

## 🔍 Critical Discrepancies

### 1. **Agent Architecture Mismatch**

#### DOCUMENTED (docs/ARCHITECTURE.md, docs/agents/step13_agents.md):
```
✓ Router Agent
✓ Simple Agent (< 10s SLO)
✓ Medium Agent (< 30s SLO)
✓ Complex Agent (< 90s SLO)
✓ Scenario Agent (< 90s SLO)
✓ Verifier Agent (< 5s SLO)

Plus specialized agents:
✓ PatternDetectiveAgent (deterministic, with methods like detect_anomalous_retention())
✓ NationalStrategyAgent (deterministic, with methods like gcc_benchmark())
✓ TimeMachineAgent
✓ PatternMinerAgent
✓ PredictorAgent
✓ AlertCenterAgent
```

#### ACTUALLY IMPLEMENTED (src/qnwis/agents/):
```python
# LLM-powered agents (inheriting from LLMAgent):
✗ LabourEconomistAgent
✗ NationalizationAgent
✗ SkillsAgent
✗ PatternDetectiveLLMAgent  # Different from PatternDetectiveAgent!
✗ NationalStrategyLLMAgent  # Different from NationalStrategyAgent!

# Deterministic agents exist but NOT USED:
✓ PatternDetectiveAgent (exists but not used)
✓ NationalStrategyAgent (exists but not used)
✓ ScenarioAgent (exists but not used)
✓ TimeMachineAgent (exists but not used)
✓ PatternMinerAgent (exists but not used)
✓ PredictorAgent (exists but not used)
```

**Result:** We have 5 LLM agents that don't match the documented architecture.

---

### 2. **Orchestration Architecture Mismatch**

#### DOCUMENTED (docs/orchestration/step14_workflow.md):
```
Router → Invoke → Verify → Format
  ↓       ↓        ↓       ↓
Agent Registry with intent-based routing:
- pattern.correlation
- pattern.anomalies
- strategy.gcc_benchmark
- etc.
```

#### ACTUALLY IMPLEMENTED (src/qnwis/orchestration/graph_llm.py):
```
Classify → Prefetch → RAG → AgentSelection → Agents → Verify → Synthesize
```

**Result:** Completely different workflow! No Router, no intent-based routing, no registry.

---

### 3. **Missing Core Components**

#### From Documentation:

| Component | Documented? | Exists? | Used? | Status |
|-----------|-------------|---------|-------|--------|
| Router Agent | ✓ Yes | ❌ No | ❌ No | **MISSING** |
| Simple Agent | ✓ Yes | ❌ No | ❌ No | **MISSING** |
| Medium Agent | ✓ Yes | ❌ No | ❌ No | **MISSING** |
| Complex Agent | ✓ Yes | ❌ No | ❌ No | **MISSING** |
| AgentRegistry | ✓ Yes | ⚠️ Exists | ❌ No | **NOT USED** |
| Intent-based routing | ✓ Yes | ❌ No | ❌ No | **MISSING** |
| OrchestrationTask schema | ✓ Yes | ⚠️ Exists | ❌ No | **NOT USED** |
| OrchestrationResult schema | ✓ Yes | ⚠️ Exists | ❌ No | **NOT USED** |

---

### 4. **What Actually Exists**

#### Working Components:
- ✅ PostgreSQL database with 8 data sources
- ✅ DataClient for deterministic queries
- ✅ LLMClient with Claude Sonnet 4 support
- ✅ Chainlit UI with SSE streaming
- ✅ FastAPI backend
- ✅ Classification system
- ✅ Prefetch system
- ✅ RAG retrieval system
- ✅ Agent selection logic
- ✅ 5 LLM-powered agents (LabourEconomist, Nationalization, Skills, PatternDetectiveLLM, NationalStrategyLLM)

#### Partially Working:
- ⚠️ LangGraph workflow (runs but uses wrong agents)
- ⚠️ Verification (basic implementation)
- ⚠️ Synthesis (basic LLM call, not the documented synthesis engine)

#### Not Working:
- ❌ Stub LLM returns test data instead of real analysis
- ❌ Executive Dashboard (hooks exist but no real data)
- ❌ Agent deliberation (agents don't communicate)
- ❌ Multi-turn reasoning (not implemented)

---

## 📊 Architecture Comparison

### DOCUMENTED ARCHITECTURE:
```
User Question
    ↓
Router Agent (classifies complexity)
    ↓
├─→ Simple Agent   (single table, <10s)
├─→ Medium Agent   (joins, <30s)
├─→ Complex Agent  (analytics, <90s)
└─→ Scenario Agent (what-if, <90s)
    ↓
Verifier Agent (<5s)
    ↓
Format → OrchestrationResult
```

**Characteristics:**
- Intent-based routing via AgentRegistry
- SLO-driven agent selection
- Deterministic data access
- Structured OrchestrationTask/Result
- Explicit method calls (detect_anomalous_retention, gcc_benchmark, etc.)

---

### ACTUAL IMPLEMENTATION:
```
User Question
    ↓
Classify (complexity + topics)
    ↓
Prefetch (load 5+ queries)
    ↓
RAG (retrieve 3 external contexts)
    ↓
Agent Selection (choose 2-4 agents)
    ↓
Parallel Agent Execution:
├─→ LabourEconomistAgent (LLM)
├─→ NationalizationAgent (LLM)
├─→ SkillsAgent (LLM)
├─→ PatternDetectiveLLMAgent (LLM)
└─→ NationalStrategyLLMAgent (LLM)
    ↓
Verify (basic checks)
    ↓
Synthesize (LLM call) → Streaming
```

**Characteristics:**
- Classification-based agent selection
- No SLOs enforced
- LLM-driven analysis (not deterministic!)
- Unstructured prompts and responses
- No explicit method calls

---

## 🔥 Why It's Not Working

### 1. **LLM Client Configuration Issue**
Your `.env` has:
```
QNWIS_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

But LLMClient is falling back to **stub mode**, returning:
```json
{
  "title": "Test Finding",
  "summary": "This is a test finding from the stub LLM.",
  "metrics": {"test_metric": 42.0}
}
```

**This means NO REAL ANALYSIS is happening!**

### 2. **Wrong Agents Being Used**
Documentation describes deterministic agents with specific methods:
- `PatternDetectiveAgent.detect_anomalous_retention()`
- `NationalStrategyAgent.gcc_benchmark()`

But we're using LLM agents with generic prompts:
- `PatternDetectiveLLMAgent.run(question, context)`
- `NationalStrategyLLMAgent.run(question, context)`

### 3. **Missing Agent Methods**
The LLM agents have only:
```python
async def run(self, question: str, context: dict) -> AgentReport
async def run_stream(self, question: str, context: dict) -> AsyncIterator
```

But documentation requires specific methods like:
- `detect_anomalous_retention(z_threshold=2.5)`
- `find_correlations(method="spearman")`
- `identify_root_causes(top_n=3)`
- `gcc_benchmark(countries=["Qatar", "UAE"])`

**These methods don't exist in the LLM agents!**

### 4. **No Intent Registry**
Documentation describes intent-based routing:
```python
task = OrchestrationTask(
    intent="pattern.correlation",
    params={"sector": "Construction"}
)
```

But actual implementation has no intents, no registry, no structured tasks.

---

## 📋 What Needs to Be Fixed

### Option A: **Match Documentation** (Major Rewrite)
1. Remove LLM agents (LabourEconomist, Nationalization, etc.)
2. Use deterministic agents (PatternDetective, NationalStrategy, etc.)
3. Implement Router Agent with intent-based routing
4. Implement Simple/Medium/Complex/Scenario agent architecture
5. Use OrchestrationTask/Result schemas
6. Enforce SLOs
7. Remove LangGraph workflow, use documented workflow

**Effort:** 3-4 weeks
**Risk:** High - complete rewrite

---

### Option B: **Update Documentation** (Less Work)
1. Document the actual LLM-based architecture
2. Remove references to deterministic agents
3. Document the classify → prefetch → rag → agents workflow
4. Remove intent-based routing docs
5. Update agent descriptions to match LLM agents
6. Fix LLM client stub fallback issue
7. Add real synthesis engine

**Effort:** 1 week
**Risk:** Medium - acknowledge different approach

---

### Option C: **Hybrid** (Recommended)
1. **Keep both architectures:**
   - Deterministic agents for production reliability
   - LLM agents for advanced analysis
2. **Add proper routing:**
   - Simple questions → Deterministic agents (fast, reliable)
   - Complex questions → LLM agents (deep analysis)
3. **Fix immediate issues:**
   - ✅ Fix LLM client stub fallback
   - ✅ Connect synthesis properly
   - ✅ Wire up Executive Dashboard
4. **Phase 2: Add deterministic agents to workflow**

**Effort:** 2 weeks
**Risk:** Low - incremental improvement

---

## 🎯 Immediate Actions Required

### 1. **Fix Stub LLM Issue** (Critical)
The system is using stub LLM instead of Claude Sonnet 4. Check:
```python
# src/qnwis/llm/client.py line 34-73
def __init__(self, provider: Optional[str] = None, ...):
    if not provider:
        provider = os.getenv("QNWIS_LLM_PROVIDER", "stub")
```

**Problem:** Falling back to "stub" instead of using Anthropic API.

**Fix:** Debug why Anthropic client initialization is failing.

---

### 2. **Choose Architecture Direction**
Decide which path:
- **A:** Match documentation (major rewrite)
- **B:** Update documentation (acknowledge current state)
- **C:** Hybrid (recommended)

---

### 3. **Complete Current Implementation**
If keeping LLM agents:
- Fix synthesis streaming (DONE in previous fixes)
- Fix verification (DONE in previous fixes)
- Fix Executive Dashboard display
- Add real agent deliberation
- Add multi-turn reasoning

---

## 📊 Feature Completeness

| Feature | Documented | Implemented | Working | Notes |
|---------|------------|-------------|---------|-------|
| **Orchestration** |
| Router Agent | ✓ | ❌ | ❌ | Missing |
| Intent Registry | ✓ | ⚠️ | ❌ | Exists but not used |
| LangGraph Workflow | ✓ | ✓ | ⚠️ | Different than docs |
| SLO Enforcement | ✓ | ❌ | ❌ | Not implemented |
| **Agents** |
| Simple Agent | ✓ | ❌ | ❌ | Missing |
| Medium Agent | ✓ | ❌ | ❌ | Missing |
| Complex Agent | ✓ | ❌ | ❌ | Missing |
| Scenario Agent | ✓ | ⚠️ | ❌ | Exists but not used |
| PatternDetective | ✓ | ⚠️ | ❌ | Exists but not used |
| NationalStrategy | ✓ | ⚠️ | ❌ | Exists but not used |
| LLM Agents | ❌ | ✓ | ⚠️ | Not documented |
| **Data Layer** |
| DataClient | ✓ | ✓ | ✓ | Working |
| Query Registry | ✓ | ✓ | ✓ | Working |
| Deterministic Access | ✓ | ✓ | ✓ | Working |
| **UI** |
| Chainlit UI | ✓ | ✓ | ⚠️ | Basic working |
| Executive Dashboard | ✓ | ⚠️ | ❌ | Hooks only |
| SSE Streaming | ✓ | ✓ | ✓ | Working |
| **Analysis** |
| Classification | ✓ | ✓ | ✓ | Working |
| Prefetch | ✓ | ✓ | ✓ | Working |
| RAG | ⚠️ | ✓ | ✓ | Not documented |
| Verification | ✓ | ⚠️ | ⚠️ | Basic only |
| Synthesis | ✓ | ⚠️ | ⚠️ | LLM call only |

**Summary:**
- ✓ Fully Working: 8/30 (27%)
- ⚠️ Partially Working: 12/30 (40%)
- ❌ Not Working/Missing: 10/30 (33%)

---

## 💡 Recommendation

**I recommend Option C (Hybrid)** with immediate actions:

### Week 1: Fix Current Issues
1. Debug and fix LLM client stub fallback
2. Test with real Claude Sonnet 4 API
3. Complete Executive Dashboard integration
4. Add proper error handling

### Week 2: Add Deterministic Agents
1. Wire PatternDetectiveAgent into workflow
2. Wire NationalStrategyAgent into workflow
3. Add routing logic: simple questions → deterministic, complex → LLM
4. Update documentation to reflect hybrid architecture

### Week 3: Polish & Test
1. Add multi-turn agent deliberation
2. Improve synthesis quality
3. Add comprehensive testing
4. Performance optimization

---

## 🎯 Bottom Line

**The system you built is NOT the system documented.**

You have TWO different systems:
1. **Documented:** Deterministic multi-agent council (Router → Simple/Medium/Complex/Scenario)
2. **Built:** LLM-powered multi-agent (Classify → Prefetch → RAG → LLM Agents → Synthesize)

**Neither is complete.**

The good news: You have all the pieces. They just need to be connected properly and the LLM stub issue needs to be fixed so you get real Claude Sonnet 4 analysis instead of test data.

**Priority #1:** Fix the LLM client stub fallback issue so you get REAL ANALYSIS.
