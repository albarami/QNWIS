# Step 33: Business Continuity & Failover Orchestration

## Overview

The Business Continuity & Failover Orchestration system provides deterministic, production-grade high-availability capabilities for QNWIS deployments. It enables automatic and manual failover between cluster nodes while maintaining data consistency, quorum requirements, and policy adherence.

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Continuity System                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐     ┌─────────────┐│
│  │   Cluster    │◄────►│  Heartbeat   │────►│   Quorum    ││
│  │   Manager    │      │   Monitor    │     │   Engine    ││
│  └──────┬───────┘      └──────────────┘     └─────────────┘│
│         │                                                     │
│         │                                                     │
│  ┌──────▼──────────────────────────────────────────────────┐│
│  │              Failover Orchestrator                       ││
│  │  • Policy Engine  • Leader Election  • Health Checks    ││
│  └──────┬──────────────────────────────────────────────────┘│
│         │                                                     │
│  ┌──────▼───────────────────────────────────────────────┐  │
│  │           Integration Layer                           │  │
│  │  • DR/Backup (Step 32)  • Alerts (Step 29)           │  │
│  │  • SLO/SLI (Step 31)     • Ops Console (Step 30)     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **Heartbeat Monitor** (`heartbeat.py`)
   - Deterministic heartbeat simulation
   - Quorum detection (N/2 + 1 formula)
   - Node health tracking
   - Configurable intervals (default: 5s)
   - Failure threshold tracking (consecutive misses)

2. **Continuity Planner** (`planner.py`)
   - Generates failover plans from topology + policy
   - Selects optimal failover targets based on priority
   - Estimates execution time (planning + execution)
   - Region/site affinity enforcement

3. **Failover Executor** (`executor.py`)
   - Executes failover actions deterministically
   - Simulates DNS flips, service promotion/demotion
   - Audit logging with L19-L22 compliance
   - Dry-run mode for validation

4. **Failover Verifier** (`verifier.py`)
   - Post-failover validation
   - Consistency, policy, quorum, freshness checks
   - Verification reporting with confidence scoring
   - Integration with observability metrics

5. **Failover Simulator** (`simulate.py`)
   - What-if scenario testing
   - Seeded random fault injection
   - Deterministic simulation for repeatability
   - Chaos engineering scenarios

6. **Continuity Auditor** (`audit.py`)
   - L19-L22 audit trail generation
   - SHA-256 manifest verification
   - Confidence scoring (0-100)
   - Immutable audit log

## Heartbeat Logic & Quorum Model

### Heartbeat Protocol

The heartbeat monitor tracks node liveness using periodic health checks with configurable intervals and thresholds:

```python
# Heartbeat configuration
heartbeat_config = {
    "interval_sec": 5,           # Check every 5 seconds
    "timeout_sec": 2,            # 2-second timeout per check
    "failure_threshold": 3,      # Mark unhealthy after 3 consecutive failures
    "recovery_threshold": 2,     # Mark healthy after 2 consecutive successes
    "jitter_percent": 10         # Randomize interval ±10% to prevent thundering herd
}
```

### Health Check Sequence

1. **Liveness Check** (HTTP GET `/health/live`)
   - Basic process health
   - Expected response: < 100ms

2. **Readiness Check** (HTTP GET `/health/ready`)
   - Can serve traffic
   - Database connectivity verified
   - Expected response: < 200ms

3. **Deep Health Check** (HTTP GET `/health/deep`)
   - Full system validation
   - DR backup accessibility
   - SLO budget status
   - Expected response: < 500ms

### Failure Detection Flow

```
Time: 0s          5s          10s         15s
      |-----------|-----------|-----------|
Node  OK          MISS        MISS        MISS → FAILED

Actions:
- 0s:  Heartbeat sent, response OK
- 5s:  Heartbeat sent, no response (failure count = 1)
- 10s: Heartbeat sent, no response (failure count = 2)
- 15s: Heartbeat sent, no response (failure count = 3) → Mark as FAILED
- 15s: Trigger failover evaluation
```

### Quorum Calculation

QNWIS uses a **majority quorum** model to prevent split-brain scenarios:

```
Quorum = floor(N / 2) + 1

Examples:
- 3 nodes → quorum = 2 (can tolerate 1 failure)
- 5 nodes → quorum = 3 (can tolerate 2 failures)
- 7 nodes → quorum = 4 (can tolerate 3 failures)
```

### Cluster State Machine

```
           ┌─────────────┐
           │   HEALTHY   │
           │ (Has Quorum)│
           └──────┬──────┘
                  │
         Node     │     Recovery
       Failures   │
                  ▼
           ┌─────────────┐
           │  DEGRADED   │◄──────┐
           │ (Has Quorum)│       │
           └──────┬──────┘       │
                  │               │
       More       │        Nodes  │
       Failures   │        Recover│
                  ▼               │
           ┌─────────────┐       │
           │  CRITICAL   │       │
           │(No Quorum)  │       │
           │ READ-ONLY   │───────┘
           └─────────────┘
```

### Metrics Tracked

- `continuity_heartbeat_latency_ms`: P50, P95, P99 latency per node
- `continuity_node_status`: Up/down status per node (gauge: 0 or 1)
- `continuity_consecutive_failures`: Failure streak counter per node
- `continuity_health_check_errors`: Error count by type (timeout, connection_refused, etc.)
- `continuity_cluster_quorum`: Current quorum ratio (gauge: 0.0-1.0)

## Cluster Topology Configuration

### Supported Deployment Models

#### 1. Active/Passive (2-Region)
**Recommended for**: Production workloads requiring strong consistency

```
Region us-east-1 (Active)          Region us-west-2 (Passive)
┌─────────────────────┐           ┌─────────────────────┐
│  node-1 (Primary)   │           │  node-3 (Secondary) │
│  Priority: 100      │───sync───►│  Priority: 80       │
└─────────────────────┘           └─────────────────────┘
          │                                   │
          │                                   │
┌─────────────────────┐           ┌─────────────────────┐
│  node-2 (Secondary) │           │  node-4 (Secondary) │
│  Priority: 90       │───sync───►│  Priority: 70       │
└─────────────────────┘           └─────────────────────┘

All traffic → us-east-1
On failure → Promote node-3 in us-west-2
RPO: 5s | RTO: 3s (inherited from DR)
```

#### 2. Active/Active (Multi-Region)
**Recommended for**: Global deployments requiring low latency

```
Region us-east-1 (Active)          Region eu-central-1 (Active)
┌─────────────────────┐           ┌─────────────────────┐
│  node-1 (Primary)   │◄─repl────►│  node-3 (Primary)   │
│  Weight: 50%        │           │  Weight: 50%        │
└─────────────────────┘           └─────────────────────┘

Traffic distribution: Geo-routing based on client location
Conflict resolution: Last-write-wins with vector clocks
```

### cluster.yaml

```yaml
cluster_id: prod-cluster
name: Production Cluster
quorum_size: 2  # Optional, defaults to N/2 + 1
regions:
  - region-1
  - region-2
nodes:
  - node_id: node-1
    hostname: 10.0.1.10
    role: primary
    region: region-1
    site: site-a
    status: healthy
    priority: 100
    capacity: 100.0
  
  - node_id: node-2
    hostname: 10.0.1.11
    role: secondary
    region: region-1
    site: site-b
    status: healthy
    priority: 90
    capacity: 95.0
  
  - node_id: node-3
    hostname: 10.0.2.10
    role: secondary
    region: region-2
    site: site-c
    status: healthy
    priority: 80
    capacity: 90.0
```

### Node Roles

- **primary**: Active node serving requests
- **secondary**: Standby node ready for failover
- **witness**: Quorum participant (no data)

### Node Status

- **healthy**: Operational and available
- **degraded**: Operational with reduced capacity
- **failed**: Not operational
- **unknown**: Status not determined

## Failover Policies

### policy.yaml

```yaml
policy_id: auto-failover-policy
name: Automatic Failover Policy
strategy: automatic  # automatic | manual | quorum_based
max_failover_time_s: 60
require_quorum: true
region_priority:
  - region-1
  - region-2
site_priority:
  - site-a
  - site-b
  - site-c
min_healthy_nodes: 2
```

### Failover Strategies

1. **automatic**: Immediate failover on primary failure
2. **manual**: Requires operator approval
3. **quorum_based**: Failover only if quorum maintained

### Target Selection

Failover targets are selected based on:

1. Node must be healthy
2. Node must be secondary (not witness)
3. Prefer regions in `region_priority`
4. Prefer sites in `site_priority`
5. Prefer higher priority nodes
6. Prefer higher capacity nodes

## CLI Usage

### Generate Plan

```bash
python -m qnwis.cli.qnwis_continuity plan \
  --cluster cluster.yaml \
  --policy policy.yaml \
  --output plan.json
```

### Simulate Failover

```bash
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster cluster.yaml \
  --policy policy.yaml \
  --scenario primary_failure \
  --seed 42 \
  --output simulation.json
```

### Execute Plan

```bash
# Dry-run (recommended first)
python -m qnwis.cli.qnwis_continuity execute \
  --plan plan.json \
  --dry-run

# Actual execution
python -m qnwis.cli.qnwis_continuity execute \
  --plan plan.json
```

### Check Status

```bash
python -m qnwis.cli.qnwis_continuity status \
  --cluster cluster.yaml
```

### View Audit

```bash
python -m qnwis.cli.qnwis_continuity audit \
  --audit-id <audit-id>
```

## API Endpoints

All endpoints require `admin` or `service` role.

### POST /api/v1/continuity/plan

Generate continuity plan.

**Request:**
```json
{
  "cluster": { ... },
  "policy": { ... },
  "trigger_reason": "manual"
}
```

**Response:**
```json
{
  "request_id": "...",
  "plan_id": "...",
  "cluster_id": "...",
  "policy_id": "...",
  "primary_node_id": "node-1",
  "failover_target_id": "node-2",
  "estimated_total_ms": 40000,
  "action_count": 5,
  "timings_ms": { "total": 15, "planning": 15 }
}
```

### POST /api/v1/continuity/execute

Execute failover plan.

**Request:**
```json
{
  "plan": { ... },
  "dry_run": false
}
```

**Response:**
```json
{
  "request_id": "...",
  "execution_id": "...",
  "plan_id": "...",
  "success": true,
  "actions_executed": 5,
  "actions_failed": 0,
  "total_duration_ms": 38500,
  "audit_id": "...",
  "confidence": {
    "score": 95,
    "band": "very_high"
  },
  "timings_ms": { "total": 38520, "execution": 38500 }
}
```

### POST /api/v1/continuity/status

Get cluster status.

**Request:**
```json
{
  "cluster": { ... }
}
```

**Response:**
```json
{
  "request_id": "...",
  "cluster_id": "...",
  "total_nodes": 3,
  "healthy_nodes": 3,
  "quorum_size": 2,
  "has_quorum": true,
  "primary_node_id": "node-1",
  "timings_ms": { "total": 5 }
}
```

### POST /api/v1/continuity/simulate

Run failover simulation.

**Request:**
```json
{
  "cluster": { ... },
  "policy": { ... },
  "scenario": "primary_failure",
  "seed": 42
}
```

**Response:**
```json
{
  "request_id": "...",
  "scenario": "primary_failure",
  "success": true,
  "failover": {
    "execution_id": "...",
    "success": true,
    "actions_executed": 5,
    "total_duration_ms": 38
  },
  "verification": {
    "report_id": "...",
    "passed": true,
    "consistency_ok": true,
    "policy_ok": true,
    "quorum_ok": true
  },
  "timings_ms": { "total": 45, "simulation": 38 }
}
```

## Observability

### Prometheus Metrics

**Counters:**
- `qnwis_failover_executions_total{cluster, status}`
- `qnwis_failover_success_total{cluster}`
- `qnwis_failover_failures_total{cluster, reason}`

**Gauges:**
- `qnwis_continuity_nodes_healthy`
- `qnwis_continuity_quorum_reached`

**Histograms:**
- `qnwis_failover_execution_ms{cluster, status}`
- `qnwis_failover_validation_ms{cluster}`

### Grafana Dashboard

Import `grafana/dashboards/continuity_ops.json` for:
- Cluster health overview
- Quorum status
- Failover history
- Execution latency (p50, p95, p99)
- Success/failure rates

## Runbooks

### Primary Node Failure

1. **Detection**: Monitor alerts for primary node health
2. **Assessment**: Check quorum status
3. **Simulation**: Run simulation to validate failover
4. **Execution**: Execute failover plan
5. **Verification**: Verify post-failover state
6. **Audit**: Review audit pack

### Planned Maintenance

1. **Preparation**: Generate failover plan
2. **Notification**: Alert operators
3. **Simulation**: Test failover in dry-run mode
4. **Execution**: Execute during maintenance window
5. **Rollback**: Keep rollback plan ready
6. **Verification**: Validate service continuity

### Region Failure

1. **Detection**: Multiple node failures in region
2. **Assessment**: Check cross-region quorum
3. **Failover**: Execute to secondary region
4. **DNS Update**: Update DNS to new region
5. **Verification**: Verify cross-region connectivity
6. **Recovery**: Plan primary region recovery

## Performance Targets

- **Planning**: < 50ms
- **Execution**: < 60s (policy configurable)
- **Verification**: < 40ms
- **Simulation p95**: < 100ms

## Security

### Access Control & RBAC

Continuity operations require elevated privileges following the principle of least privilege:

```yaml
# RBAC policy (config/rbac/continuity.yaml)
rbac:
  roles:
    - name: continuity_viewer
      permissions:
        - continuity:read_status
        - continuity:view_audit
        - continuity:list_plans
      description: "Read-only access to continuity system"

    - name: continuity_operator
      permissions:
        - continuity:read_status
        - continuity:generate_plan
        - continuity:simulate
        - continuity:trigger_manual_failover
        - continuity:view_audit
      description: "Execute manual failovers and simulations"

    - name: continuity_admin
      permissions:
        - continuity:*
        - continuity:configure_policy
        - continuity:override_constraints
        - continuity:manage_cluster
        - continuity:emergency_override
      description: "Full control over continuity system"

  approval_workflows:
    manual_failover:
      required_approvers: 1
      allowed_roles:
        - continuity_admin
        - sre_oncall
      timeout_sec: 600  # 10-minute approval window

    emergency_override:
      required_approvers: 2
      allowed_roles:
        - continuity_admin
      timeout_sec: 300  # 5-minute approval window
```

### Allowlist & Network Security

Cluster nodes must be pre-registered and validated:

```yaml
# config/continuity/allowlist.yaml
allowed_nodes:
  - node_id: node-1
    endpoint: https://qnwis-1a.prod.example.com:8443
    fingerprint: sha256:abcd1234567890ef...
    region: us-east-1
    certificate_dn: "CN=node-1.qnwis.prod,O=QNWIS,C=US"

  - node_id: node-2
    endpoint: https://qnwis-2a.prod.example.com:8443
    fingerprint: sha256:efgh5678901234ab...
    region: us-west-2
    certificate_dn: "CN=node-2.qnwis.prod,O=QNWIS,C=US"

security_settings:
  require_tls: true
  min_tls_version: "1.3"
  validate_certificates: true
  mutual_auth: true
  cipher_suites:
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256
  certificate_pinning: true
```

### Threat Model & Mitigation

| Threat | Risk | Mitigation |
|--------|------|------------|
| **Node Spoofing** | High | TLS certificates + SHA-256 fingerprint validation |
| **Man-in-the-Middle** | High | Mutual TLS authentication + certificate pinning |
| **Unauthorized Failover** | Critical | RBAC + approval workflow + audit trail |
| **Split-Brain Attack** | Critical | Quorum enforcement + network partition detection |
| **Replay Attacks** | Medium | Timestamped requests + nonce validation |
| **Data Tampering** | High | SHA-256 manifest verification + immutable audit log |
| **Denial of Service** | Medium | Rate limiting + cooldown periods + max_failovers_per_hour |
| **Insider Threat** | Medium | Separation of duties + approval workflow + audit logging |

### Encryption Inheritance from DR (Step 32)

Continuity leverages the encryption mechanisms from the DR/Backup system:

- **In-Transit Encryption**: TLS 1.3 for all cluster communication (heartbeats, failover coordination)
- **At-Rest Encryption**: Inherit DR backup encryption (AES-256-GCM with unique keys per backup)
- **Key Management**: Same KMS integration as DR system (AWS KMS, HashiCorp Vault, or Azure Key Vault)
- **Key Rotation**: Automated 90-day rotation aligned with DR policies

### Audit Trail & Compliance

All continuity operations generate immutable audit logs:

```json
{
  "audit_id": "audit-cont-20250111-123456",
  "timestamp": "2025-01-11T12:34:56Z",
  "operation": "failover_execute",
  "cluster_id": "prod-cluster",
  "initiated_by": "john.doe@example.com",
  "role": "continuity_operator",
  "source_node": "node-1",
  "target_node": "node-3",
  "reason": "Primary node health degradation",
  "approval": {
    "required": true,
    "approved_by": "jane.admin@example.com",
    "approved_at": "2025-01-11T12:33:45Z"
  },
  "result": {
    "success": true,
    "duration_ms": 3450,
    "actions_executed": 5
  },
  "manifest_hash": "sha256:98765fedcba43210...",
  "signature": "..."
}
```

### Security Best Practices

1. **Principle of Least Privilege**: Assign minimal required permissions
2. **Separation of Duties**: Operators cannot approve their own failovers
3. **Defense in Depth**: Multiple security layers (TLS, RBAC, allowlist, audit)
4. **Zero Trust**: Verify every node on every heartbeat
5. **Immutable Audit**: No modification or deletion of audit logs
6. **Regular Reviews**: Quarterly access audits and policy reviews
7. **Incident Response**: Automated alerts on suspicious activities

## Testing

### Unit Tests

```bash
pytest tests/unit/continuity/ -v
```

### Integration Tests

```bash
pytest tests/integration/continuity/ -v
```

### RG-8 Gate

```bash
python src/qnwis/scripts/qa/rg8_continuity_gate.py
```

## Troubleshooting

### Quorum Not Achieved

**Symptom**: `has_quorum: false`

**Causes**:
- Too many failed nodes
- Network partitions
- Incorrect quorum_size configuration

**Resolution**:
1. Check node health status
2. Verify network connectivity
3. Review quorum_size (should be N/2 + 1)
4. Restart failed nodes

### Failover Target Not Found

**Symptom**: "No suitable failover target found"

**Causes**:
- All secondary nodes failed
- No nodes match policy criteria
- Insufficient capacity

**Resolution**:
1. Check secondary node status
2. Review policy region/site priorities
3. Verify node capacity
4. Consider relaxing policy constraints

### Verification Failed

**Symptom**: `verification.passed: false`

**Causes**:
- Consistency check failed
- Policy violation
- Quorum lost during failover
- Data freshness issue

**Resolution**:
1. Review verification errors
2. Check cluster state
3. Verify policy compliance
4. Re-run verification after stabilization

## References

- [RG-8 Continuity Gate](../audit/rg8/CONTINUITY_SUMMARY.md)
- [API Specification](../api/step27_service_api.md)
- [Observability Metrics](../PERFORMANCE.md)
