# 🚀 START MIGRATION NOW - Immediate Actions

**Copy-paste these commands in order. Report results after each step.**

---

## ⚡ STEP 1: Verify Backend (5 minutes)

### Check if FastAPI is running:

```powershell
# Test if backend is up
curl http://localhost:8000/health
```

**Expected:** `{"status": "ok"}` or similar

**If backend not running:**
```powershell
cd d:\lmis_int
python -m uvicorn src.qnwis.api.main:app --reload --port 8000
```

---

## ⚡ STEP 2: Test SSE Endpoint (5 minutes)

```powershell
# Test SSE streaming
curl -N http://localhost:8000/api/v1/council/llm/stream `
  -X POST `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"test query\"}'
```

### What to look for:

**✅ GOOD OUTPUT:**
```
data: {"event": "stage_start", "stage": "classify", ...}

data: {"event": "stage_complete", "stage": "classify", ...}

data: {"event": "stage_start", "stage": "prefetch", ...}
```

**❌ BAD OUTPUT:**
- `404 Not Found` → Endpoint doesn't exist
- `{"error": "..."}` → Backend error
- Plain JSON without `data:` prefix → Wrong format
- Connection timeout → Backend issue

**📋 REPORT BACK:**
- What output did you get?
- Any errors?
- Did it complete successfully?

---

## ⚡ STEP 3: Check Backend SSE Format (2 minutes)

Let me check your backend code:

```powershell
# Show me your streaming endpoint
Get-Content src\qnwis\api\routes\council.py | Select-String -Pattern "stream" -Context 5,10
```

**Or manually check:**
1. Open `src/qnwis/api/routes/council.py`
2. Find the streaming endpoint
3. Look for the `yield` statement

**Should look like:**
```python
yield f"data: {json.dumps(event)}\n\n"
```

**NOT like:**
```python
yield json.dumps(event)  # ❌ Missing "data: " prefix
```

---

## ⚡ STEP 4: Add CORS (if not already present) (3 minutes)

Check if CORS is configured:

```powershell
Get-Content src\qnwis\api\main.py | Select-String -Pattern "CORS"
```

**If no output, add CORS:**

1. Open `src/qnwis/api/main.py`
2. Add after imports:
```python
from fastapi.middleware.cors import CORSMiddleware
```

3. Add after `app = FastAPI(...)`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

4. Restart backend

---

## ⚡ STEP 5: Document Backend Status (5 minutes)

Create this file: `BACKEND_SSE_STATUS.md`

```markdown
# Backend SSE Status Report

**Date:** [Today's date]
**Tested by:** [Your name]

## Endpoint Test Results

### URL
- Endpoint: `POST /api/v1/council/llm/stream`
- Port: 8000
- Status: ✅ Working / ❌ Needs fixes

### SSE Format
- Follows SSE spec (data: prefix): ✅ / ❌
- Double newline separator: ✅ / ❌
- Valid JSON: ✅ / ❌

### Stages Tested
- [ ] classify
- [ ] prefetch
- [ ] agents (financial/market/operations/research)
- [ ] debate
- [ ] critique
- [ ] synthesis
- [ ] complete

### CORS Configuration
- CORS middleware present: ✅ / ❌
- localhost:3000 allowed: ✅ / ❌

## Issues Found
1. [List any issues]

## Fixes Applied
1. [List fixes]

## Ready for React Integration
✅ YES - Proceed to Phase 1A
❌ NO - Fix issues first

## Test Query Used
```json
{"query": "test query"}
```

## Sample Output
```
[Paste first few lines of SSE output here]
```
```

---

## ⚡ STEP 6: Commit Backend Changes (2 minutes)

**Only if you made changes:**

```powershell
git add src/qnwis/api/ BACKEND_SSE_STATUS.md
git commit -m "fix(backend): verify and fix SSE streaming for React frontend

- Test SSE endpoint with curl
- Fix event format to match SSE spec (if needed)
- Add CORS middleware for localhost:3000
- Document backend state in BACKEND_SSE_STATUS.md

Backend verified and ready for React integration.

Ref: REACT_MIGRATION_REVISED.md Phase 0"
git push origin main
```

---

## 🎯 DECISION POINT

### ✅ If Backend Working:
**Proceed to React setup:**
```powershell
# Run this script
.\scripts\migrate_to_react.ps1 -Phase 1A
```

**Or manually:**
```powershell
cd d:\lmis_int
npm create vite@latest qnwis-ui -- --template react-ts
```

### ❌ If Backend Has Issues:

**STOP and report:**
1. What error did you get?
2. What does the SSE output look like?
3. Is CORS configured?
4. Does the endpoint exist?

**I'll help you fix it before proceeding.**

---

## 📊 Phase 0 Checklist

- [ ] Backend running on port 8000
- [ ] SSE endpoint tested with curl
- [ ] Output follows SSE format (`data: {...}\n\n`)
- [ ] All stages emit correctly
- [ ] CORS configured for localhost:3000
- [ ] `BACKEND_SSE_STATUS.md` created
- [ ] Changes committed to git

**Phase 0 Complete:** ✅ / ❌

---

## 🚀 Next Steps (After Phase 0)

1. **Initialize React project** (Phase 1A)
2. **Test integration** (Phase 1C-Minimal)
3. **Build components** (Phase 1B)
4. **Remove Chainlit** (Phase 2)
5. **Document** (Phase 5)

**Estimated Timeline:** 7 days

---

## 📞 Report Back

**After completing Phase 0, report:**

1. ✅ Backend SSE working correctly
2. ❌ Backend has issues: [describe]
3. 📋 `BACKEND_SSE_STATUS.md` created
4. 🎯 Ready for Phase 1A: YES / NO

**Then I'll guide you through Phase 1A!** 🚀
