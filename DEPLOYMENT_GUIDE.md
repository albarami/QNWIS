# QNWIS Development Deployment Guide

**System:** Qatar National Workforce Intelligence System  
**Version:** Week 3 - Pilot Validated  
**Date:** November 22, 2025  
**Status:** Ready for development deployment

---

## System Architecture

**Backend:** Python + LangGraph + FastAPI  
**Frontend:** React 19 + TypeScript + Vite  
**Database:** PostgreSQL  
**LLM:** Anthropic Claude Sonnet 4.5

---

## Prerequisites Validated ✅

- [x] PostgreSQL database operational (128 cached indicators)
- [x] All API keys configured (.env file)
- [x] Python 3.11+ environment
- [x] Node.js 18+ (for React frontend)
- [x] LangGraph orchestration working
- [x] Anthropic Sonnet 4.5 integrated
- [x] 10/10 pilot queries passing

---

## Part 1: Backend Deployment

### 1. Clone Repository

```bash
git clone https://github.com/albarami/QNWIS.git
cd QNWIS
git checkout main  # Week 3 validated branch
```

### 2. Backend Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your keys:
ANTHROPIC_API_KEY=sk-ant-...  # Required
QNWIS_LANGGRAPH_LLM_PROVIDER=anthropic
QNWIS_LANGGRAPH_LLM_MODEL=claude-sonnet-4-20250514

# Data Source APIs (recommended):
BRAVE_API_KEY=...
PERPLEXITY_API_KEY=...
# (FRED, UN Comtrade, MoL LMIS are optional)

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qnwis
```

### 4. Database Setup

```bash
# Initialize PostgreSQL
python scripts/init_db.py

# Load World Bank cache (128 indicators)
python scripts/load_wb_cache.py

# Verify
python scripts/verify_db.py
```

### 5. Backend Validation

```bash
# Run validation suite (6/6 tests should pass)
python validate_langgraph_refactor.py

# Expected output:
# Tests passed: 6/6
# ✅ ALL TESTS PASSED - Production-ready
```

### 6. Start Backend Server

```bash
# Start FastAPI backend (port 8000)
python -m qnwis.main

# Or with uvicorn directly:
uvicorn qnwis.api.main:app --reload --port 8000

# Backend available at: http://localhost:8000
# API endpoint: http://localhost:8000/api/v1/council/stream
```

---

## Part 2: Frontend Deployment

### 1. Navigate to Frontend Directory

```bash
cd qnwis-frontend
```

### 2. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Verify installation
npm list react vite typescript
# Should show: react@19.0.x, vite@7.2.x, typescript@5.9.x
```

### 3. Configure Frontend

```bash
# Check frontend configuration
cat src/config.ts

# Should have:
# BACKEND_URL: http://localhost:8000/api/v1/council/stream
# FRONTEND_PORT: 3000
```

### 4. Start Frontend Development Server

```bash
# Start Vite dev server (port 3000)
npm run dev

# Frontend available at: http://localhost:3000
# Live reload enabled
```

### 5. Production Build (Optional)

```bash
# Build for production
npm run build

# Preview production build
npm run preview

# Production files in: dist/
```

---

## Part 3: Full Stack Verification

### 1. Backend Health Check

```bash
# Test backend is running
curl http://localhost:8000/health

# Expected: {"status": "healthy", "version": "1.0.0"}
```

### 2. Frontend Access

Open browser: `http://localhost:3000`

**Expected UI:**
- 12-agent visualization grid
- Live streaming workflow display
- Stage progress timeline
- Debate panel with real-time updates
- Executive summary results
- Verification panel

### 3. Test End-to-End Query

**In the frontend:**

1. Enter query: "What is Qatar's GDP growth trend?"
2. Click "Submit"
3. Watch live streaming:
   - Data extraction phase
   - 4 specialist agents analyzing
   - Multi-agent debate
   - Critique & verification
   - Final synthesis

**Expected results:**
- 80-150 facts extracted
- Confidence score 0.5-0.8
- Multi-source citations visible
- Agent debate shows distinct perspectives
- Executive summary is coherent

### 4. Verify SSE Streaming

**Check browser console (F12):**
- ✅ Connected to SSE stream
- ✅ Receiving events: `extraction_complete`, `agent_analysis`, `debate_turn`, `synthesis_complete`
- ✅ No connection errors

---

## Frontend Tech Stack Details

### Core Framework:
- **React 19.0** - Latest with concurrent rendering
- **TypeScript 5.9** - Strict mode enabled
- **Vite 7.2** - Lightning-fast dev server

### Styling:
- **TailwindCSS 3.4** - Utility-first CSS
- **Lucide React** - Icon library

### Streaming:
- **@microsoft/fetch-event-source** - SSE streaming

### Components Structure:
```
qnwis-frontend/src/
├── components/
│   ├── agents/        # AgentCard, AgentGrid
│   ├── debate/        # DebatePanel, DebateConversation
│   ├── critique/      # CritiquePanel
│   ├── results/       # ExecutiveSummary, VerificationPanel
│   └── workflow/      # StageProgress, StageTimeline
├── hooks/
│   └── useWorkflowStream.ts  # SSE streaming logic
├── types/
│   └── workflow.ts    # TypeScript definitions
└── config.ts          # Backend URL configuration
```

---

## Verification Checklist

After deployment, verify:

**Backend:**
- [ ] PostgreSQL cache working (<100ms)
- [ ] Anthropic API responding (check logs)
- [ ] FastAPI server on port 8000
- [ ] Test query returns 80+ facts
- [ ] Confidence scores 0.5-0.8 range
- [ ] No stub LLM references in logs

**Frontend:**
- [ ] React app on port 3000
- [ ] SSE streaming connected
- [ ] 12 agents visible in UI
- [ ] Live updates during query execution
- [ ] Debate panel showing conversations
- [ ] Results display properly

**Integration:**
- [ ] Frontend → Backend connection working
- [ ] Real-time streaming events received
- [ ] Agent analysis updates in real-time
- [ ] Final synthesis displays correctly

---

## Monitoring

### Backend logs:
- **Application:** `logs/qnwis.log`
- **API calls:** `logs/api_calls.log`
- **Errors:** `logs/errors.log`

### Frontend console:
- Check browser DevTools (F12)
- **Network tab:** Verify SSE connection
- **Console:** Check for JavaScript errors

### Key metrics to track:
- Query execution time (target: <120s)
- Facts extracted per query (target: >80)
- Confidence scores (target: 0.5-0.8)
- API error rates (target: <5%)
- SSE connection stability (target: >99%)

---

## Troubleshooting

### Backend Issues

**Issue:** "Stub LLM" in logs  
**Solution:** Check `.env` has `QNWIS_LANGGRAPH_LLM_PROVIDER=anthropic`

**Issue:** Low fact count (<80)  
**Solution:** Check API keys in `.env`, verify PostgreSQL cache

**Issue:** Slow queries (>200s)  
**Solution:** Normal for complex queries; check if UN Comtrade rate limiting

**Issue:** FastAPI won't start  
**Solution:** Check port 8000 not in use: `netstat -ano | findstr :8000`

### Frontend Issues

**Issue:** "Cannot connect to backend"  
**Solution:** Verify backend running on port 8000, check CORS settings

**Issue:** SSE connection keeps disconnecting  
**Solution:** Check backend SSE endpoint, verify `@microsoft/fetch-event-source` installed

**Issue:** React app won't start  
**Solution:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

**Issue:** Build errors  
**Solution:** Check TypeScript errors: `npm run type-check`

### Integration Issues

**Issue:** Frontend shows data but no live updates  
**Solution:** Check SSE streaming in Network tab, verify backend emitting events

**Issue:** Agent cards not updating  
**Solution:** Check `useWorkflowStream` hook, verify event types match backend

---

## Development Workflow

### Making Changes

**Backend changes:**
```bash
# Backend auto-reloads with uvicorn --reload
# No restart needed for code changes
# Restart needed for .env changes
```

**Frontend changes:**
```bash
# Frontend auto-reloads with Vite HMR (Hot Module Replacement)
# Changes visible instantly in browser
```

### Testing

**Backend:**
```bash
pytest tests/
python validate_langgraph_refactor.py
```

**Frontend:**
```bash
npm run test          # Unit tests (if configured)
npm run type-check    # TypeScript validation
npm run lint          # ESLint
```

---

## Production Deployment

### Backend (Docker recommended)

```bash
# Build Docker image
docker build -t qnwis-backend .

# Run container
docker run -p 8000:8000 --env-file .env qnwis-backend
```

### Frontend (Static hosting)

```bash
# Build production bundle
cd qnwis-frontend
npm run build

# Deploy dist/ folder to:
# - Netlify
# - Vercel  
# - AWS S3 + CloudFront
# - Azure Static Web Apps
# - Or any static hosting
```

---

## Support

**Documentation:**
- Backend: `/docs` folder
- Frontend: `qnwis-frontend/README.md`
- Pilot results: `WEEK_3_PILOT_FINAL_REPORT.md`
- Architecture: `docs/ARCHITECTURE_DOMAIN_AGNOSTIC.md`

**API Documentation:**
- FastAPI auto-docs: `http://localhost:8000/docs`
- OpenAPI spec: `http://localhost:8000/openapi.json`

---

**Deployment validated:** November 22, 2025  
**Backend:** FastAPI + LangGraph  
**Frontend:** React 19 + TypeScript + Vite  
**Status:** Production-ready  
**Next:** Stakeholder testing
