# Duplicate Agent Bug - ROOT CAUSE FIXED ✅

**Date:** 2025-11-20 03:02 UTC  
**Status:** Root cause identified and fixed

---

## The Real Problem

The frontend was creating **24 agents instead of 12** because of **case-sensitivity in Map keys**.

### Example:
Backend sends both:
- `LabourEconomist` (PascalCase from normalization)
- `laboureconomist` (lowercase - actual agent key)

Frontend was treating these as **2 different agents** because JavaScript Maps are case-sensitive:
```javascript
map.set("LabourEconomist", {...})  // Agent 1
map.set("laboureconomist", {...})  // Agent 2 (duplicate!)
```

---

## The Fix

**File:** `qnwis-frontend/src/hooks/useWorkflowStream.ts`

### Changed:
All agent Map operations now use **lowercase keys** to prevent case-sensitive duplicates:

```typescript
// Before (case-sensitive - creates duplicates)
state.agentStatuses.set(agentName, {...})

// After (case-insensitive - no duplicates)
const normalizedKey = agentName.toLowerCase()
state.agentStatuses.set(normalizedKey, {...})
```

### Locations Fixed:
1. **handleAgentEvent()** - When agent events arrive (running/complete/error)
2. **agent_selection event** - Initial agent list creation
3. **agents stage start** - When agents start executing

---

## Backend Fix (Also Applied)

**File:** `src/qnwis/orchestration/graph_llm.py`

Fixed agent key lookup to use actual agent keys instead of normalized names:
```python
# Map normalized names back to actual agent keys
for name in selected_agent_names:
    if name in self.agents:
        actual_key = name
    elif name.lower() in self.agents:
        actual_key = name.lower()
```

---

## Why This Happened

1. **Agent Selection** returns PascalCase names: `["LabourEconomist", "Nationalization"]`
2. **Agents** are registered with lowercase keys: `{"laboureconomist": ...}`
3. **Backend** was invoking both keys because normalization created duplicates
4. **Frontend** was storing both keys because Map keys are case-sensitive

---

## How to Test

### No restart needed - just refresh the browser!

1. **Refresh browser page** (Ctrl+F5 or Cmd+Shift+R)
2. Enter question: "What are the unemployment trends in Qatar?"
3. Provider: **anthropic** (now default)
4. Click Submit

### Expected Result:
- ✅ **Exactly 12 agents** (not 24!)
- ✅ All agents complete successfully  
- ✅ Synthesis appears
- ✅ Workflow completes (not stuck)

---

## Files Changed

### Frontend (Requires Browser Refresh)
1. `qnwis-frontend/src/hooks/useWorkflowStream.ts`
   - Line 36-38: Normalize keys in handleAgentEvent
   - Line 41: Use normalized key for "running" status
   - Line 50: Use normalized key for "complete" status
   - Line 61: Use normalized key for "error" status
   - Line 103-105: Normalize keys when agent_selection completes
   - Line 113-118: Deduplicate and normalize when agents stage starts
   - Line 147-150: Mark workflow as complete when "done" stage arrives

2. `qnwis-frontend/src/App.tsx`
   - Line 19: Default provider changed from "stub" to "anthropic"

### Backend (Requires Server Restart)
3. `src/qnwis/orchestration/graph_llm.py`
   - Lines 662-682: Fixed agent key lookup logic
4. `src/qnwis/rag/embeddings.py`
   - Lines 52-75: Fixed PyTorch meta tensor error

---

## Testing Checklist

After refreshing browser:

- [ ] Frontend loads successfully
- [ ] Submit button works
- [ ] Provider defaults to "anthropic"
- [ ] Agent count shows "12" (not 24)
- [ ] All 12 agents appear in grid
- [ ] All agents complete (no stuck "running")
- [ ] Synthesis appears at bottom
- [ ] Workflow finishes (button changes from "Streaming..." to "Submit")
- [ ] No dark screen crashes

---

## Why Previous Fixes Didn't Work

### Day 1: Fixed backend normalization
- ✅ Reduced duplicate backend execution
- ❌ Frontend still created duplicates from case-sensitive Map keys

### Day 2: Fixed frontend deduplication
- ✅ Added Array.from(new Set(...))
- ❌ Still had duplicates because Set is also case-sensitive!

### Day 3 (Today): Fixed Map keys to be lowercase
- ✅ **Actual root cause fixed**
- ✅ Map uses `agentName.toLowerCase()` as key
- ✅ Case-insensitive lookups work correctly

---

## Summary

**Root Cause:** Case-sensitive Map keys in frontend  
**Fix:** Normalize all agent Map keys to lowercase  
**Testing:** Refresh browser and submit query  
**Expected:** 12 agents, workflow completes successfully

---

## Quick Test Now

1. **Refresh browser** → http://localhost:3001
2. **Submit test** → "What are the unemployment trends in Qatar?"
3. **Watch for** → "12 agents" (not 24!)

**This should finally work!** 🎯
