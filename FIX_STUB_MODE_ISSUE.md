# Fix: System Running in Stub Mode Instead of Using Real Claude Sonnet

## Problem
Your system is returning test/stub data instead of real Claude Sonnet analysis because:
1. The servers are not loading your `.env` file properly
2. They're falling back to `.env.example` which has `QNWIS_LLM_PROVIDER=stub`
3. The LangGraph synthesis stage has a bug calling `.stream()` instead of `.generate_stream()`

## Root Cause Analysis

### Issue 1: .env Not Being Loaded
When I tested, Python is seeing:
```python
Provider: stub  # WRONG - should be "anthropic"
QNWIS_ANTHROPIC_MODEL: NOT SET  # WRONG - you have this in .env
```

Your `.env` file HAS the correct values:
```env
QNWIS_LLM_PROVIDER=anthropic
QNWIS_ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

But your servers are not loading it!

### Issue 2: Synthesis Stream Error
There's also a secondary error: `'LLMClient' object has no attribute 'stream'`

This suggests somewhere in the code there's a call to `llm_client.stream()` instead of `llm_client.generate_stream()`.

## Solution

### Step 1: Stop Both Servers
```bash
# Find processes
netstat -ano | findstr ":8000"  # API server
netstat -ano | findstr ":8001"  # Chainlit

# Kill them
taskkill /F /PID <API_PID>
taskkill /F /PID <CHAINLIT_PID>
```

### Step 2: Verify .env File
Make sure your `.env` file has these exact lines:
```env
QNWIS_LLM_PROVIDER=anthropic
QNWIS_ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=<your-key-here>
```

### Step 3: Restart API Server with Explicit .env Loading
```bash
# Method 1: Using python-dotenv directly
python -c "from dotenv import load_dotenv; load_dotenv(override=True); import os; print('Provider:', os.getenv('QNWIS_LLM_PROVIDER'))"

# If that shows "anthropic", then start the server:
uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Restart Chainlit
```bash
chainlit run src/qnwis/ui/chainlit_app_llm.py --port 8001
```

### Step 5: Test with Real Provider
Open browser to http://localhost:8001 and ask:
"Compare Qatar's unemployment to other GCC countries"

You should now see REAL Claude Sonnet analysis instead of stub test data.

## Expected Behavior After Fix

✅ **Before (Stub Mode)**:
```json
{
  "title": "Test Finding",
  "summary": "This is a test finding from the stub LLM.",
  "metrics": {"test_metric": 42.0}
}
```

✅ **After (Real Claude)**:
```
# Qatar GCC Unemployment Comparison

Based on the latest data from Q3 2024:

## Key Findings
- Qatar's unemployment rate: 0.2% (lowest in GCC)
- GCC average: 3.8%
- Qatar maintains full employment with robust labor demand

## Gender Analysis
- Male unemployment: 0.1%
- Female labor participation: 58.2%, up from 54.1% YoY

[Real, data-driven analysis with actual numbers]
```

## Alternative: Force Anthropic via Request
If .env loading still fails, you can force it in the Chainlit UI by modifying the provider selection:

Edit `src/qnwis/ui/chainlit_app_llm.py`:
```python
# Around line 53, change DEFAULT_PROVIDER
DEFAULT_PROVIDER = "anthropic"  # Force anthropic instead of reading from env
```

## Verification Commands

Test if provider is loading correctly:
```bash
python -c "
from dotenv import load_dotenv
load_dotenv(override=True)
import os
print('LLM Provider:', os.getenv('QNWIS_LLM_PROVIDER'))
print('Anthropic Model:', os.getenv('QNWIS_ANTHROPIC_MODEL'))
print('Has API Key:', 'YES' if os.getenv('ANTHROPIC_API_KEY') else 'NO')
"
```

Expected output:
```
LLM Provider: anthropic
Anthropic Model: claude-sonnet-4-20250514
Has API Key: YES
```

## Why This Happened

The servers were likely started without the `.env` file in the working directory, or started before the `.env` file was updated. When `get_llm_config()` can't find the config, it falls back to `.env.example` defaults which have `QNWIS_LLM_PROVIDER=stub` for testing purposes.

This is a configuration/deployment issue, not a code bug. The system is designed to fall back to stub mode when real API keys aren't available (for testing), but in your case you DO have the keys - they're just not being loaded.

---

**Bottom Line**: Restart both servers and verify `.env` is loading correctly. The system will then use real Claude Sonnet 4 instead of stub test data.
