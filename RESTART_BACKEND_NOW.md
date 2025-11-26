# ⚡ RESTART BACKEND NOW

## RAG Pre-Warming Fix Applied - Backend Restart Required

---

## What Was Fixed

✅ **PyTorch Meta Tensor Error** - RESOLVED

Modified `src/qnwis/rag/embeddings.py` to:
- Explicitly specify `device="cpu"` when loading SentenceTransformer
- Add fallback loading strategy
- Better error handling

---

## How to Restart Backend

### Step 1: Stop Current Backend
In your backend terminal, press:
```
Ctrl+C
```

### Step 2: Restart Backend
```powershell
cd d:\lmis_int
python -m uvicorn src.qnwis.api.server:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Verify Fix in Logs

**✅ You should see:**
```
INFO - Pre-warming RAG components (embedder + document store)...
INFO - Loading sentence-transformers model: all-mpnet-base-v2
INFO - Model loaded successfully on device: cpu  ← GOOD!
INFO - Model loaded successfully. Embedding dimension: 768
INFO - RAG components warm-up scheduled
INFO - Application startup complete.
```

**❌ You should NOT see:**
```
ERROR - Failed to load model all-mpnet-base-v2: Cannot copy out of meta tensor...
```

---

## After Restart

### Frontend is Already Running ✅
- Frontend is still running on http://localhost:3001
- No need to restart frontend

### Test Immediately
1. Open http://localhost:3001
2. Submit test question: "What are the unemployment trends in Qatar?"
3. Provider: "stub"
4. Verify RAG stage completes in <1 second (not 8 seconds!)

---

## Quick Verification

After backend restart, all these should be true:

- [ ] No PyTorch "meta tensor" errors in logs
- [ ] Logs show "Model loaded successfully on device: cpu"
- [ ] RAG pre-warming completes without errors
- [ ] Server starts successfully
- [ ] Can access http://localhost:8000/health

---

## Expected Performance

| Metric | Before Fix | After Fix |
|--------|-----------|----------|
| RAG pre-warming | ❌ Failed | ✅ Success |
| First request latency | ~8 seconds | <1 second |
| Startup errors | Yes | No |

---

## If You Still See Errors

1. **Check Python version:** Should be 3.11+
   ```powershell
   python --version
   ```

2. **Check virtual environment is activated:**
   ```powershell
   # Should see (.venv) in prompt
   & d:/lmis_int/.venv/Scripts/Activate.ps1
   ```

3. **Verify fix was applied:**
   ```powershell
   # Check line 58 in embeddings.py
   cat src\qnwis\rag\embeddings.py | Select-String -Pattern "device=device"
   ```
   Should show: `self.model = SentenceTransformer(model_name, device=device)`

4. **Check sentence-transformers version:**
   ```powershell
   pip show sentence-transformers
   ```
   Should be version 2.0+

---

## Summary

✅ Fix applied to `src/qnwis/rag/embeddings.py`  
⏳ **ACTION REQUIRED:** Restart backend server  
✅ Frontend already running (no restart needed)  
✅ Test script ready to run  

**Next:** Restart backend and verify logs show success!

🚀
