# 🚀 How to Start the QNWIS System

## Quick Start (2 Commands)

### Terminal 1 - Backend
```powershell
cd d:\lmis_int
python -m uvicorn src.qnwis.api.server:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2 - Frontend
```powershell
cd d:\lmis_int\qnwis-ui
npm run dev
```

## Access Points

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs (if enabled)
- **Test Page**: http://localhost:8000/test_frontend_flow.html

## Testing the System

### Option 1: Use Frontend UI
1. Navigate to http://localhost:3000
2. Enter a question in the text area
3. Click "Submit to Intelligence Council"
4. Watch the streaming analysis

### Option 2: Use Test Page
1. Open http://localhost:8000/test_frontend_flow.html
2. Enter a question
3. Click "Submit Question"
4. Monitor stream events in real-time

### Option 3: Use Python Test Script
```powershell
python test_stream.py
```

## Troubleshooting

### Backend Won't Start
**Error**: "Port 8000 already in use"
```powershell
# Kill existing process
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) { Stop-Process -Id $conn.OwningProcess -Force }
```

### Frontend Won't Start
**Error**: "Port 3000 already in use"
```powershell
# Find and kill process on port 3000
Get-Process node | Where-Object {$_.Path -like "*lmis_int*"} | Stop-Process -Force
```

### Connection Errors
1. Verify backend is running: `Invoke-WebRequest http://localhost:8000/health`
2. Check backend logs for errors
3. Ensure `.env` file exists with correct settings
4. Verify database is accessible

### Model Loading Issues
If you see "Loading sentence-transformers model" during requests (not at startup):
- Cache is not working
- Check `src/qnwis/rag/embeddings.py` has `_EMBEDDER_CACHE`
- Restart backend to trigger pre-warming

## Environment Variables

Key settings in `.env`:
```bash
# LLM Provider (stub for testing, anthropic for production)
QNWIS_LLM_PROVIDER=anthropic  # or stub

# API Keys (required for real LLM calls)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...

# Model pre-warming (recommended)
QNWIS_WARM_EMBEDDER=true

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qnwis
```

## Expected Startup Sequence

### Backend Startup
```
INFO: Started server process [xxxxx]
INFO: Waiting for application startup.
INFO: Logging configured: level=INFO, json=True, redaction=True
WARNING: Redis unavailable (optional, for rate limiting)
INFO: Pre-warming sentence embedder model...
INFO: Loading sentence-transformers model: all-mpnet-base-v2
INFO: Model loaded successfully. Embedding dimension: 768
INFO: Embedder warm-up scheduled
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
```

### Frontend Startup
```
VITE vX.X.X  ready in XXX ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
➜  press h + enter to show help
```

## Performance Expectations

- **Backend startup**: 10-15 seconds (includes model pre-warming)
- **First request**: 2-5 seconds
- **Subsequent requests**: <2 seconds overhead
- **Full LLM workflow**: 30-180 seconds (depends on query complexity)

## What Was Fixed

The system was crashing due to:
1. ❌ Model loading on every request (8-15s delay)
2. ❌ No model caching
3. ❌ Frontend timeout too short

Now:
1. ✅ Model cached globally
2. ✅ Pre-warmed at startup
3. ✅ Frontend handles long workflows

See `FRONTEND_CRASH_FIX.md` for detailed analysis.
