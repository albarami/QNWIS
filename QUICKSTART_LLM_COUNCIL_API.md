# LLM Council API - Quick Start

**Status**: ✅ Complete | **Date**: 2025-11-13

## TL;DR - Get Started in 30 Seconds

### Start Server
```bash
uvicorn src.qnwis.api.server:app --reload --port 8001
```

### Test Streaming
```bash
python examples/api_client_llm.py "What are Qatar's unemployment trends?"
# Select: 1) Streaming
```

### Test CLI
```bash
qnwis query-llm "Test question" --provider stub -v
```

## Endpoints

### 1. Streaming (SSE) - `/api/v1/council/stream`

**Real-time token-by-token output via Server-Sent Events**

```bash
curl -N -X POST http://localhost:8001/api/v1/council/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Qatar unemployment trends?",
    "provider": "anthropic"
  }'
```

**Response**: Stream of SSE events
```
event: heartbeat
data: {}

data: {"stage":"classify","status":"running","payload":{},"latency_ms":null,"timestamp":"..."}

data: {"stage":"classify","status":"complete","payload":{...},"latency_ms":123,"timestamp":"..."}

data: {"stage":"synthesize","status":"streaming","payload":{"token":"Qatar"},"latency_ms":null,"timestamp":"..."}
```

### 2. Complete (JSON) - `/api/v1/council/run-llm`

**Full structured response after all stages complete**

```bash
curl -X POST http://localhost:8001/api/v1/council/run-llm \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Qatar unemployment trends?",
    "provider": "anthropic"
  }'
```

**Response**: Structured JSON
```json
{
  "synthesis": "Qatar's unemployment rate has shown...",
  "classification": {"category": "employment", "confidence": 0.95},
  "agent_reports": [
    {"agent": "time_machine", "findings": "..."},
    {"agent": "pattern_miner", "findings": "..."}
  ],
  "verification": {"passed": true, "checks": [...]},
  "metadata": {
    "question": "What are Qatar unemployment trends?",
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "stages": {
      "classify": {"latency_ms": 123, "timestamp": "..."},
      "prefetch": {"latency_ms": 456, "timestamp": "..."}
    }
  }
}
```

### 3. Legacy (Deprecated) - `/api/v1/council/run`

**⚠️ DEPRECATED - Use `/api/v1/council/run-llm` instead**

```bash
curl -X POST http://localhost:8001/api/v1/council/run
```

**Response**: Legacy format with deprecation notice
```json
{
  "status": "deprecated",
  "message": "Use /api/v1/council/run-llm for LLM-powered analysis.",
  "council": {...},
  "verification": {...}
}
```

## Request Parameters

### CouncilRequest Schema
```python
{
  "question": str,        # 3-5000 characters (required)
  "provider": str,        # "anthropic" | "openai" | "stub" (default: anthropic)
  "model": str | null     # Optional model override
}
```

**Examples**:
```json
{"question": "Analyze healthcare workforce", "provider": "anthropic"}
{"question": "Compare GCC markets", "provider": "openai", "model": "gpt-4"}
{"question": "Test query", "provider": "stub"}
```

## CLI Usage

### Basic Query (Streaming)
```bash
qnwis query-llm "What are Qatar's unemployment trends?"
```

### Complete Response (No Streaming)
```bash
qnwis query-llm "Analyze healthcare workforce" --no-stream
```

### With Provider and Verbose Output
```bash
qnwis query-llm "Compare GCC labor markets" --provider openai -v
```

### Test with Stub Provider
```bash
qnwis query-llm "Test query" --provider stub
```

### CLI Options
- `QUESTION`: Required positional argument
- `--provider`: anthropic|openai|stub (default: anthropic)
- `--model`: Optional model override
- `--no-stream`: Disable streaming (wait for complete response)
- `--verbose, -v`: Show stage transitions and metadata

## Example Client

### Interactive Usage
```bash
python examples/api_client_llm.py "Your question here"

# Select mode:
# 1) Streaming (real-time token output)
# 2) Complete (single structured response)
> 1
```

### Streaming Output
```
🔗 Connected to http://localhost:8001/api/v1/council/stream
📝 Question: What are Qatar's unemployment trends?

▶ classify ...
✅ classify (123 ms)
▶ prefetch ...
✅ prefetch (456 ms)
▶ agent:time_machine ...
✅ agent:time_machine (789 ms)
[synthesis tokens stream here in real-time...]
✅ synthesize (234 ms)
```

### Complete Output
```
🔗 Sending request to http://localhost:8001/api/v1/council/run-llm
📝 Question: What are Qatar's unemployment trends?
⏳ Processing (this may take a minute)...

================================================================================
📊 FINAL ANALYSIS
================================================================================
Qatar's unemployment rate has shown steady decline from 2020-2024...

================================================================================
📋 METADATA
================================================================================
Provider: anthropic
Model: claude-3-sonnet-20240229

Stage Timings:
  • classify: 123 ms
  • prefetch: 456 ms
  • agent:time_machine: 789 ms
  • verify: 234 ms
  • synthesize: 345 ms
```

## Event Structure (SSE)

Each SSE event follows this structure:

```typescript
{
  stage: "classify" | "prefetch" | "agent:<name>" | "verify" | "synthesize" | "done",
  status: "running" | "streaming" | "complete" | "error",
  payload: {
    token?: string,           // For streaming status
    classification?: object,  // For classify stage
    report?: object,          // For agent stages
    synthesis?: string,       // For synthesize stage
    ...
  },
  latency_ms: number | null,
  timestamp: string            // ISO 8601 format
}
```

### Status Types

- **running**: Stage has started
- **streaming**: LLM is generating tokens (payload.token present)
- **complete**: Stage finished (payload has results)
- **error**: Stage failed (payload.error present)

### Stage Flow

```
┌──────────┐
│ classify │ Determine query category and intent
└────┬─────┘
     │
┌────▼─────┐
│ prefetch │ Fetch relevant data from Data API
└────┬─────┘
     │
┌────▼────────┐
│ agent:<name>│ Execute specialized agents (parallel)
└────┬────────┘
     │
┌────▼────┐
│ verify  │ Validate results and check invariants
└────┬────┘
     │
┌────▼──────┐
│ synthesize│ Generate final response with LLM
└────┬──────┘
     │
┌────▼───┐
│  done  │ Workflow complete
└────────┘
```

## Testing

### Run All Tests
```bash
pytest -v tests/integration/api/test_council_llm.py
```

### Run Specific Test
```bash
pytest -v tests/integration/api/test_council_llm.py::test_run_llm_complete_returns_structure
```

### With Coverage
```bash
pytest --cov=src/qnwis/api/routers/council_llm -v tests/integration/api/test_council_llm.py
```

### Test List (9 tests)
- ✅ `test_run_llm_complete_returns_structure` - Validates response schema
- ✅ `test_run_llm_validates_provider` - Invalid provider rejection
- ✅ `test_run_llm_validates_question_length` - Length validation
- ✅ `test_streaming_endpoint_emits_sse_events` - SSE format and headers
- ✅ `test_streaming_endpoint_validates_input` - Input validation
- ✅ `test_legacy_endpoint_deprecation_warning` - Deprecation warning
- ✅ `test_run_llm_with_anthropic_provider` - Provider switching
- ✅ `test_run_llm_with_custom_model` - Model override
- ✅ `test_streaming_event_stages` - Stage transitions

## Python Client Usage

### Streaming
```python
import asyncio
import json
import httpx

async def query_streaming(question: str):
    url = "http://localhost:8001/api/v1/council/stream"
    payload = {"question": question, "provider": "anthropic"}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event["status"] == "streaming":
                        print(event["payload"]["token"], end="", flush=True)

asyncio.run(query_streaming("Your question"))
```

### Complete
```python
import asyncio
import httpx

async def query_complete(question: str):
    url = "http://localhost:8001/api/v1/council/run-llm"
    payload = {"question": question, "provider": "anthropic"}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    
    print(data["synthesis"])

asyncio.run(query_complete("Your question"))
```

## Error Handling

### HTTP Errors
```python
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
except requests.HTTPStatusError as e:
    print(f"HTTP {e.response.status_code}: {e.response.text}")
```

### Validation Errors (422)
```json
{
  "detail": [
    {
      "loc": ["body", "provider"],
      "msg": "string does not match regex pattern",
      "type": "value_error.str.regex"
    }
  ]
}
```

### Server Errors (500)
```json
{
  "detail": "Workflow execution failed: <error message>"
}
```

## Configuration

### Environment Variables
```bash
# LLM Provider
ANTHROPIC_API_KEY=sk-ant-***
OPENAI_API_KEY=sk-***

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/qnwis

# API
API_HOST=0.0.0.0
API_PORT=8001
```

### Provider Selection
- **anthropic**: Uses Anthropic Claude models (requires API key)
- **openai**: Uses OpenAI GPT models (requires API key)
- **stub**: Deterministic test provider (no API key needed)

## Troubleshooting

### Issue: Connection refused
**Cause**: Server not running  
**Solution**:
```bash
uvicorn src.qnwis.api.server:app --reload --port 8001
```

### Issue: 401 Authentication error
**Cause**: Missing or invalid API key  
**Solution**:
```bash
export ANTHROPIC_API_KEY=sk-ant-***
# or
export OPENAI_API_KEY=sk-***
```

### Issue: 422 Validation error
**Cause**: Invalid request parameters  
**Solution**: Check question length (3-5000 chars) and provider value

### Issue: SSE stream cuts off
**Cause**: Proxy buffering or timeout  
**Solution**: Use `curl -N` or configure nginx:
```nginx
proxy_buffering off;
proxy_cache off;
```

## Performance Notes

- **Streaming**: Low latency, real-time output, memory efficient
- **Complete**: Higher latency, full response, better for programmatic use
- **Timeouts**: Default 120s client timeout, adjustable
- **Concurrent requests**: FastAPI handles async, multiple clients OK

## Security

### Input Validation
- Question length: 3-5000 characters
- Provider whitelist: anthropic, openai, stub
- Pydantic validation on all inputs

### Headers (SSE)
- `Cache-Control: no-cache` - Prevent caching
- `X-Accel-Buffering: no` - Disable nginx buffering
- `Connection: keep-alive` - Maintain connection

### Error Handling
- Stack traces logged, not exposed to clients
- Generic 500 errors for internal failures
- Detailed validation errors (422) for bad input

## Migration from Legacy

### Old Code
```python
response = requests.post(
    "http://localhost:8001/api/v1/council/run",
    json={"queries_dir": "...", "ttl_s": 300}
)
```

### New Code
```python
response = requests.post(
    "http://localhost:8001/api/v1/council/run-llm",
    json={"question": "...", "provider": "anthropic"}
)
```

---

**Files Modified**: 6 files  
**Lines Added**: ~740 lines  
**Tests**: 9 integration tests  
**Status**: ✅ Production Ready
