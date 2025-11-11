# Business Continuity Examples

This directory contains example configurations for the QNWIS Business Continuity & Failover Orchestration system.

## Files

- **cluster.yaml**: Example cluster topology with 3 nodes across 2 regions
- **policy.yaml**: Example automatic failover policy

## Quick Start

### 1. Generate Failover Plan

```bash
python -m qnwis.cli.qnwis_continuity plan \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --output failover-plan.json
```

### 2. Simulate Failover

```bash
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --scenario primary_failure \
  --seed 42
```

### 3. Check Cluster Status

```bash
python -m qnwis.cli.qnwis_continuity status \
  --cluster examples/continuity/cluster.yaml
```

## Customization

### Modify Cluster Topology

Edit `cluster.yaml` to:
- Add/remove nodes
- Change regions and sites
- Adjust node priorities
- Update capacity values

### Modify Failover Policy

Edit `policy.yaml` to:
- Change failover strategy (automatic/manual/quorum_based)
- Adjust timing constraints
- Reorder region/site priorities
- Set minimum healthy nodes

## Scenarios

### Scenario 1: Primary Node Failure

Simulates the primary node failing and automatic failover to the highest-priority secondary node.

```bash
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --scenario primary_failure
```

**Expected Result**:
- Primary (node-1) marked as failed
- Failover to node-2 (highest priority secondary in region-1)
- Quorum maintained (2/3 nodes healthy)
- Verification passes

### Scenario 2: Random Node Failures

Simulates random node failures to test resilience.

```bash
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --scenario random_failures \
  --seed 42
```

**Expected Result**:
- Random secondary node(s) fail
- Primary remains operational
- Quorum status checked
- Verification passes if quorum maintained

### Scenario 3: Region Failure

Simulates an entire region failing (e.g., datacenter outage).

```bash
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --scenario region_failure
```

**Expected Result**:
- All nodes in specified region fail
- Failover to secondary region
- Cross-region quorum checked
- Verification passes if sufficient nodes in other regions

## Testing

### Dry-Run Execution

Always test with dry-run before actual execution:

```bash
# Generate plan
python -m qnwis.cli.qnwis_continuity plan \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --output plan.json

# Execute in dry-run mode
python -m qnwis.cli.qnwis_continuity execute \
  --plan plan.json \
  --dry-run
```

### Determinism Testing

Verify deterministic behavior by running with same seed:

```bash
# Run 1
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --scenario primary_failure \
  --seed 42 \
  --output sim1.json

# Run 2
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster examples/continuity/cluster.yaml \
  --policy examples/continuity/policy.yaml \
  --scenario primary_failure \
  --seed 42 \
  --output sim2.json

# Compare (should be identical)
diff sim1.json sim2.json
```

## Production Deployment

### Step 1: Customize Configuration

1. Copy example files:
   ```bash
   cp examples/continuity/cluster.yaml config/prod-cluster.yaml
   cp examples/continuity/policy.yaml config/prod-policy.yaml
   ```

2. Update with production values:
   - Real IP addresses/hostnames
   - Actual region/site identifiers
   - Production priorities
   - Appropriate timing constraints

### Step 2: Validate Configuration

```bash
# Test plan generation
python -m qnwis.cli.qnwis_continuity plan \
  --cluster config/prod-cluster.yaml \
  --policy config/prod-policy.yaml \
  --output /tmp/test-plan.json

# Run simulation
python -m qnwis.cli.qnwis_continuity simulate \
  --cluster config/prod-cluster.yaml \
  --policy config/prod-policy.yaml \
  --scenario primary_failure
```

### Step 3: Deploy to Staging

1. Deploy configuration to staging environment
2. Run RG-8 gate validation
3. Execute dry-run failover tests
4. Verify monitoring/alerting

### Step 4: Deploy to Production

1. Deploy configuration to production
2. Configure monitoring dashboards
3. Set up alerting rules
4. Train operators on runbooks
5. Schedule failover drills

## Monitoring

### Prometheus Metrics

After deployment, monitor these metrics:

```promql
# Healthy nodes
qnwis_continuity_nodes_healthy

# Quorum status
qnwis_continuity_quorum_reached

# Failover executions
rate(qnwis_failover_executions_total[5m])

# Failover success rate
rate(qnwis_failover_success_total[5m]) / rate(qnwis_failover_executions_total[5m])

# Failover latency p95
histogram_quantile(0.95, rate(qnwis_failover_execution_ms_bucket[5m]))
```

### Grafana Dashboard

Import the continuity dashboard:

```bash
# Dashboard JSON available at:
grafana/dashboards/continuity_ops.json
```

## Troubleshooting

### Issue: "No suitable failover target found"

**Cause**: All secondary nodes are unhealthy or don't meet policy criteria.

**Solution**:
1. Check node status in cluster.yaml
2. Verify at least one secondary is healthy
3. Review policy region/site priorities
4. Check node capacity values

### Issue: "Quorum not achieved"

**Cause**: Too many nodes are unhealthy to maintain quorum.

**Solution**:
1. Check how many nodes are healthy
2. Verify quorum_size is correct (should be N/2 + 1)
3. Restore failed nodes
4. Consider adjusting quorum_size (carefully!)

### Issue: Simulation fails

**Cause**: Configuration error or policy violation.

**Solution**:
1. Review simulation output for specific error
2. Validate YAML syntax
3. Check that cluster has at least one primary node
4. Verify policy constraints are achievable

## Additional Resources

- **Documentation**: `docs/ops/step33_continuity_failover.md`
- **Implementation Summary**: `STEP33_CONTINUITY_IMPLEMENTATION_COMPLETE.md`
- **RG-8 Gate Guide**: `RUN_RG8_GATE.md`
- **API Specification**: See API docs for `/api/v1/continuity/*` endpoints

## Support

For issues or questions:
1. Review documentation
2. Run RG-8 gate: `python src/qnwis/scripts/qa/rg8_continuity_gate.py`
3. Check test suite: `pytest tests/unit/continuity/ tests/integration/continuity/ -v`
4. Review audit logs: `python -m qnwis.cli.qnwis_continuity audit`
