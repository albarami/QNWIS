# 🔍 Debug Logging Enabled

## Status: Both Servers Running with Enhanced Logging

**Date**: 2025-11-16 21:48  
**Backend**: ✅ Running on http://localhost:8000  
**Frontend**: ✅ Running on http://localhost:3000

---

## Debug Logging Added

### Nodes with Entry/Exit Logging

1. **Classify Node**
   - Entry: Shows state keys and question
   - Exit: Shows result keys and confirmation
   - Location: Lines 259-263, 318-320

2. **Routing Function**
   - Shows state keys and routing decision
   - Location: Lines 211-215

3. **Prefetch Node**
   - Entry: Shows state keys
   - Location: Lines 448-451

4. **RAG Node**
   - Entry: Shows state keys
   - Location: Lines 566-569

5. **Select Agents Node**
   - Entry: Shows state keys
   - Location: Lines 625-628

6. **Agents Node**
   - Entry: Shows state keys
   - Location: Lines 688-691

---

## What to Look For

When you submit a query, watch the **backend terminal** for this pattern:

### ✅ Expected Flow:
```
================================================================================
[CLASSIFY NODE] ENTRY
================================================================================
[CLASSIFY NODE] State keys: ['question', 'classification', ...]
[CLASSIFY NODE] Question: What are the implications...
[CLASSIFY NODE] EXIT - Returning state with 8 keys

================================================================================
[ROUTING FUNCTION] CALLED
================================================================================
[ROUTING FUNCTION] State keys: ['question', 'classification', ...]
[ROUTING FUNCTION] Decision: llm_agents
================================================================================

================================================================================
[PREFETCH NODE] ENTRY
[PREFETCH NODE] State keys: ['question', 'classification', 'prefetch', ...]
================================================================================

================================================================================
[RAG NODE] ENTRY
[RAG NODE] State keys: ['question', 'classification', 'rag_context', ...]
================================================================================

================================================================================
[SELECT_AGENTS NODE] ENTRY
[SELECT_AGENTS NODE] State keys: ['question', 'selected_agents', ...]
================================================================================

================================================================================
[AGENTS NODE] ENTRY
[AGENTS NODE] State keys: ['question', 'agent_reports', ...]
================================================================================
```

### ❌ Loop Pattern to Watch For:
```
[CLASSIFY NODE] ENTRY
[CLASSIFY NODE] EXIT

[ROUTING FUNCTION] CALLED

[PREFETCH NODE] ENTRY  ← Good so far

[CLASSIFY NODE] ENTRY  ← ❌ LOOP! Should NOT return to classify!
[CLASSIFY NODE] EXIT

[ROUTING FUNCTION] CALLED

[SELECT_AGENTS NODE] ENTRY  ← ❌ Wrong! Should go to RAG first

[CLASSIFY NODE] ENTRY  ← ❌ Loop again!
```

---

## Test Instructions

1. **Open backend terminal** - You should see uvicorn output
2. **Refresh browser** at http://localhost:3000
3. **Submit test query**: "What are the implications of raising the minimum wage for Qatari nationals to QR 20,000?"
4. **Watch backend terminal** for debug output
5. **Copy the entire console output** showing the node execution pattern
6. **Report back** with:
   - Screenshot of backend console
   - Confirmation if loop still happens
   - At which node it loops back to classify

---

## What Each Piece of Info Tells Us

### If we see:
```
[CLASSIFY NODE] State keys: [...long list...]
[CLASSIFY NODE] EXIT - Returning state with 15 keys
```
**Means**: Classify is working and returning full state ✅

### If we see:
```
[ROUTING FUNCTION] Decision: llm_agents
[PREFETCH NODE] ENTRY
[PREFETCH NODE] State keys: [...long list...]
```
**Means**: Routing is working and prefetch received state ✅

### If we see:
```
[PREFETCH NODE] ENTRY
[CLASSIFY NODE] ENTRY  ← Appears again!
```
**Means**: Prefetch either crashed or returned wrong type, graph restarted ❌

### If we see:
```
[CLASSIFY NODE] State keys: ['question', 'metadata']  ← Only 2 keys!
```
**Means**: State is being reset somewhere, losing data ❌

---

## Next Steps

Once you submit the query and see the output:

1. **If flow is linear** (classify → prefetch → rag → select → agents → ...)
   - ✅ Loop is FIXED!
   - Continue to verify data population

2. **If loop still occurs**
   - Note which node it loops FROM
   - Note what state keys are present when it loops
   - I'll analyze and fix the specific node causing the issue

---

## Files Modified

```
src/qnwis/orchestration/graph_llm.py
├── Added debug prints to _classify_node (entry + exit)
├── Added debug prints to should_route_deterministic
├── Added debug prints to _prefetch_node (entry)
├── Added debug prints to _rag_node (entry)
├── Added debug prints to _select_agents_node (entry)
└── Added debug prints to _invoke_agents_node (entry)
```

---

## Ready to Test

Both servers are running with enhanced logging.

**REFRESH YOUR BROWSER** and **SUBMIT A QUERY**.

The backend console will now show exactly what's happening at each step.

Watch for the pattern and report back!
