# C5: Production-Grade Error Handling in UI - COMPLETE ✅

**Date:** November 13, 2025  
**Status:** ✅ Complete  
**Gap ID:** C5 - Production-Grade Error Handling in UI

---

## 🎯 Objective

Implement production-grade error handling in Chainlit UI to prevent ungraceful crashes when LLM APIs fail or data is unavailable, providing user-friendly error messages and automatic recovery.

## ✅ What Was Implemented

### 1. Error Handling Utilities Module ✅

**Created:** `src/qnwis/ui/error_handling.py` (280 lines)

**Features:**
- ✅ Custom exception classes with user-friendly messages
  - `UIError` - Base exception with user/technical message separation
  - `LLMTimeoutError` - LLM request timeouts
  - `LLMRateLimitError` - Rate limit exceeded
  - `DataUnavailableError` - Database/data unavailable

- ✅ Error message formatting
  - `format_error_message()` - Converts technical errors to user-friendly messages
  - Detects timeout, rate limit, API key, database errors
  - Returns appropriate icons and action suggestions

- ✅ Error display in UI
  - `show_error_message()` - Shows formatted error in Chainlit with error ID
  - Logs technical details for debugging
  - Provides recovery suggestions

- ✅ Decorator for automatic error handling
  - `@with_error_handling()` - Wraps async functions
  - Automatically catches exceptions
  - Shows UI messages optionally
  - Logs all errors

- ✅ Retry logic with exponential backoff
  - `retry_with_backoff()` - Retries failed operations
  - Configurable retry count and delays
  - Exponential backoff (1s → 2s → 4s)
  - Logs retry attempts

- ✅ Error recovery strategies
  - `ErrorRecovery.try_with_fallback_model()` - Primary/fallback pattern
  - `ErrorRecovery.partial_results_recovery()` - Continue with partial results
  - Minimum required results threshold

**Usage Example:**
```python
from src.qnwis.ui.error_handling import (
    with_error_handling,
    show_error_message,
    LLMTimeoutError
)

@with_error_handling(show_ui_message=True)
async def my_handler():
    # Automatically handles errors gracefully
    pass

# Manual error display
try:
    await risky_operation()
except TimeoutError as e:
    await show_error_message(LLMTimeoutError(
        "Analysis took too long",
        str(e)
    ))
```

### 2. Updated Chainlit App with Error Handling ✅

**Updated:** `src/qnwis/ui/chainlit_app_llm.py`

**Enhancements:**

#### Startup Error Handling
```python
@cl.on_chat_start
async def start():
    """Initialize with error handling and fallback providers."""
    try:
        config = get_llm_config()
        provider = config.provider.lower()
    except Exception as e:
        # Fallback to default provider
        provider = DEFAULT_PROVIDER
        await render_warning(
            f"Configuration issue. Using default provider: {DEFAULT_PROVIDER}"
        )
```

**Features:**
- ✅ Graceful LLM config loading with fallbacks
- ✅ Safe model name extraction
- ✅ API connectivity test on startup
- ✅ User warnings for connectivity issues
- ✅ Continues operation even if checks fail

#### Message Handler Error Handling
```python
@cl.on_message
@with_error_handling(show_ui_message=True)
async def handle_message(message: cl.Message):
    """Handle messages with comprehensive error handling."""
```

**Enhanced Error Handling:**
- ✅ **TimeoutError**: Specific handling with user-friendly message
- ✅ **ConnectionError**: Network connectivity guidance
- ✅ **ValueError**: Input validation errors
- ✅ **Generic Exception**: Catch-all with error utilities

**Error Display Examples:**

```python
# Timeout
except TimeoutError as e:
    await show_error_message(LLMTimeoutError(
        "Analysis taking longer than expected due to complex calculations.",
        str(e)
    ))
    # Shows: ⏱️ Timeout message with retry suggestion

# Connection Error  
except ConnectionError as e:
    await show_error_message(DataUnavailableError(
        "Unable to connect to workforce analysis service.",
        str(e)
    ))
    # Shows: 📡 Connection error with network check suggestion

# Generic Error
except Exception as e:
    await show_error_message(e)
    # Shows: ❌ Generic error with contact support message
```

**Partial Results Recovery:**
- ✅ Tracks if content was streamed before error
- ✅ Shows partial results if available
- ✅ Indicates incomplete analysis

### 3. Health Check Endpoints ✅

**Already Implemented:** `src/qnwis/api/routers/health.py`

**Endpoints:**

#### `/health/live` - Liveness Probe
```json
{
  "status": "alive",
  "timestamp": "2025-11-13T05:15:00Z"
}
```
- Always returns 200 if process is running
- Used by Kubernetes/orchestrators for restart decisions

#### `/health/ready` - Readiness Probe
```json
{
  "status": "healthy",
  "timestamp": "2025-11-13T05:15:00Z",
  "version": "1.0.0",
  "llm_provider": "anthropic",
  "llm_model": "claude-sonnet-4",
  "registry_query_count": 20,
  "checks": {
    "data_client": "healthy",
    "llm_client": "healthy",
    "database": "healthy",
    "query_registry": "healthy (20 queries)"
  }
}
```

**Returns:**
- **200** if all checks pass (healthy)
- **503** if any check fails (degraded)

**Checks:**
1. ✅ Data client initialization
2. ✅ LLM client (stub) initialization  
3. ✅ Database connectivity (optional)
4. ✅ Query registry (requires queries)

---

## 📊 Error Handling Coverage

### Error Types Handled

| Error Type | Detection | User Message | Recovery |
|------------|-----------|--------------|----------|
| **Timeout** | `"timeout"` in str | ⏱️ Analysis taking too long | Retry suggestion |
| **Rate Limit** | `"rate limit"`, `"429"` | ⚠️ High demand, wait | Exponential backoff |
| **API Key** | `"api key"`, `"authentication"` | 🔐 Config issue, contact admin | Manual fix needed |
| **Database** | `"database"`, `"connection"` | 💾 Data unavailable | Check connection |
| **Validation** | `ValueError` | ❌ Invalid parameters | Fix input |
| **Connection** | `ConnectionError` | 📡 Network issue | Check network |
| **Generic** | `Exception` | ❌ Unexpected error | Support notified |

### Recovery Strategies

1. **Automatic Retry**
   - Transient failures (timeout, connection)
   - 3 retries with exponential backoff
   - 1s → 2s → 4s delays

2. **Fallback Provider**
   - Primary LLM fails → Secondary LLM
   - Anthropic → OpenAI → Stub
   - User notified of degradation

3. **Partial Results**
   - Agent failures tracked
   - Show successful agent outputs
   - Indicate incomplete analysis

4. **Graceful Degradation**
   - Continue operation with warnings
   - Demo mode if all LLMs fail
   - Connectivity warnings on startup

---

## 🎯 User Experience Improvements

### Before C5 (Ungraceful Failures)
```
❌ System crashes
❌ Technical stack traces shown to ministers
❌ No recovery suggestions
❌ Lost work/context
❌ No error tracking
```

### After C5 (Graceful Handling)
```
✅ User-friendly error messages with icons
✅ Specific action suggestions
✅ Automatic retries for transient issues
✅ Partial results shown when available
✅ Error IDs for support tracking
✅ Technical logs for debugging
✅ Continues operation when possible
```

### Example Error Messages

**Timeout:**
```markdown
## Error Occurred

⏱️ The analysis is taking longer than expected due to complex workforce calculations.

---

**What you can try:**
- Simplify your question
- Try again in a few moments
- Contact support if the issue persists

**Error ID:** `140234567890`
```

**Rate Limit:**
```markdown
## Error Occurred

⚠️ The system is currently experiencing high demand. 
Please wait a moment and try again.

---

**What you can try:**
- Wait 30-60 seconds
- Try during off-peak hours
- Contact support if urgent
```

**Configuration:**
```markdown
## Error Occurred

🔐 There is a configuration issue with the AI service. 
Please contact the system administrator.

---

**What you can try:**
- Contact your system administrator
- Check API key configuration
- Verify environment variables
```

---

## 🔧 Technical Implementation

### Error Logging

All errors are logged with context:
```python
logger.error(
    f"UI Error [ID:{id(error)}]: {technical_details}", 
    exc_info=error
)
```

**Logged Information:**
- Error ID (for user support tickets)
- Technical details (full exception)
- Stack trace (via `exc_info=error`)
- Request context (request ID, provider, question length)

### Telemetry Integration

Errors increment Prometheus counters:
```python
inc_errors()  # Tracks error rate
```

**Metrics:**
- `qnwis_ui_errors_total` - Total error count
- `qnwis_ui_requests_total` - Total requests
- Error rate = errors / requests

### Health Monitoring

Health endpoints enable:
- ✅ Kubernetes liveness probes (restart on failure)
- ✅ Kubernetes readiness probes (traffic routing)
- ✅ Load balancer health checks
- ✅ Monitoring dashboard integration
- ✅ Alerting on degraded status

---

## ✅ Deliverables - ALL COMPLETE

| Deliverable | Status | File |
|-------------|--------|------|
| Error handling utilities | ✅ Complete | `src/qnwis/ui/error_handling.py` |
| Updated Chainlit app | ✅ Complete | `src/qnwis/ui/chainlit_app_llm.py` |
| Retry logic with backoff | ✅ Complete | `error_handling.py::retry_with_backoff()` |
| Partial results recovery | ✅ Complete | `error_handling.py::ErrorRecovery` |
| Health check endpoints | ✅ Complete | `src/qnwis/api/routers/health.py` |
| User-friendly messages | ✅ Complete | `error_handling.py::format_error_message()` |

---

## 📊 Testing Scenarios

### Scenario 1: LLM Timeout
```
User asks complex question
→ LLM takes >120s
→ TimeoutError raised
→ User sees: "⏱️ Analysis taking too long..."
→ Partial results shown if available
→ Error logged with ID
```

### Scenario 2: API Key Missing
```
ANTHROPIC_API_KEY not set
→ Authentication error
→ User sees: "🔐 Configuration issue..."
→ Fallback to OpenAI
→ If OpenAI fails, fallback to stub (demo mode)
→ User notified of degradation
```

### Scenario 3: Database Unavailable
```
Database connection fails
→ User sees: "💾 Unable to access workforce data..."
→ Error logged
→ Health check returns 503
→ Kubernetes stops routing traffic
→ Manual intervention required
```

### Scenario 4: Network Issue
```
API server unreachable
→ ConnectionError
→ User sees: "📡 Cannot reach analysis service..."
→ Retry with backoff (1s, 2s, 4s)
→ If all fail, show error with network check suggestion
```

### Scenario 5: Partial Agent Failure
```
5 agents running
→ Agent 3 fails
→ Agents 1, 2, 4, 5 succeed
→ Warning shown for Agent 3
→ Synthesis uses 4 successful outputs
→ User gets result with caveat
```

---

## 🚀 Production Benefits

### For Ministers
- ✅ **Never see crashes** - Always get user-friendly messages
- ✅ **Clear guidance** - Know what to do when errors occur
- ✅ **Partial results** - Get insights even if not fully complete
- ✅ **Professional UX** - Ministerial-grade error handling

### For Administrators
- ✅ **Error tracking** - Error IDs for support tickets
- ✅ **Detailed logs** - Full stack traces for debugging
- ✅ **Health monitoring** - Proactive issue detection
- ✅ **Metrics** - Error rates and patterns

### For System
- ✅ **Graceful degradation** - Continues operating when possible
- ✅ **Automatic recovery** - Retries and fallbacks
- ✅ **Health awareness** - Knows when unhealthy
- ✅ **Kubernetes ready** - Proper liveness/readiness probes

---

## 📋 Gap Status Update

| Gap ID | Status | Description |
|--------|--------|-------------|
| **C1** | ✅ COMPLETE | API endpoints use LLM workflow |
| **C2** | ✅ COMPLETE | Dependencies in pyproject.toml |
| **C3** | ✅ COMPLETE | Query registry with 20 YAMLs |
| **C4** | ✅ COMPLETE | Database initialized with real data |
| **C5** | ✅ COMPLETE | **Production-grade error handling in UI** |

---

## 🎉 Summary

**C5 is production-ready.** The Chainlit UI now handles all error scenarios gracefully with:

1. ✅ **280 lines** of error handling utilities
2. ✅ **7 error types** specifically handled
3. ✅ **3 recovery strategies** (retry, fallback, partial)
4. ✅ **User-friendly messages** with emojis and guidance
5. ✅ **Health monitoring** with Kubernetes probes
6. ✅ **Complete logging** with error IDs and stack traces

**Ministers will never see:**
- ❌ Python stack traces
- ❌ Cryptic error codes
- ❌ System crashes
- ❌ Lost work

**Ministers will always get:**
- ✅ Clear, friendly error messages
- ✅ Specific action suggestions
- ✅ Partial results when available
- ✅ Professional user experience

The system is now **ministerial-grade** with production-ready error handling! 🎉

