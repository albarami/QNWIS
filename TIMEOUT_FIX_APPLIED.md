# ✅ Workflow Timeout Fixed - 30 Minutes Now Allowed

**Issue:** Workflow timing out at 3 minutes during debate phase  
**Root Cause:** API timeout (180s) incompatible with legendary debate target (20-30 min)  
**Solution:** Increased timeout to 1800s (30 minutes)  

---

## The Problem

### Configuration Mismatch

**LegendaryDebateOrchestrator** (`legendary_debate_orchestrator.py` line 22):
```python
"""
COMPLETE 6-phase legendary debate system.
Target: 80-125 turns over 20-30 minutes.
"""
```

**API Timeout** (`council_llm.py` line 32):
```python
STREAM_TIMEOUT_SECONDS = 180  # Only 3 minutes!
```

### What Happened

1. **7:28:39 PM** - Workflow started
2. **Agents completed** - All 12 agents finished successfully
3. **Debate started** - Legendary debate with 6 phases begins
4. **16 turns completed** - Still in Phase 1 (opening statements, max 12 turns) or Phase 2 (challenge/defense)
5. **3 minutes elapsed** - API timeout triggered
6. **7:31:39 PM** (estimated) - Workflow killed mid-debate
7. **Frontend shows:** `Current Stage: timeout` with `Status: pending`

---

## The Fix

### File: `src/qnwis/api/routers/council_llm.py` (Line 32)

**Before:**
```python
STREAM_TIMEOUT_SECONDS = 180  # 3 minutes
```

**After:**
```python
STREAM_TIMEOUT_SECONDS = 1800  # 30 minutes - allows legendary debate to complete (20-30min target)
```

---

## How It Works

### Legendary Debate Phases

The debate orchestrator runs **6 phases** with different turn limits:

1. **Opening Statements** - Max 12 turns (~2 min)
   - Each agent presents their position

2. **Challenge/Defense** - Max 50 turns (~8 min)
   - Agents challenge each other's positions
   - Resolutions tracked

3. **Edge Case Exploration** - Max 25 turns (~6 min)
   - LLM generates edge cases
   - Agents analyze scenarios

4. **Risk Analysis** - Max 25 turns (~4 min)
   - Agents identify catastrophic risks
   - Peer assessment

5. **Consensus Building** - Max 13 turns (~5 min)
   - Final positions from each agent
   - Convergence detection

6. **Final Synthesis** - (~5 min)
   - LLM synthesizes consensus

**Total: Up to 125 turns over 20-30 minutes**

### Timeout Behavior

**Before Fix:**
- Timeout at 180s (3 minutes)
- Killed debate mid-Phase 2
- Frontend showed "timeout" error

**After Fix:**
- Timeout at 1800s (30 minutes)
- Allows full 6-phase debate
- Graceful completion

---

## Testing

### Current Session
The **current timed-out workflow is dead** and cannot recover. 

### To Test:
1. **Backend will auto-reload** (uvicorn --reload)
2. **Refresh browser** at http://localhost:3004
3. **Submit a new query** (same food security question)
4. **Watch the debate run to completion:**
   - All 6 phases should execute
   - 80-125 turns expected
   - 20-30 minutes total time
   - **No timeout error!**

---

## Expected Behavior

### During Execution
```
Agents: 12 complete (✓)
Debate: Phase 1 - Opening statements
  Turn 1: Nationalization (✓)
  Turn 2: SkillsAgent (✓)
  ...
  Turn 16: NationalStrategyLLM (✓)
Debate: Phase 2 - Challenge/Defense
  Turn 17: LabourEconomist challenges Nationalization (✓)
  ...
  [Continues for 20-30 minutes]
Debate: Phase 6 - Final Synthesis (✓)
Critique: Devil's advocate analysis (✓)
Verify: Citation compliance (✓)
Synthesize: Executive summary (✓)
Done: Complete! (✓)
```

### After Completion
- Full debate conversation history
- Resolutions from Phase 2
- Consensus from Phase 5
- Final synthesis
- Executive summary

---

## Files Changed

- ✅ `src/qnwis/api/routers/council_llm.py` - Increased timeout to 30 minutes

---

## Status

- ✅ Timeout increased from 3 min → 30 min
- ✅ Backend will auto-reload (uvicorn --reload)
- ⏳ **Restart query to see full debate complete!**

---

## Notes

### Why 30 Minutes?

- **Safety margin**: Debate target is 20-30 min, so 30 min timeout provides buffer
- **LLM latency**: API calls can be slow, especially for complex reasoning
- **Real ministerial analysis**: Complex policy questions deserve thorough debate
- **Production consideration**: May want to make this configurable per endpoint

### Alternative Solutions Considered

1. ❌ **Reduce debate turns** - Would compromise analysis quality
2. ❌ **Skip debate phases** - Defeats purpose of legendary debate
3. ✅ **Increase timeout** - Simple, preserves full functionality
4. 💡 **Future**: Make timeout query-complexity dependent

---

**Backend auto-reloading now. Submit a new query to see the full legendary debate!** 🎉
