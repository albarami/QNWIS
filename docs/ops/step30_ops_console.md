# Step 30: Ops Console Implementation

## Overview

Production-grade operations console for incident and alert management with:
- Server-rendered UI (FastAPI + Jinja2 + HTMX)
- Live updates via Server-Sent Events (SSE)
- CSRF protection with signed HMAC tokens
- Role-based access control (RBAC)
- Comprehensive audit trail
- Accessibility-first design

## Architecture

### Technology Stack

- **Backend**: FastAPI
- **Templating**: Jinja2
- **Interactivity**: HTMX 1.9.10
- **Live Updates**: Server-Sent Events (SSE)
- **Styling**: Custom CSS (no external CDN)
- **Security**: CSRF tokens (HMAC-SHA256), RBAC

### Module Structure

```
src/qnwis/ops_console/
├── __init__.py
├── app.py              # FastAPI app factory
├── views.py            # Page handlers and actions
├── csrf.py             # CSRF protection
├── sse.py              # Server-Sent Events
├── templates/          # Jinja2 templates
│   ├── layout.html
│   ├── ops_index.html
│   ├── incidents_list.html
│   ├── incident_detail.html
│   └── alerts_list.html
└── assets/
    └── style.css       # Accessible, high-contrast CSS

## RG-5 Snapshot & Artifacts

![RG-5 Ops Console Badge](../../src/qnwis/docs/audit/badges/rg5_ops_console.svg)

- Gate report: `src/qnwis/docs/audit/ops/ui_gate_report.json`
- Metrics snapshot: `src/qnwis/docs/audit/ops/ui_metrics.json`
- Summary digest: `OPS_UI_SUMMARY.md`
- Badge SVG: `src/qnwis/docs/audit/badges/rg5_ops_console.svg`

```

## Features

### Incident Management

**List View** (`/ops/incidents`)
- Filterable by state, severity, rule ID
- Sortable table with pagination
- Color-coded severity badges
- State indicators (OPEN, ACK, SILENCED, RESOLVED)

**Detail View** (`/ops/incidents/{id}`)
- Full incident information
- Timeline of state changes
- Action forms (Acknowledge, Resolve, Silence)
- Link to audit pack (if available)
- Metadata display

**Actions** (POST with CSRF)
- **Acknowledge**: Mark incident as acknowledged
- **Resolve**: Close incident with optional note
- **Silence**: Suppress until specified time with reason

### Live Updates

**Server-Sent Events** (`/ops/stream/incidents`)
- Real-time incident state changes
- Auto-reconnect support
- Heartbeat every 30 seconds
- Event IDs for replay

**HTMX Integration**
- Partial page updates
- No client-side JavaScript required
- Progressive enhancement

### Security

**CSRF Protection**
- HMAC-SHA256 signed tokens
- Embedded timestamp and TTL (15 minutes)
- Constant-time signature comparison
- Automatic form field injection

**RBAC**
- `analyst`: Read incidents, perform actions
- `admin`: All analyst permissions
- `auditor`: Read-only access
- `service`: Cannot access ops console

**Content Security**
- No inline scripts (except with nonce)
- No third-party JavaScript
- CORS disabled on ops routes
- SameSite cookies

### Accessibility (a11y)

**WCAG 2.1 AA Compliance**
- Semantic HTML5 elements
- ARIA labels and roles
- High contrast color palette (4.5:1 minimum)
- Keyboard navigation support
- Screen reader friendly

**Accessibility Features**
- `<label>` for all form inputs
- Alternative text for images
- Logical heading hierarchy
- Focus indicators (3px solid outline)
- Skip navigation links

### Audit Trail

**Request Tracking**
- Unique request ID per page load
- Request ID in headers and footer
- Logged with all actions

**Action Logging**
- All POST actions logged with:
  - Request ID
  - Actor (user ID)
  - Timestamp
  - Action type and parameters
  - Result

**Audit Footer**
- Visible on all pages
- Shows: Request ID, User, Roles, Timestamp

## API Endpoints

### Pages (GET)

| Endpoint | Description | RBAC |
|----------|-------------|------|
| `GET /` | Dashboard with stats | analyst, admin, auditor |
| `GET /incidents` | List incidents with filters | analyst, admin, auditor |
| `GET /incidents/{id}` | Incident detail | analyst, admin, auditor |
| `GET /alerts` | Alert history (placeholder) | analyst, admin, auditor |
| `GET /stream/incidents` | SSE stream | analyst, admin, auditor |

### Actions (POST)

| Endpoint | Description | RBAC | CSRF |
|----------|-------------|------|------|
| `POST /incidents/{id}/ack` | Acknowledge incident | analyst, admin | ✓ |
| `POST /incidents/{id}/resolve` | Resolve incident | analyst, admin | ✓ |
| `POST /incidents/{id}/silence` | Silence incident | analyst, admin | ✓ |

## CSRF Implementation

### Token Generation

```python
csrf = CSRFProtection(secret_key="...", ttl=900)
token = csrf.generate_token(timestamp)
# token.token format: "timestamp|ttl|signature"
```

### Token Verification

```python
valid = csrf.verify_token(token.token, current_timestamp)
# Checks: signature match, TTL not exceeded
```

### Form Integration

```jinja2
<form method="post" action="/ops/incidents/{{ incident_id }}/ack">
    {{ csrf_field(csrf_token)|safe }}
    <button type="submit">Acknowledge</button>
</form>
```

### FastAPI Dependency

```python
from src.qnwis.ops_console.csrf import verify_csrf_token

@router.post("/incidents/{incident_id}/ack")
async def incident_ack(
    csrf_token: str = Form(...),
    _csrf_check: None = Depends(verify_csrf_token),
):
    # Action implementation
    pass
```

## SSE (Server-Sent Events)

### Event Format

```
id: incident_inc_123_2024-01-01T12:00:00Z
event: incident_update
data: {"incident_id": "inc_123", "state": "ACK", "actor": "user@example.com", "timestamp": "2024-01-01T12:00:00Z"}

```

### Client Connection (HTMX)

```html
<div 
    hx-ext="sse" 
    sse-connect="/ops/stream/incidents"
    sse-swap="incident_update"
    hx-target="#incidents-table"
    hx-swap="outerHTML">
</div>
```

### Heartbeat

- Sent every 30 seconds
- Format: `: heartbeat\n\n`
- Keeps connection alive

## Performance

### Targets

- **Page Render**: p95 < 150ms (96 incidents dataset)
- **SSE Enqueue**: < 5ms per event
- **Form Submission**: < 100ms (with CSRF validation)

### Optimizations

- Template caching
- Minimal CSS (no framework overhead)
- Efficient incident filtering
- Stable sorting (deterministic)

## Determinism

### Banned Calls

The following are **not allowed** in ops_console module:
- `datetime.now()` → Use injected `Clock`
- `time.time()` → Use `Clock.utcnow()`
- `random.*` → Use deterministic algorithms
- `uuid.uuid4()` → Use predictable IDs in tests

### Testing with ManualClock

```python
from src.qnwis.utils.clock import ManualClock

clock = ManualClock(current="2024-01-01T12:00:00Z")
app = create_ops_app(clock=clock)

# Deterministic timestamp
timestamp = clock.utcnow()  # Always "2024-01-01T12:00:00Z"
```

## RBAC Matrix

| Action | analyst | admin | auditor | service |
|--------|---------|-------|---------|---------|
| View dashboard | ✓ | ✓ | ✓ | ✗ |
| View incidents | ✓ | ✓ | ✓ | ✗ |
| Acknowledge incident | ✓ | ✓ | ✗ | ✗ |
| Resolve incident | ✓ | ✓ | ✗ | ✗ |
| Silence incident | ✓ | ✓ | ✗ | ✗ |
| View alerts | ✓ | ✓ | ✓ | ✗ |
| SSE stream | ✓ | ✓ | ✓ | ✗ |

## Deployment

### Mounting on Main App

```python
from fastapi import FastAPI
from src.qnwis.ops_console.app import mount_ops_console
from src.qnwis.utils.clock import Clock

app = FastAPI()
clock = Clock()  # Or ManualClock for testing

mount_ops_console(
    parent_app=app,
    mount_path="/ops",
    clock=clock,
    secret_key="your-secret-key-here",
)
```

### Environment Variables

```bash
OPS_CONSOLE_SECRET_KEY=<64-char hex key>
OPS_CONSOLE_CSRF_TTL=900  # seconds
OPS_CONSOLE_SSE_HEARTBEAT=30  # seconds
```

### Grafana Dashboard

Import `grafana/dashboards/qnwis_ops.json` to monitor:
- Notification metrics
- Incident lifecycle
- Page render latency
- Cache hit rate
- CSRF failures

See `docs/ops/grafana_import.md` for detailed instructions.

## Testing

### Unit Tests

- `tests/unit/ops_console/test_csrf.py`: CSRF token generation, verification, TTL
- `tests/unit/ops_console/test_sse.py`: SSE event formatting, streaming, heartbeat
- `tests/unit/ops_console/test_templates.py`: Template rendering, a11y, determinism

### Integration Tests

- `tests/integration/ops_console/test_incident_pages.py`: Page rendering, filters, actions
- `tests/integration/ops_console/test_live_updates.py`: SSE integration, event delivery

### Performance Tests

- `tests/unit/ops_console/test_perf_render.py`: p95 render latency, SSE enqueue

### Run Tests

```bash
# All ops console tests
pytest tests/unit/ops_console/ tests/integration/ops_console/ -v

# With coverage
pytest tests/unit/ops_console/ tests/integration/ops_console/ --cov=src.qnwis.ops_console --cov-report=term

# Performance only
pytest tests/unit/ops_console/test_perf_render.py -v
```

## RG-5 Gate

Run the ops console readiness gate:

```bash
python src/qnwis/scripts/qa/ops_console_gate.py
```

Checks:
1. **UI Completeness**: Pages, templates, routes, a11y
2. **UI Performance**: p95 render < 150ms, SSE < 5ms
3. **UI Security**: CSRF, headers, no inline scripts
4. **UI Determinism**: No banned calls, stable sorting
5. **UI Audit**: Request IDs, actor logging, artifacts

Generates:
- `src/qnwis/docs/audit/ops/ui_gate_report.json`
- `src/qnwis/docs/audit/badges/rg5_ops_console.svg`
- `OPS_UI_SUMMARY.md`

## Troubleshooting

### CSRF Token Expired

**Issue**: "CSRF token invalid or expired"

**Solutions**:
1. Check system clock synchronization
2. Increase TTL: `CSRFProtection(ttl=1800)`
3. Verify secret key consistency across instances

### SSE Connection Drops

**Issue**: SSE stream disconnects frequently

**Solutions**:
1. Check proxy timeout settings (nginx, load balancer)
2. Reduce heartbeat interval: `SSEStream(heartbeat_interval=15)`
3. Enable SSE reconnection in HTMX

### Slow Page Rendering

**Issue**: p95 render exceeds 150ms

**Solutions**:
1. Reduce incident dataset size (pagination)
2. Optimize template complexity
3. Enable template caching
4. Check database query performance

### RBAC Denies Access

**Issue**: 403 Forbidden despite correct role

**Solutions**:
1. Verify principal middleware is configured
2. Check `rbac.yml` route configuration
3. Confirm role names match exactly (case-sensitive)

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Jinja2 Template Designer](https://jinja.palletsprojects.com/)
- [HTMX Documentation](https://htmx.org/)
- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
