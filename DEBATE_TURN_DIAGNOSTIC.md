# 🔍 Debate Turn Streaming Diagnostic

## 📊 Current Status

### ✅ What's CONFIRMED Working:
1. **Backend debate orchestrator executes** - 6 contradictions detected
2. **Debate summary generated** - Shows in frontend
3. **Workflow completes** - All 9/10 stages done
4. **User reported: "got to turn 16"** - Debate DID run

### ❌ What's BROKEN:
1. **Frontend shows: "Waiting for debate to start..."** despite debate completing
2. **Turn count shows: "NaNs"** instead of actual number
3. **No live debate conversation displayed** in DebatePanel
4. **Individual `debate:turn` events not reaching frontend**

---

## 🔬 Root Cause Analysis

### Problem: Debate Turns Not Reaching Frontend

**Two possible causes:**

#### Cause 1: Backend Not Emitting Turn Events
**Location:** `legendary_debate_orchestrator.py` line 1223
```python
await self.emit_event("debate:turn", "streaming", turn_data)
```

**Hypothesis:** This line may not be executing OR `emit_event_fn` callback is not properly connected to the streaming queue.

**Evidence needed:**
- Backend log showing: `📤 Queued event: debate:turn1 - streaming`
- If this log is MISSING → callback not working

#### Cause 2: Frontend Not Processing Turn Events
**Location:** `useWorkflowStream.ts` and `DebatePanel.tsx`

**Hypothesis:** Events are emitted but frontend filter/parser is dropping them.

**Evidence needed:**
- Browser console should show: `🎯 DEBATE TURN RECEIVED: debate:turn`
- If this log is MISSING → events not reaching frontend

---

## 🧪 Diagnostic Steps

### Step 1: Check Backend Logs
**Run this command in PowerShell:**
```powershell
# Check if backend is currently running
Get-Process python | Where-Object {$_.Path -like "*lmis_int*"}

# If running, read the terminal output:
# Look for these patterns:
# ✅ "📤 Queued event: debate:turn" → Events ARE being queued
# ❌ If missing → callback not working
```

### Step 2: Check Browser Console
**In your browser (F12 → Console tab):**

Look for these log patterns:
```javascript
// Should see:
🎯 DEBATE TURN RECEIVED: debate:turn {agent: "...", turn: 1, ...}

// Should also see:
🎭 DebatePanel render: {debateTurnsCount: 15}

// If missing → Events not reaching frontend
```

### Step 3: Check Network Tab
**In browser (F12 → Network tab):**
1. Filter for: `/council/stream`
2. Click on the request
3. Go to **Preview** or **Response** tab
4. Search for: `"debate:turn"`

**Expected:** Multiple lines like:
```
data: {"stage":"debate:turn1","status":"streaming","payload":{...}}
data: {"stage":"debate:turn2","status":"streaming","payload":{...}}
```

**If missing:** Backend is NOT emitting turn events

---

## 🔧 Likely Fixes

### Fix A: If Backend Not Emitting (Most Likely)

**Problem:** `legendary_debate_orchestrator.py` emits turns, but streaming queue doesn't forward them.

**Location to check:** `streaming.py` lines 212-237

**Expected code:**
```python
while True:
    queue_item = await event_queue.get()
    
    # Handle different event types
    if isinstance(queue_item, WorkflowEvent):
        # Direct event from emit_event_fn (e.g., debate turns)
        yield queue_item  # ← THIS MUST EXECUTE
        continue
```

**Diagnostic:** Add log RIGHT HERE:
```python
if isinstance(queue_item, WorkflowEvent):
    logger.info(f"🎪 YIELDING WorkflowEvent: {queue_item.stage}")
    yield queue_item
    continue
```

### Fix B: If Frontend Not Processing

**Problem:** Events reach browser but React state not updating.

**Location:** `useWorkflowStream.ts` lines 86-100

**Check:** Is `debateTurns` state being updated?

```typescript
if (event.stage.startsWith('debate:turn')) {
  logger.info(`🎯 DEBATE TURN RECEIVED: ${event.stage}`);
  setDebateTurns(prev => [...prev, event]); // ← THIS MUST EXECUTE
}
```

---

## 🎯 IMMEDIATE ACTION REQUIRED

**Please do ONE of these now:**

### Option 1: Check Browser Console (FASTEST)
1. Open your browser where you just ran the query
2. Press F12 → Console tab
3. Scroll through logs
4. **Tell me:** Do you see `🎯 DEBATE TURN RECEIVED` ?

### Option 2: Check Network Tab
1. Press F12 → Network tab
2. Find `/council/stream` request
3. Click → Preview tab
4. **Tell me:** Do you see multiple `"stage":"debate:turn"` lines?

### Option 3: Show Me Backend Logs
1. Go to your PowerShell terminal where backend is running
2. Scroll up through the logs from your last query
3. **Tell me:** Do you see `📤 Queued event: debate:turn` ?

---

## 📋 What I Expect to Find

Based on your report "got to turn 16", I predict:

**MOST LIKELY SCENARIO:**
- ✅ Backend debate orchestrator runs (confirmed by contradiction detection)
- ✅ `emit_event_fn` callback IS being called 16 times
- ❌ **Streaming queue NOT forwarding WorkflowEvent objects to SSE**
- ❌ Events stay in queue but never yield to frontend

**Why this matters:**
The fix will be in `streaming.py` lines 212-237, not in the debate orchestrator itself.

---

## 🔍 Next Steps

Once you tell me what you see in:
- Browser console logs
- Network tab preview
- Backend terminal logs

I can pinpoint EXACTLY which line of code is failing and provide a surgical fix.

**Status: 🟡 AWAITING YOUR DIAGNOSTIC RESULTS**
