# 🚀 React Migration - Quick Reference Card

**Print this or keep it open while working**

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| **`START_MIGRATION_NOW.md`** | ⚡ Start here - immediate actions |
| **`REACT_MIGRATION_REVISED.md`** | 📖 Complete strategic plan |
| **`REACT_EXECUTION_CHECKLIST.md`** | ✅ Day-by-day checklist |
| **`REACT_CODE_FILES.md`** | 💻 All code to copy |
| **`MIGRATION_SUMMARY.md`** | 📊 Overview and decisions |

---

## ⚡ Quick Start Commands

### Phase 0: Test Backend
```powershell
# Test SSE endpoint
curl -N http://localhost:8000/api/v1/council/llm/stream `
  -X POST `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"test\"}'
```

### Phase 1A: Initialize React
```powershell
cd d:\lmis_int
npm create vite@latest qnwis-ui -- --template react-ts
cd qnwis-ui
npm install
npm install axios @microsoft/fetch-event-source date-fns lucide-react
npm install -D @types/node tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Start Development
```powershell
# Terminal 1: Backend
cd d:\lmis_int
python -m uvicorn src.qnwis.api.main:app --reload --port 8000

# Terminal 2: Frontend
cd d:\lmis_int\qnwis-ui
npm run dev
```

---

## 📋 7-Day Timeline

| Day | Phase | Key Deliverable |
|-----|-------|-----------------|
| 1 | Phase 0 + 1A | Backend verified, React initialized |
| 2 | Phase 1C-Min | Integration working |
| 3-4 | Phase 1B | Components complete |
| 5 | Phase 1C + Phase 2 | Backend enhanced, Chainlit removed |
| 6 | Phase 5 | Documentation complete |
| 7 | Buffer | Testing and polish |

---

## ✅ Phase Checklist

### Phase 0: Backend Verification
- [ ] Test SSE with curl
- [ ] Verify event format
- [ ] Add CORS
- [ ] Create `BACKEND_SSE_STATUS.md`
- [ ] Commit changes

### Phase 1A: React Setup
- [ ] Initialize Vite project
- [ ] Install dependencies
- [ ] Create types
- [ ] Create SSE hook
- [ ] Create MVP App.tsx
- [ ] Commit changes

### Phase 1C-Minimal: Integration
- [ ] Start both servers
- [ ] Test connection
- [ ] Verify streaming
- [ ] Fix any issues
- [ ] Commit changes

### Phase 1B: Components
- [ ] Layout components
- [ ] Workflow components
- [ ] Analysis components
- [ ] Common components
- [ ] Refactor App.tsx
- [ ] Commit changes (4 commits)

### Phase 1C-Complete: Backend
- [ ] Add validation
- [ ] Error handling
- [ ] Optimization
- [ ] Commit changes

### Phase 2: Remove Chainlit
- [ ] Audit dependencies
- [ ] Delete app
- [ ] Clean configs
- [ ] Update docs
- [ ] Commit changes (2 commits)

### Phase 5: Documentation
- [ ] Frontend README
- [ ] Architecture docs
- [ ] Update main docs
- [ ] Commit changes

---

## 🚨 Common Issues

### CORS Error
**Symptom:** `Access to fetch blocked by CORS policy`

**Fix:**
```python
# In src/qnwis/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### SSE Not Parsing
**Symptom:** `Failed to parse event`

**Fix:** Check backend format
```python
# CORRECT:
yield f"data: {json.dumps(event)}\n\n"

# WRONG:
yield json.dumps(event)
```

### Connection Closes Immediately
**Symptom:** Stream closes right after opening

**Fix:** Check headers
```python
return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
)
```

---

## 📊 Git Commit Format

```
<type>(<scope>): <description>

<body>

Ref: REACT_MIGRATION_REVISED.md Phase X
```

**Types:** feat, fix, docs, style, refactor, test, chore

**Example:**
```
feat(frontend): initialize React + Vite with TypeScript

- Create Vite project with react-ts template
- Install core dependencies
- Configure Tailwind CSS

Ref: REACT_MIGRATION_REVISED.md Phase 1A
```

---

## 🎯 Success Criteria

### After Phase 0:
✅ SSE endpoint works with curl  
✅ Event format correct  
✅ CORS configured

### After Phase 1A:
✅ React app runs  
✅ No TypeScript errors  
✅ Tailwind working

### After Phase 1C-Minimal:
✅ React connects to FastAPI  
✅ Events stream correctly  
✅ UI updates in real-time

### After Phase 1B:
✅ Component architecture complete  
✅ UI polished  
✅ All features working

### After Phase 2:
✅ Chainlit completely removed  
✅ No references remain  
✅ Docs updated

### After Phase 5:
✅ Documentation complete  
✅ Ready for production

---

## 📞 Decision Points

**After Phase 0:**
- ✅ Backend working? → Proceed
- ❌ Backend broken? → Fix first

**After Phase 1C-Minimal:**
- ✅ Integration working? → Build components
- ❌ Issues? → Debug first

---

## 🚀 Next Action

**Right now, execute:**
```powershell
code START_MIGRATION_NOW.md
```

**Then run:**
```powershell
curl http://localhost:8000/health
```

**Report results and proceed!** 🎯
