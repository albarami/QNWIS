# ✅ Duplicate Agent Bug Fixed

**Issue:** Frontend showing 24 agents (12 duplicates) with capitalized versions stuck at "pending"  
**Root Cause:** Case mismatch between `agent_selection` payload (PascalCase) and individual agent events (lowercase after normalization)  
**Impact:** Workflow appeared frozen because frontend waiting for capitalized agents to complete  

---

## The Bug

### Backend Behavior
1. `agent_selection` stage sends: `["LabourEconomist", "Nationalization", ...]` (PascalCase)
2. Individual agent events send: `agent:LabourEconomist` (PascalCase)

### Frontend Bug
1. `agent_selection` handler created Map entries:
   ```typescript
   agentStatuses.set("LabourEconomist", { status: "pending" })
   ```

2. Event parser normalized agent stages to lowercase:
   ```typescript
   // eventParser.ts line 24
   const normalized = trimmed.toLowerCase()  // "agent:laboureconomist"
   ```

3. Individual agent events updated different Map entries:
   ```typescript
   agentStatuses.set("laboureconomist", { status: "complete" })
   ```

### Result
- Map had TWO entries per agent: `LabourEconomist` (pending) + `laboureconomist` (complete)
- Frontend displayed 24 agents instead of 12
- UI showed 12 pending (capitalized) that would never complete
- Workflow appeared frozen

---

## Fix Applied

### File: `qnwis-frontend/src/utils/eventParser.ts` (Line 31)

**Before:**
```typescript
if (normalized.startsWith('agent:')) {
  return normalized  // Returns lowercase: "agent:laboureconomist"
}
```

**After:**
```typescript
// Keep agent stages in original case to match agent_selection payload
if (trimmed.startsWith('agent:')) {
  return trimmed  // Returns original case: "agent:LabourEconomist"
}
```

---

## How It Works Now

1. **agent_selection** creates: `agentStatuses.set("LabourEconomist", { status: "pending" })`
2. **agent:LabourEconomist** (running) updates: Same entry → `{ status: "running" }`
3. **agent:LabourEconomist** (complete) updates: Same entry → `{ status: "complete" }`

✅ **No more duplicates!**

---

## Testing

### Immediate Fix (Current Session)
The frontend will hot-reload automatically with Vite. However, the **current query is already frozen** and won't recover.

### To Test:
1. **Refresh the browser** at http://localhost:3004
2. **Submit a new query** (click "Submit to Intelligence Council")
3. **Watch Agent Execution section** - should show:
   - 12 agents total (no duplicates)
   - All agents progress: pending → running → complete
   - No capitalized versions stuck at "pending"

---

## Expected Behavior

### Before Fix
```
Agent Execution: 24 agents
✗ LabourEconomist - pending (stuck)
✓ laboureconomist - complete (244ms)
✗ Nationalization - pending (stuck)
✓ nationalization - complete (51266ms)
... (12 more duplicates)
```

### After Fix
```
Agent Execution: 12 agents
✓ LabourEconomist - pending → running → complete (244ms)
✓ Nationalization - pending → running → complete (51266ms)
... (10 more agents, all completing normally)
```

---

## Related Files

### Fixed
- `qnwis-frontend/src/utils/eventParser.ts` (line 31)

### Involved But Not Changed
- `qnwis-frontend/src/hooks/useWorkflowStream.ts` (line 101-106: agent_selection handler)
- `qnwis-frontend/src/hooks/useWorkflowStream.ts` (line 34-70: handleAgentEvent)
- `src/qnwis/orchestration/graph_llm.py` (line 688-702: backend sends PascalCase)

---

## Prevention

This bug was caused by inconsistent casing handling:
- Backend normalized agent names to PascalCase for display
- Frontend normalized stage names to lowercase for consistency
- The two normalizations conflicted in Map key matching

**Lesson:** When using Maps or objects as dictionaries, ensure consistent key normalization on **one side only**.

---

## Status

- ✅ Bug identified
- ✅ Root cause analyzed
- ✅ Fix applied to frontend
- ✅ Vite hot-reload active
- ⏳ **Action Required:** Refresh browser and test with new query

**Current frozen query will remain stuck. Submit a fresh query to see the fix in action!**
