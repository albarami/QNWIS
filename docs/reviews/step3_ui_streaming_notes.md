# UI Streaming Integration - Developer Notes & Operational Runbook

**Date**: 2025-11-13  
**Component**: Chainlit UI + SSE Streaming  
**Status**: Production Ready

## Overview

This document describes the implementation of real-time ministerial streaming in the QNWIS Chainlit UI, including SSE client integration, health telemetry, and operational procedures.

## Architecture

### Component Stack

```
┌─────────────────────────────────────┐
│   Chainlit UI (chainlit_app_llm.py) │
│   - User interaction                 │
│   - Message handling                 │
│   - Token streaming display          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   SSE Client (streaming_client.py)  │
│   - HTTP/SSE connection              │
│   - Retry logic with backoff         │
│   - Event parsing                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   API Gateway (/api/council/stream) │
│   - FastAPI SSE endpoint             │
│   - Event generation                 │
│   - Request correlation              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   LLM Workflow (run_workflow_stream)│
│   - Multi-stage execution            │
│   - Agent coordination               │
│   - Token generation                 │
└─────────────────────────────────────┘
```

### Data Flow

1. **User submits question** → Chainlit `handle_message()`
2. **SSEClient.stream()** → Establishes connection to `/api/council/stream`
3. **Server generates events** → Workflow emits: running, streaming, complete, error
4. **Client parses SSE** → Extracts `{stage, status, payload, latency_ms, timestamp}`
5. **UI renders** → Progress panel + token streaming + completion messages
6. **Telemetry tracks** → Requests, tokens, errors, latencies

## Implementation Details

### SSE Client (`streaming_client.py`)

**Key Features**:
- Exponential backoff retry (0.5s, 1s, 2s)
- Request ID correlation (UUID v4)
- Heartbeat handling
- Malformed JSON graceful degradation
- Non-blocking async iteration

**Configuration**:
```python
client = SSEClient(
    base_url="http://localhost:8001",  # From QNWIS_API_URL env var
    timeout=120.0                       # 2 minutes for long workflows
)
```

**Usage**:
```python
async for event in client.stream(question="...", provider="anthropic"):
    if event.status == "streaming":
        await display_token(event.payload["token"])
    elif event.status == "complete":
        await show_completion(event.stage, event.latency_ms)
```

### Telemetry (`telemetry.py`)

**Metrics (Prometheus)**:
- `qnwis_ui_requests_total` - Total questions processed
- `qnwis_ui_tokens_streamed_total` - Tokens sent to UI
- `qnwis_ui_stage_latency_ms` - Stage completion times (histogram)
- `qnwis_ui_stream_errors_total` - Streaming failures

**Safe Fallback**:
If `prometheus_client` not installed, all metrics become no-ops. No exceptions raised.

**Usage**:
```python
from src.qnwis.ui.telemetry import inc_requests, inc_tokens, stage_timer

inc_requests()                    # Counter increment
inc_tokens(len(tokens))           # Bulk increment
with stage_timer():               # Latency tracking
    await process_stage()
```

### Progress Panel (`components/progress_panel.py`)

**Stage Labels**:
- 🔍 Classifying question
- 📊 Preparing data
- ⏰ Time Machine (agent)
- 🔬 Pattern Miner (agent)
- ✅ Verifying results
- 📝 Synthesizing findings

**Functions**:
```python
await render_stage("classify", latency_ms=123, status="complete")
await render_error("Connection failed. Retrying...")
await render_warning("Stage encountered issue but continuing")
await render_info("Analysis complete!")
```

### Health Endpoints (`api/routers/health.py`)

#### Liveness Probe: `GET /api/health/live`

**Purpose**: Indicates process is alive  
**Returns**: Always 200  
**Response**:
```json
{
  "status": "alive",
  "timestamp": "2025-11-13T00:00:00Z"
}
```

**Use Case**: Kubernetes liveness probe, container restart decisions

#### Readiness Probe: `GET /api/health/ready`

**Purpose**: Indicates service can handle traffic  
**Returns**: 200 (healthy) or 503 (degraded)  
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-13T00:00:00Z",
  "checks": {
    "data_client": "healthy",
    "llm_client": "healthy",
    "database": "healthy",
    "query_registry": "healthy (42 queries)"
  }
}
```

**Subsystem Checks**:
1. **data_client**: Can initialize DataClient
2. **llm_client**: Can initialize LLMClient with stub provider
3. **database**: Can connect and execute SELECT 1 (optional)
4. **query_registry**: Has queries loaded (critical)

**Use Case**: Kubernetes readiness probe, load balancer decisions

## Operational Procedures

### Starting the UI

```bash
# Development
export QNWIS_API_URL=http://localhost:8001
chainlit run src/qnwis/ui/chainlit_app_llm.py -w --port 8002

# Production
export QNWIS_API_URL=https://api.qnwis.gov.qa
chainlit run src/qnwis/ui/chainlit_app_llm.py --port 8002 --host 0.0.0.0
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `QNWIS_API_URL` | `http://localhost:8001` | API base URL |
| `ANTHROPIC_API_KEY` | - | LLM provider API key |
| `OPENAI_API_KEY` | - | Alternative LLM provider |

### Health Monitoring

**Check Service Health**:
```bash
# Liveness
curl http://localhost:8001/api/health/live
# Expected: {"status": "alive", ...}

# Readiness
curl http://localhost:8001/api/health/ready
# Expected: {"status": "healthy", ...} with 200 status
```

**Prometheus Metrics** (if installed):
```bash
curl http://localhost:8001/metrics | grep qnwis_ui
```

Expected metrics:
```
qnwis_ui_requests_total 42
qnwis_ui_tokens_streamed_total 15234
qnwis_ui_stream_errors_total 0
```

### Troubleshooting

#### Issue: UI shows "Streaming failed"

**Symptoms**: Error message in UI, no synthesis displayed

**Diagnosis**:
1. Check API health: `curl http://localhost:8001/api/health/ready`
2. Check logs: `grep "streaming_client" /var/log/qnwis/ui.log`
3. Verify network: `curl -v http://localhost:8001/api/council/stream`

**Solutions**:
- API down → Restart API service
- Network issue → Check firewall/proxy settings
- Timeout → Increase `SSEClient(timeout=180.0)`

#### Issue: 503 Service Unavailable

**Symptoms**: `/api/health/ready` returns 503

**Diagnosis**:
```bash
curl http://localhost:8001/api/health/ready | jq '.checks'
```

Look for checks marked "unhealthy":
- `data_client`: Database connection issue
- `llm_client`: LLM config problem
- `query_registry`: Missing query files

**Solutions**:
- `data_client` unhealthy → Check database connection
- `llm_client` unhealthy → Verify LLM config, API keys
- `query_registry` unhealthy → Ensure query files in `data/deterministic/queries/`

#### Issue: No Prometheus metrics

**Symptoms**: `/metrics` endpoint missing or empty

**Diagnosis**:
```bash
python -c "import prometheus_client; print('OK')"
```

**Solution**:
```bash
pip install prometheus-client>=0.19.0
# Restart services
```

#### Issue: Tokens not streaming in realtime

**Symptoms**: UI shows buffered output instead of token-by-token

**Diagnosis**:
1. Check SSE headers: `curl -N http://localhost:8001/api/council/stream`
2. Verify no proxy buffering: Check nginx/traefik config

**Solutions**:
- Add to nginx config: `proxy_buffering off; proxy_cache off;`
- Add to traefik config: `buffering: false`
- Verify API sends correct headers: `X-Accel-Buffering: no`

### Performance Tuning

**Latency Targets**:
- Stage A (classify): <50ms
- Stage B (prefetch): <60ms
- Stage C (verify): <40ms
- Total workflow: <30s

**Monitoring**:
```bash
# Check stage latencies
curl http://localhost:8001/metrics | grep qnwis_ui_stage_latency

# Percentiles
qnwis_ui_stage_latency_ms_bucket{le="100.0"} 0.95
qnwis_ui_stage_latency_ms_bucket{le="1000.0"} 0.99
```

**Optimization**:
1. Reduce unnecessary data prefetch
2. Cache classification results
3. Parallelize agent execution
4. Use faster LLM models for synthesis

### Kubernetes Deployment

**Deployment YAML**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qnwis-ui
spec:
  replicas: 3
  selector:
    matchLabels:
      app: qnwis-ui
  template:
    spec:
      containers:
      - name: qnwis-ui
        image: qnwis-ui:latest
        ports:
        - containerPort: 8002
        env:
        - name: QNWIS_API_URL
          value: "http://qnwis-api:8001"
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-keys
              key: anthropic
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Testing

**Unit Tests**:
```bash
pytest -v tests/unit/ui/test_sse_parsing.py
```

**Integration Tests**:
```bash
pytest -v tests/integration/api/test_health_endpoints.py
pytest -v tests/integration/ui/test_chainlit_streaming_happy_path.py
```

**Manual Smoke Test**:
1. Start API: `uvicorn src.qnwis.api.server:app --port 8001`
2. Start UI: `chainlit run src/qnwis/ui/chainlit_app_llm.py --port 8002`
3. Open browser: `http://localhost:8002`
4. Submit question: "What are Qatar's unemployment trends?"
5. Verify:
   - Progress messages appear
   - Tokens stream in real-time
   - Completion message shows
   - No errors in logs

## Security Considerations

### API Keys
- Never hardcode API keys in code
- Use environment variables or secrets manager
- Rotate keys regularly

### CORS
- Configure CORS appropriately for production
- Restrict origins to known domains
- Don't use `*` in production

### Rate Limiting
- Implement per-user rate limits
- Protect SSE endpoints from abuse
- Monitor for unusual traffic patterns

### Request Correlation
- Every SSE stream has unique request_id
- Log request_id for tracing
- Include in error reports

## Metrics Dashboard

**Grafana Queries** (Prometheus):

```promql
# Request rate
rate(qnwis_ui_requests_total[5m])

# Token throughput
rate(qnwis_ui_tokens_streamed_total[5m])

# Error rate
rate(qnwis_ui_stream_errors_total[5m])

# P95 latency
histogram_quantile(0.95, qnwis_ui_stage_latency_ms_bucket)

# Health status
up{job="qnwis-api"}
```

## Future Enhancements

1. **Caching**: Cache classification results for similar questions
2. **WebSocket**: Consider WebSocket as alternative to SSE
3. **Multi-provider**: Support provider selection in UI
4. **Feedback**: Add user feedback mechanism for responses
5. **Analytics**: Track question types and user patterns
6. **A/B Testing**: Compare different synthesis strategies

## References

- SSE Specification: https://html.spec.whatwg.org/multipage/server-sent-events.html
- Chainlit Documentation: https://docs.chainlit.io/
- Prometheus Client Python: https://github.com/prometheus/client_python
- FastAPI Streaming: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

## Change Log

- 2025-11-13: Initial implementation with SSE, telemetry, health endpoints
