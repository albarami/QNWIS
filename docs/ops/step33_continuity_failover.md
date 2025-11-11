# Step 33: Business Continuity & Failover Orchestration

## Overview

The Business Continuity & Failover Orchestration system provides deterministic, production-grade high-availability capabilities for QNWIS deployments. It enables automatic and manual failover between cluster nodes while maintaining data consistency, quorum requirements, and policy adherence.

## Architecture

### Components

1. **Heartbeat Monitor** (`heartbeat.py`)
   - Deterministic heartbeat simulation
   - Quorum detection (N/2 + 1 formula)
   - Node health tracking

2. **Continuity Planner** (`planner.py`)
   - Generates failover plans from topology + policy
   - Selects optimal failover targets
   - Estimates execution time

3. **Failover Executor** (`executor.py`)
   - Executes failover actions deterministically
   - Simulates DNS flips, service promotion/demotion
   - Audit logging

4. **Failover Verifier** (`verifier.py`)
   - Post-failover validation
   - Consistency, policy, quorum, freshness checks
   - Verification reporting

5. **Failover Simulator** (`simulate.py`)
   - What-if scenario testing
   - Seeded random fault injection
   - Deterministic simulation

6. **Continuity Auditor** (`audit.py`)
   - L19-L22 audit trail generation
   - SHA-256 manifest verification
   - Confidence scoring

## Cluster Topology Configuration

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

- All API endpoints require RBAC (admin/service roles)
- Audit trails for all failover operations
- SHA-256 manifest verification
- No hardcoded credentials
- Encrypted communication between nodes (production)

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

- [RG-8 Continuity Gate](../../audit/rg8/CONTINUITY_SUMMARY.md)
- [API Specification](../api/step27_service_api.md)
- [Observability](../observability/metrics.md)
