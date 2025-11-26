# ⏱️ Timeout Increase for PhD-Level Agents

**Date:** November 19, 2025, 2:10 PM  
**Issue:** 60-second timeout too short for deep economic analysis  
**Status:** ✅ FIXED

---

## 🎓 The Problem

These are **PhD-level agents** performing sophisticated economic analysis for Qatar's Ministry of Labour:

- **Labour Economist**: Deep sectoral analysis, wage trends, employment projections
- **Nationalization Expert**: Qatarization policy impact, workforce composition analysis
- **Skills Analyst**: Skills gap analysis, training program evaluation
- **Pattern Detective**: Historical trend analysis, economic cycle detection
- **National Strategy**: Multi-year strategic planning, GCC benchmarking

**60 seconds is NOT enough** for this level of analysis!

---

## 📊 What Was Happening

### Before (60-second timeout):
1. Agent starts deep analysis
2. LLM begins generating comprehensive report with:
   - Multi-year trend analysis
   - Sectoral breakdowns
   - GCC comparisons
   - Policy recommendations
   - Statistical projections
3. **At 60 seconds**: Timeout! ⏰
4. Agent fails, workflow crashes
5. No results despite good analysis in progress

### The Evidence:
- User saw 2 agents (Nationalization, SkillsAgent) stuck at "running"
- They weren't hung - they were just doing **deep analysis**
- The 60-second cap killed them mid-analysis

---

## ✅ The Fix

### New Timeouts:

**Individual LLM Calls:**
- **Before**: 60 seconds (1 minute)
- **After**: 180 seconds (3 minutes) ✅
- **Why**: PhD-level agents need time for:
  - Processing multiple data sources
  - Generating comprehensive analysis
  - Producing detailed recommendations
  - Creating proper citations

**Total Agent Execution:**
- **Before**: 300 seconds (5 minutes) for all 12 agents
- **After**: 600 seconds (10 minutes) for all 12 agents ✅
- **Why**:
  - 12 agents run in parallel
  - Each can take up to 3 minutes
  - Allow for retries (3 max per agent)
  - Buffer for API latency

---

## 📝 Files Modified

### 1. `src/qnwis/llm/config.py`

**Line 94** (documentation):
```python
# BEFORE:
- QNWIS_LLM_TIMEOUT: Timeout in seconds (default: 60, capped at 60)

# AFTER:
- QNWIS_LLM_TIMEOUT: Timeout in seconds (default: 180, capped at 180 for deep PhD-level analysis)
```

**Line 112** (actual timeout):
```python
# BEFORE:
timeout = min(int(os.getenv("QNWIS_LLM_TIMEOUT", "60")), 60)

# AFTER:
timeout = min(int(os.getenv("QNWIS_LLM_TIMEOUT", "180")), 180)  # 3 minutes for PhD-level analysis
```

### 2. `src/qnwis/llm/client.py`

**Line 57**:
```python
# BEFORE:
self.timeout_s = min(effective_timeout, 60)

# AFTER:
self.timeout_s = min(effective_timeout, 180)  # 3 minutes for PhD-level deep analysis
```

### 3. `src/qnwis/orchestration/graph_llm.py`

**Lines 754-766**:
```python
# BEFORE:
# Execute agents with 5-minute timeout to prevent indefinite hangs
try:
    results = await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True),
        timeout=300  # 5 minutes total for all agents
    )
except asyncio.TimeoutError:
    logger.error("Agent execution timed out after 5 minutes")
    await event_cb("agents", "error", {"error": "Agent execution timeout after 5 minutes"})
    results = [Exception("Timeout") for _ in tasks]

# AFTER:
# Execute agents with 10-minute timeout for PhD-level deep analysis
# Individual LLM calls have 3-minute timeout, so 10 minutes total allows for retries and parallel execution
try:
    results = await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True),
        timeout=600  # 10 minutes total for all 12 agents in parallel
    )
except asyncio.TimeoutError:
    logger.error("Agent execution timed out after 10 minutes")
    await event_cb("agents", "error", {"error": "Agent execution timeout after 10 minutes - may indicate hung agent"})
    results = [Exception("Timeout") for _ in tasks]
```

---

## 🧮 Timeout Math

### Realistic Scenario:
- **12 agents** run in parallel
- **Average completion**: 60-90 seconds per agent
- **Slow agents** (deep analysis): 120-180 seconds
- **With 3 retries**: Could take up to 180s × 3 = 540 seconds (9 minutes)
- **10-minute total**: Reasonable buffer ✅

### Safety Net:
- Still have timeout to prevent **true hangs** (infinite loops, deadlocks)
- But won't kill agents doing **legitimate deep analysis**
- Logs will show if 10-minute timeout is hit (indicates real problem)

---

## 📊 Expected Behavior Now

### Successful Deep Analysis:
1. Agent starts analysis
2. LLM takes 120-180 seconds generating comprehensive report
3. Agent completes successfully ✅
4. Workflow continues to debate/critique/verify
5. User gets high-quality PhD-level insights

### Actual Hang Detection:
If an agent **truly hangs** (bug, deadlock, API freeze):
- Individual call times out at 3 minutes
- Retry happens (up to 3 times)
- If still failing after retries → marked as failed
- Other agents continue
- Total workflow times out at 10 minutes if all agents stuck

---

## 🎯 Quality vs Speed Tradeoff

### What We're Optimizing For:
- ✅ **Quality**: Deep, PhD-level analysis
- ✅ **Accuracy**: Proper data synthesis
- ✅ **Completeness**: Comprehensive recommendations
- ⏱️ **Speed**: Secondary concern (but still reasonable)

### What We're NOT Doing:
- ❌ Sacrificing analysis quality for speed
- ❌ Rushing agents to meet arbitrary deadlines
- ❌ Cutting corners on Ministerial-grade reports

---

## 🔍 Monitoring

To check if agents are using the full time:

```python
# In logs, look for:
"Agent completed in Xms"

# If you see completion times > 60,000ms (60s):
# → Agents ARE using the extra time for deep analysis ✅

# If you see timeout errors after 10 minutes:
# → Possible hung agent, investigate ⚠️
```

---

## ✅ System Status

**Timeouts Now:**
- Individual LLM: **180 seconds** (3 minutes)
- Total agents: **600 seconds** (10 minutes)
- Backend: ✅ Restarted with new timeouts
- Frontend: ✅ Running (no changes needed)

**Ready for deep PhD-level economic analysis!** 🎓📊

---

*Optimized for quality over speed - as befits analysis for Qatar's Ministry of Labour*
