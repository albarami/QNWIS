# 🚨 CURRENT BLOCKER - Agents Returning Invalid Results

**Date**: 2025-11-16  
**Status**: 🔴 CRITICAL - System Non-Functional  
**Test**: test_full_depth.py FAILED

---

## ❌ The Problem

**Agents are returning invalid results** instead of proper structured AgentReport dicts.

### Error:
```python
KeyError: 'agent_name'
File "graph_llm.py", line 732, in _invoke_agents_node
    agents_invoked.append(result["agent_name"])
```

### What's Happening:
1. ✅ Workflow initializes correctly  
2. ✅ Classification runs (complexity: complex)  
3. ✅ Prefetch runs (24 facts extracted from 7 APIs)  
4. ✅ RAG runs  
5. ✅ Agent selection runs ("invoking ALL 4 specialist agents" - **should be 5!**)  
6. ❌ **Agents return invalid results** (missing 'agent_name' key)  
7. ❌ System crashes

---

## 🔍 Root Cause Investigation Needed

### Question 1: Why only 4 agents instead of 5?

**Log shows**:
```
[SELECT AGENTS] Complex query detected - invoking ALL 4 specialist agents
```

**Should show**:
```
[SELECT AGENTS] Complex query detected - invoking ALL 5 specialist agents
```

**Hypothesis**: One agent is not in the agent_map or failing to instantiate.

**Check**:
```python
# In graph_llm.py around line 690
agent_map = {
    "labour_economist": labour_economist,
    "financial_economist": financial_economist,
    "market_economist": market_economist,
    "operations_expert": operations_expert,
    "research_scientist": research_scientist,  # <- Is this one missing?
}
```

### Question 2: Why are agents returning invalid dicts?

**Expected**: 
```python
{
    "agent_name": "labour_economist",
    "narrative": "...",
    "confidence": 0.85,
    "citations": [...],
    ...
}
```

**Actual**: Something without 'agent_name' key (not even an Exception)

**Hypothesis**: Agents are catching their own exceptions and returning error dicts without proper structure.

**Check Agent Code**:
```python
# In labour_economist.py, market_economist.py, etc.
async def analyze(...):
    try:
        # ... agent logic ...
        return AgentReport(...)  # This should return dict[str, Any]
    except Exception as exc:
        return AgentReport(  # Error case - does this have agent_name?
            agent_name="???",  # <- Is this missing?
            narrative=error_text,
            ...
        )
```

### Question 3: Are agents even being called?

**We know**:
- Prefetch worked (24 facts)
- Agent selection claims to invoke 4 agents
- But agents return invalid results

**Hypothesis**: Agents are being called but immediately failing/returning malformed dicts.

**Debug Steps**:
1. Add logging at start of each agent's `analyze()` method
2. Check if agent imports are working
3. Verify agent instances are created correctly

---

## 🔧 Quick Fix Applied

Added validation to prevent crash:

```python
# In graph_llm.py line 731-735
# Check if result is a valid dict with required keys
if not isinstance(result, dict) or "agent_name" not in result:
    logger.error("%s returned invalid result: %s", agent_name, type(result))
    reasoning_chain.append(f"❌ {agent_name} returned invalid result")
    continue
```

**Impact**: System won't crash, but agents still won't work correctly.

---

## 🐛 Debug Steps to Execute

### Step 1: Check Agent Instantiation

```bash
python -c "
from src.qnwis.agents import labour_economist, financial_economist, market_economist, operations_expert, research_scientist

print('Agents:')
print('  labour_economist:', labour_economist)
print('  financial_economist:', financial_economist)
print('  market_economist:', market_economist)
print('  operations_expert:', operations_expert)
print('  research_scientist:', research_scientist)
"
```

**Expected**: All 5 agent modules should import without errors.

### Step 2: Test Single Agent Directly

```bash
python -c "
import asyncio
from src.qnwis.agents.labour_economist import analyze
from src.qnwis.llm.client import LLMClient

async def test():
    llm = LLMClient(provider='anthropic')
    result = await analyze('test query', [], llm)
    print('Result type:', type(result))
    print('Result keys:', result.keys() if isinstance(result, dict) else 'NOT A DICT')
    print('Has agent_name:', 'agent_name' in result if isinstance(result, dict) else False)
    
asyncio.run(test())
"
```

**Expected**: Result should be dict with 'agent_name' key.

### Step 3: Check Agent Map

```python
# Add debug logging to graph_llm.py around line 696
agent_map = {
    "labour_economist": labour_economist,
    "financial_economist": financial_economist,
    "market_economist": market_economist,
    "operations_expert": operations_expert,
    "research_scientist": research_scientist,
}

# ADD THIS:
logger.info(f"Agent map has {len(agent_map)} agents:")
for name, obj in agent_map.items():
    logger.info(f"  {name}: {obj}")
```

**Expected**: Should show 5 agents, not 4.

### Step 4: Enable Verbose Agent Logging

```python
# Add to each agent's analyze() method at the very start:
async def analyze(query: str, extracted_facts: list, llm_client: LLMClient) -> dict[str, Any]:
    logger.info(f"[AGENT START] {__name__} analyzing: {query[:50]}...")
    try:
        # ... existing code ...
```

**Expected**: Should see 5 "[AGENT START]" log messages, one per agent.

---

## 💡 Likely Issues

### Issue 1: Import Problem

One or more agents may not be importing correctly.

**Check**:
```python
# In graph_llm.py
from ..agents import (
    labour_economist,
    financial_economist,
    market_economist,
    operations_expert,
    research_scientist,  # <- Missing comma? Wrong import?
)
```

### Issue 2: Agent Return Format

Agents may be returning the WRONG format.

**Current (wrong)**:
```python
# Agents currently use: AgentReport = dict[str, Any]
# But this is just a type alias!

# When they do:
return AgentReport(agent_name="...", ...)
# This actually calls: dict(agent_name="...", ...)
# Which fails!
```

**Should be**:
```python
return {
    "agent_name": "labour_economist",
    "narrative": narrative,
    ...
}
```

### Issue 3: Exception Handling

Agents may be catching exceptions and returning malformed error dicts.

**Check agent exception handlers**:
```python
except Exception as exc:
    return AgentReport(  # <- This might not work!
        agent_name="labour_economist",  # Make sure this is here
        narrative=f"ERROR: {exc}",
        ...
    )
```

---

## 🎯 Action Items

### Immediate (Critical)
1. **Debug agent instantiation** - Are all 5 agents being created?
2. **Test single agent** - Can one agent run successfully?
3. **Check agent return format** - Are they returning proper dicts?

### Next
4. Fix agent return format if broken
5. Add verbose logging to track agent execution
6. Re-test with fixes

### Then
7. Run test_full_depth.py again
8. Verify all 5 agents execute
9. Confirm cost is $0.50-0.87

---

## 📊 Current State

**What Works**:
- ✅ Workflow initialization
- ✅ Classification  
- ✅ Prefetch (24 facts from 7 APIs)
- ✅ RAG
- ✅ Agent selection logic

**What's Broken**:
- ❌ Agents return invalid results
- ❌ Only 4 agents instead of 5
- ❌ No LLM calls being made
- ❌ System crashes before debate/critique/synthesis

**Blocker**: Cannot proceed to staging/production until agents work.

---

## 🔧 Quick Test Command

```bash
# Test if agents can be imported
python -c "from src.qnwis.agents import labour_economist; print('✅ Import works')"

# Test if agent has analyze function
python -c "from src.qnwis.agents.labour_economist import analyze; print('✅ Analyze exists')"

# Test agent signature
python -c "
import inspect
from src.qnwis.agents.labour_economist import analyze
sig = inspect.signature(analyze)
print('Signature:', sig)
print('Return annotation:', sig.return_annotation)
"
```

---

**Status**: 🔴 **CRITICAL BLOCKER**  
**Est. Time to Fix**: 2-4 hours of debugging  
**Priority**: IMMEDIATE - System cannot function without agents working

**Commit**: 0720293 (validation fix to prevent crash)  
**Next**: Debug why agents return invalid results
