# 🔴 CRITICAL: Workflow Loop Detected

## Issue Report

**Time**: 2025-11-16 21:45  
**Symptom**: Workflow cycles backward instead of progressing forward  
**Pattern**: classify → agents → classify → select_agents → classify (repeating)

---

## Analysis

### Expected Flow
```
classify → prefetch → rag → select_agents → agents → debate → critique → verify → synthesize → END
```

### Actual Flow (Reported by User)
```
classify → agents → classify → select_agents → classify → ... (loops forever)
```

---

## Hypothesis 1: Node Not Returning State Correctly

**Problem**: If a node doesn't return the complete state dict, LangGraph might restart from entry point.

**Check**: Look at each node's return statement - must return full `{**state, ...}` dict.

---

## Hypothesis 2: Exception Being Swallowed

**Problem**: If a node throws an exception that's caught somewhere, graph might retry from beginning.

**Check**: Add try/except logging to each node to see if exceptions are being thrown.

---

## Hypothesis 3: Event Callback Causing Serialization Issues

**Problem**: `event_callback` is an async function stored in state. If LangGraph tries to serialize state between nodes, this could fail and cause restart.

**Check**: Remove `event_callback` from WorkflowState type or store it separately.

---

## Hypothesis 4: Conditional Routing Function Error

**Problem**: The `should_route_deterministic` function might be returning wrong value or causing error.

**Check**: Add logging inside routing function to see what it returns.

---

## Immediate Fix Needed

Add comprehensive debug logging to track:
1. Entry/exit of each node
2. State keys before/after each node
3. Any exceptions being caught
4. Graph routing decisions

Then run query and collect logs to identify where loop starts.

---

## Status

🔴 **BLOCKED** - Cannot proceed until workflow loop is fixed.

User cannot test UI improvements because workflow never completes.
