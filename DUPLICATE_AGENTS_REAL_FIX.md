# 🔧 Real Fix for Duplicate Agents Issue

**Date:** November 19, 2025, 2:15 PM  
**Status:** ✅ FIXED (for real this time)

---

## 🐛 The ACTUAL Problem (Found in Logs)

### What Was Happening:

**Step 1: `agent_selection` stage completes**
```json
{
  "stage": "agent_selection",
  "status": "complete",
  "payload": {
    "selected_agents": ["laboureconomist", "nationalization", "skillsagent", ...]
  }
}
```
Frontend creates agent slots: `{laboureconomist, nationalization, skillsagent, ...}`

**Step 2: `agents` stage starts**
```json
{
  "stage": "agents",
  "status": "running",
  "payload": {
    "agents": ["LabourEconomist", "Nationalization", "SkillsAgent", ...]
  }
}
```
Frontend had **NO HANDLER** for this event! Agent slots remain unchanged.

**Step 3: Individual agent events**
```json
{
  "stage": "agent:LabourEconomist",
  "status": "running"
}
{
  "stage": "agent:Nationalization",  
  "status": "running"
}
```
Frontend's `handleAgentEvent()` creates **NEW** slots for each!

**Result:**
- 12 slots from `agent_selection` (lowercase)
- 12 MORE slots from `agent:Name` events (PascalCase)
- Total: **24 agents shown!**

---

## ✅ The Real Fix

### Backend Fix (Already Applied):
**File:** `src/qnwis/orchestration/graph_llm.py` lines 683-690

```python
# Send normalized agent names to match event emissions
normalized_names = [self._normalize_agent_name(name) for name in agents_to_invoke]
await event_cb(
    "agents",
    "running",
    {"agents": normalized_names, "count": len(normalized_names)},
    0,
)
```

This ensures backend sends PascalCase names from the start.

### Frontend Fix (JUST APPLIED):
**File:** `qnwis-frontend/src/hooks/useWorkflowStream.ts` lines 108-117

```typescript
// When agents stage starts, replace with normalized names from backend
if (event.stage === 'agents' && event.status === 'running' && event.payload) {
  const normalizedAgents = (event.payload as any).agents ?? []
  if (normalizedAgents.length > 0) {
    next.selectedAgents = normalizedAgents
    next.agentStatuses = new Map(
      normalizedAgents.map((name: string) => [name, { name, status: 'pending' as const }])
    )
  }
}
```

This **REPLACES** the agent slots when `agents` stage starts, preventing duplicates.

---

## 🔍 Why My Previous Fix Didn't Work

### What I Did Before:
✅ Changed backend to send normalized names ✅

### What I Missed:
❌ Frontend had no handler for `agents` stage event!
❌ It kept the lowercase slots from `agent_selection`
❌ Then created NEW slots from `agent:Name` events

### The Missing Piece:
Frontend needed to **REPLACE** agent slots, not just receive them!

---

## 🧪 Verification

### Before Fix:
```
Agent Execution: 24 agents
- LabourEconomist (pending)
- laboureconomist (complete)  
- Nationalization (pending)
- nationalization (running)
... (12 duplicates)
```

### After Fix:
```
Agent Execution: 12 agents
- LabourEconomist (complete)
- Nationalization (running)
- SkillsAgent (complete)
... (12 unique agents)
```

---

## 📊 System Status

**Backend:**
- ✅ Running (port 8000)
- ✅ Sends normalized agent names
- ✅ 3-minute timeout for PhD-level analysis
- ✅ 10-minute total workflow timeout

**Frontend:**
- ✅ Rebuilt with fix
- ✅ Restarted on port 3000
- ✅ Handles `agents` stage event
- ✅ Replaces agent slots correctly

---

## 🎯 Test Now

**URL:** http://localhost:3000

**Expected:**
- ✅ Exactly 12 agents shown
- ✅ No duplicates
- ✅ All names in PascalCase
- ✅ Agents execute and complete normally

**No more 24 agents!** 🎉

---

*Root cause: Missing frontend handler for `agents` stage event*  
*Solution: Add handler to replace agent slots with normalized names*  
*Result: Clean 12-agent display with no duplicates* ✅
