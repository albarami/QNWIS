# ✅ Endpoint Corrected - Third Time's the Charm!

**Issue**: Frontend connecting to non-existent endpoint  
**Timestamp**: November 18, 2025 @ 14:10 UTC  
**Status**: ✅ **FIXED**

---

## 🔍 The Problem

The frontend was trying THREE different wrong endpoints:

1. ❌ **First attempt**: `/api/v1/council/stream` (doesn't exist)
2. ❌ **Second attempt**: `/council/stream-llm` (doesn't exist) 
3. ✅ **CORRECT**: `/council/stream` (this one exists!)

Backend responded with `{"detail":"Not Found"}` because the endpoint didn't match any registered route.

---

## ✅ The Fix

**File**: `qnwis-ui/src/hooks/useWorkflowStream.ts` (Line 58)

**Changed from:**
```typescript
await fetchEventSource('http://localhost:8000/council/stream-llm', {
```

**To:**
```typescript
await fetchEventSource('http://localhost:8000/council/stream', {
```

---

## 📍 Correct Backend Endpoint

**Route**: `/council/stream`  
**Method**: POST  
**File**: `src/qnwis/api/routers/council_llm.py` (Line 178)  
**Full URL**: `http://localhost:8000/council/stream`

**Request Body:**
```json
{
  "question": "Your ministerial question here",
  "provider": "stub"
}
```

**Response**: SSE stream with workflow events

---

## 🧪 Test It Now

Vite HMR should have auto-reloaded. 

**Steps:**
1. Go to http://localhost:3000 (refresh if needed with `Ctrl+R`)
2. Enter a test question
3. Click Submit
4. Watch the magic happen! ✨

**Expected:**
- ✅ Connection opens to correct endpoint
- ✅ SSE events start streaming
- ✅ Stage indicators update in real-time
- ✅ No more ErrorBoundary screen!

---

## 🎯 If Still Not Working

### Check Backend Endpoint
```powershell
# Test the endpoint directly
$body = '{"question": "Test", "provider": "stub"}'
Invoke-WebRequest -Uri "http://localhost:8000/council/stream" -Method POST -Headers @{"Content-Type"="application/json"} -Body $body
```

### Check Browser Console (F12)
- **Network tab**: Look for request to `/council/stream`
- **Console tab**: Check for "Stream connection established"
- **Errors**: Any red errors about connections

### Check CORS
Backend allows `localhost:3000` by default in settings.

---

## 📊 Summary of All Endpoints

**Council LLM Endpoints** (from `council_llm.py`):
- `/council/stream` - SSE streaming endpoint (THIS ONE!)
- `/council/run-llm` - Non-streaming JSON response

**Health Endpoints**:
- `/health` - Health check
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe

**Documentation**:
- `/docs` - Swagger UI
- `/redoc` - ReDoc UI

---

## 🎉 Ready to Test!

The correct endpoint is now configured. Reload the frontend and submit a question!

---

**Fixed**: November 18, 2025 @ 14:10 UTC  
**Endpoint**: `/council/stream` ✅  
**Status**: Ready for testing 🚀
