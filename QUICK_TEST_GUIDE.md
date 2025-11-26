# Quick Test Guide - Level 4 Fixes

**Time Required:** 5-10 minutes  
**Prerequisites:** Backend and frontend servers running

---

## ⚡ Quick Start (2 Steps)

### 1. Start Servers

```powershell
# Terminal 1: Backend
cd d:\lmis_int
python -m uvicorn src.qnwis.api.server:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd d:\lmis_int\qnwis-frontend
npm run dev
```

**✓ Checkpoint:** Look for this in backend logs:
```
INFO - Pre-warming RAG components (embedder + document store)...
INFO - RAG components warm-up scheduled
```

### 2. Run Test Script

```powershell
# Terminal 3: Test Script
cd d:\lmis_int
.\scripts\test_level4_fix.ps1
```

Follow the prompts and verify all tests pass.

---

## 🧪 Manual UI Test (1 Minute)

1. **Open:** http://localhost:5173
2. **Open DevTools:** Press `F12`
3. **Enter Question:** "What are the unemployment trends in Qatar?"
4. **Select Provider:** "stub"
5. **Click Submit**

### ✅ Success Indicators
- ✅ Classification completes in <100ms
- ✅ Prefetch completes successfully
- ✅ RAG completes (no 8-second delay)
- ✅ **Exactly 12 unique agents** appear (no duplicates)
- ✅ All agents complete or error (no stuck "running")
- ✅ Synthesis appears
- ✅ No browser console errors
- ✅ Screen stays responsive (no dark screen)

### ❌ Failure Indicators
- ❌ HTTP 500 error
- ❌ More than 12 agents (duplicates)
- ❌ Agents stuck in "running" state
- ❌ Screen goes dark
- ❌ Error banner appears without user action

---

## 🔍 What Changed?

### The 6 Critical Fixes

| # | Fix | You Should See |
|---|-----|----------------|
| 1 | Backend Crash | ✅ No HTTP 500 errors |
| 2 | Data Pipeline | ✅ Agents have data (not empty contexts) |
| 3 | SSE Stability | ✅ Stream completes without errors |
| 4 | Agent Execution | ✅ Exactly 12 agents, all complete |
| 5 | Frontend Resilience | ✅ Error banner (not dark screen) on failures |
| 6 | RAG Performance | ✅ Fast first request (<1 second) |

---

## 🚨 Troubleshooting

### Problem: Backend crashes with HTTP 500
**Check:** Backend logs for `PydanticUserError`  
**Fix:** Verify `council_llm.py` line 207 signature is correct  
**Restart:** Backend server

### Problem: Still seeing duplicate agents
**Check:** Browser cache  
**Fix:** Hard reload (Ctrl+Shift+R) or clear cache  
**Verify:** Frontend code at `useWorkflowStream.ts` line 113

### Problem: Agents stuck in "running"
**Check:** Backend logs for timeout errors  
**Fix:** Verify `graph_llm.py` lines 711-714 timeout is set  
**Expected:** Agent times out after 60 seconds

### Problem: RAG still slow on first request
**Check:** Backend logs for "Pre-warming RAG components"  
**Fix:** Set `QNWIS_WARM_EMBEDDER=true` in `.env`  
**Restart:** Backend server

### Problem: Screen goes dark on error
**Check:** Browser console for JavaScript errors  
**Fix:** Verify `useWorkflowStream.ts` lines 248-257 error handling  
**Expected:** Error banner, not dark screen

---

## 📊 Performance Benchmarks

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Classification | <100ms | DevTools Network tab → classify event |
| Prefetch | <2s | DevTools Network tab → prefetch event |
| RAG (first request) | <1s | Backend logs → RAG latency |
| All 12 agents | <2 min | UI timer (agents stage) |
| Total workflow | <3 min | UI timer (start to synthesis) |

---

## ✅ Success Criteria

**All of these must be true:**
- ✅ No HTTP 500 errors in Network tab
- ✅ No browser console errors
- ✅ Exactly 12 unique agent cards
- ✅ All agents reach "complete" or "error" status
- ✅ Workflow completes with synthesis
- ✅ RAG pre-warming confirmed in backend logs
- ✅ First request is fast (<1 second for RAG)

---

## 📚 Detailed Documentation

For comprehensive testing:
- **Full Checklist:** `LEVEL4_FIX_VERIFICATION_COMPLETE.md`
- **Implementation Details:** `LEVEL4_FIXES_APPLIED.md`
- **Test Script:** `scripts/test_level4_fix.ps1`

---

## 🎯 Next Steps After Successful Test

1. **Test with Anthropic provider** (requires API key)
   - Question: "Compare Qatar's unemployment to GCC countries"
   - Provider: "anthropic"
   - Expected: More detailed synthesis with citations

2. **Test complex scenarios**
   - Vision 2030 questions
   - Gender disparity analysis
   - Multi-sector comparisons

3. **Test error recovery**
   - Disconnect network mid-workflow
   - Expected: Error banner, can retry

4. **Performance testing**
   - Submit 3 queries in rapid succession
   - Expected: No memory leaks, no duplicate connections

5. **Prepare for deployment**
   - Re-enable rate limiting
   - Configure production settings
   - Load test with 100+ users

---

**Good luck with testing! 🚀**

If all tests pass, the Level 4 crash issues are fully resolved.
