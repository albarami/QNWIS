# Step 29: Notifications & Incident Ops

Production-grade notification and incident management system with multi-channel dispatch, deduplication, and auto-resolution.

## Architecture

### Components

```
┌──────────────────────────────────────────────────────────┐
│                    Alert Center Agent                     │
│  (Evaluates rules → Emits Notifications)                 │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│              Notification Dispatcher                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 1. Deduplication (SHA256 idempotency key)         │  │
│  │ 2. Rate Limiting (per-rule counter)               │  │
│  │ 3. Suppression Windows                            │  │
│  │ 4. Multi-Channel Fan-Out                          │  │
│  │ 5. Audit Ledger Persistence                       │  │
│  └────────────────────────────────────────────────────┘  │
└──────┬──────────┬──────────┬─────────────────────────────┘
       │          │          │
       ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌─────────┐
  │ Email  │ │ Teams  │ │ Webhook │
  └────────┘ └────────┘ └─────────┘

┌──────────────────────────────────────────────────────────┐
│               Incident Resolver                           │
│  State Machine: OPEN → ACK → SILENCED → RESOLVED        │
│  Auto-Resolution: N consecutive green evaluations        │
└──────────────────────────────────────────────────────────┘
```

## Features

### Deterministic Deduplication
- **Idempotency Key**: `SHA256(rule_id + scope + window_start + window_end)`
- **Guarantees**: Same alert conditions produce same notification ID
- **Test Coverage**: `test_dispatcher.py::test_dispatch_deduplication`

### Rate Limiting
- **Per-Rule**: Configurable limit (default: 10 notifications / 60 minutes)
- **Sliding Window**: Uses injected `Clock.time()` for determinism
- **Test Coverage**: `test_dispatcher.py::test_dispatch_rate_limiting`

### Suppression Windows
- **Manual Suppression**: CLI/API can suppress rules for N minutes
- **Auto-Clear**: Suppression expires based on clock time
- **Test Coverage**: `test_dispatcher.py::test_dispatch_suppression`

### Multi-Channel Dispatch
- **Email**: SMTP with TLS, HTML + plain text
- **Teams**: Adaptive cards via incoming webhooks
- **Webhook**: Generic POST with HMAC-SHA256 signatures
- **Dry-Run Mode**: All channels support dry-run for testing

### Audit Trail
- **Ledger**: `docs/audit/incidents/incidents.jsonl` (append-only)
- **Envelopes**: Per-incident JSON with SHA256 signature
- **Integrity**: RG-4 gate verifies signature matching

### Auto-Resolution
- **Threshold**: Configurable consecutive green evaluations (default: 3)
- **State Update**: OPEN/ACK → RESOLVED
- **Metadata**: Marks auto-resolved incidents with `auto_resolved: true`

## API Endpoints

### Send Notification (Admin/Service Only)
```http
POST /api/v1/notify/send
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "rule_id": "rule_retention_low",
  "severity": "warning",
  "message": "Retention below threshold",
  "scope": {"level": "sector", "code": "010"},
  "window_start": "2024-01-01T00:00:00Z",
  "window_end": "2024-01-01T23:59:59Z",
  "channels": ["email", "teams"],
  "evidence": {"retention_rate": 0.65, "threshold": 0.70}
}
```

### List Incidents
```http
GET /api/v1/incidents?state=open&rule_id=rule_retention_low&limit=20
Authorization: Bearer <jwt>
```

### Acknowledge Incident
```http
POST /api/v1/incidents/{incident_id}/ack
Authorization: Bearer <jwt>
```

### Resolve Incident
```http
POST /api/v1/incidents/{incident_id}/resolve
Authorization: Bearer <jwt>
```

### Silence Incident (Admin Only)
```http
POST /api/v1/incidents/{incident_id}/silence
Authorization: Bearer <jwt>
```

## CLI Commands

### Send Manual Notification
```bash
python -m src.qnwis.cli.qnwis_notify send \
  --rule-id rule_test \
  --severity warning \
  --message "Manual test alert" \
  --scope '{"level":"national","code":""}' \
  --channel email \
  --dry-run
```

### Silence Rule
```bash
python -m src.qnwis.cli.qnwis_notify silence \
  --rule-id rule_retention_low \
  --duration 60  # minutes
```

### Acknowledge Incident
```bash
python -m src.qnwis.cli.qnwis_notify ack <incident_id>
```

### Resolve Incident
```bash
python -m src.qnwis.cli.qnwis_notify resolve <incident_id>
```

### View Incident Status
```bash
python -m src.qnwis.cli.qnwis_notify status \
  --state open \
  --rule-id rule_retention_low \
  --limit 20 \
  --format table
```

### Replay Notifications from Ledger
```bash
python -m src.qnwis.cli.qnwis_notify replay \
  --since 2024-01-01T00:00:00Z \
  --rule-id rule_retention_low \
  --dry-run
```

## Configuration

### Environment Variables

```bash
# Email (SMTP)
QNWIS_SMTP_HOST=smtp.example.com
QNWIS_SMTP_PORT=587
QNWIS_SMTP_USER=alerts@example.com
QNWIS_SMTP_PASS=<password>
QNWIS_SMTP_FROM=qnwis@example.com
QNWIS_SMTP_TO=ops-team@example.com
QNWIS_SMTP_USE_TLS=true

# Teams
QNWIS_TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...

# Webhook
QNWIS_WEBHOOK_URL=https://api.example.com/alerts
QNWIS_WEBHOOK_SECRET=<hmac_secret>
```

## RG-4 Gate Checks

Run the full RG-4 gate:
```bash
python -m src.qnwis.scripts.qa.ops_notify_gate
```

### Checks
1. **Completeness**: All modules load, channels wired
2. **Accuracy**: Golden fixtures produce expected notifications
3. **Performance**: p95 dispatch < 50ms (100 notifications, dry-run)
4. **Audit**: Ledger + HMAC integrity verified
5. **Determinism**: No `datetime.now()`, `time.time()`, `random.*`
   - Incidents package is additionally scanned to block `smtplib`, `socket`, `requests`, or `httpx` imports (pure deterministic core).

### RG-4 Artifacts
- `docs/audit/ops/RG4_SUMMARY.json` (p50, p95, p99, sample size)
- `OPS_NOTIFY_SUMMARY.md` (full gate narrative)
- `src/qnwis/docs/audit/badges/rg4_notify.svg` (badge for dashboards)

## Runbooks

### Incident Response

1. **New Alert Fires**
   - Notification sent to configured channels
   - Incident created in OPEN state
   - Analyst receives email/Teams notification

2. **Acknowledge Incident**
   ```bash
   python -m src.qnwis.cli.qnwis_notify ack <incident_id>
   ```
   - State: OPEN → ACK
   - Timestamp recorded

3. **Investigate & Fix**
   - Review evidence in incident metadata
   - Apply corrective action

4. **Monitor Auto-Resolution**
   - System records green evaluations
   - After 3 consecutive greens: auto-resolves
   - Or manually resolve:
     ```bash
     python -m src.qnwis.cli.qnwis_notify resolve <incident_id>
     ```

5. **Silence Noisy Alerts (Admin)**
   ```bash
   python -m src.qnwis.cli.qnwis_notify silence --rule-id <rule> --duration 120
   ```

## Testing

### Unit Tests
```bash
pytest tests/unit/notify/ -v --cov=src/qnwis/notify --cov-report=term-missing
```

### Integration Tests
```bash
pytest tests/integration/notify/ -v
```

### Performance Benchmark
```bash
python -m src.qnwis.scripts.qa.ops_notify_gate
# Check p95 latency < 50ms
```

## Monitoring

### Key Metrics
- `qnwis_notifications_dispatched_total{channel="email|teams|webhook",status="success|error"}`
- `qnwis_notifications_deduplicated_total`
- `qnwis_notifications_rate_limited_total`
- `qnwis_notifications_suppressed_total`
- `qnwis_incidents_total{state="open|ack|silenced|resolved"}`
- `qnwis_incidents_auto_resolved_total`

### Alerts to Watch
- High deduplication rate → May indicate alert fatigue
- High rate-limit hits → May need to adjust thresholds
- Incidents not being acknowledged → Follow-up needed

## Security

### RBAC Requirements
- **Send Notification**: `admin` or `service` role
- **Acknowledge/Resolve**: `admin` or `analyst` role
- **Silence**: `admin` role only
- **List/View**: `admin`, `analyst`, or `service` role

### Audit
- All notification dispatches logged to JSONL ledger
- Each incident has HMAC envelope for integrity verification
- API operations logged with principal subject
