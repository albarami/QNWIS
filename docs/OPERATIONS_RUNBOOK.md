# QNWIS Operations Runbook

**Version:** 1.0.0  
**Audience:** Operations team, SREs, on-call engineers  
**Last Updated:** 2025-01-12

## Overview

This runbook provides operational procedures for maintaining and troubleshooting the QNWIS production system. Follow these procedures during incidents, maintenance, and routine operations.

## System Architecture Overview

```
┌─────────────────┐
│   Load Balancer │ (Traefik/nginx)
└────────┬────────┘
         │
    ┌────┴────┐
    │ FastAPI │ (Multiple instances)
    │  App    │
    └────┬────┘
         │
    ┌────┴────────────────┐
    │                     │
┌───┴────┐         ┌─────┴─────┐
│ PostgreSQL│       │   Redis   │
│  (Primary)│       │  (Cache)  │
└──────────┘       └───────────┘
```

**Key Components:**
- **FastAPI Application**: Python 3.11, uvicorn workers
- **PostgreSQL 14+**: Primary data store (60+ LMIS tables)
- **Redis 6+**: Caching, rate limiting, session storage
- **Traefik/nginx**: Load balancing, TLS termination
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and alerting

## On-Call Responsibilities

### Primary Duties

1. **Incident Response**: Acknowledge alerts within 15 minutes
2. **System Monitoring**: Check dashboards every 4 hours
3. **Log Review**: Review error logs daily
4. **Backup Verification**: Confirm daily backups completed
5. **Performance Tracking**: Monitor SLO compliance

### Escalation Path

1. **L1 (On-call Engineer)**: Initial response, basic troubleshooting
2. **L2 (Senior SRE)**: Complex issues, system changes
3. **L3 (Development Team)**: Code bugs, architectural issues
4. **L4 (Management)**: Major outages, security incidents

### Contact Information

```
On-Call Rotation: PagerDuty schedule
L2 Escalation: +974-XXXX-XXXX
Security Team: security@mol.gov.qa
Development Lead: dev-lead@mol.gov.qa
```

## Service Locations

### Production Environment

```bash
# Application servers
app-01.qnwis.mol.gov.qa
app-02.qnwis.mol.gov.qa
app-03.qnwis.mol.gov.qa

# Database
db-primary.qnwis.mol.gov.qa:5432
db-replica.qnwis.mol.gov.qa:5432

# Redis
redis-01.qnwis.mol.gov.qa:6379
redis-02.qnwis.mol.gov.qa:6379 (replica)

# Load balancer
lb.qnwis.mol.gov.qa
```

### Log Locations

```bash
# Application logs
/var/log/qnwis/app.log
/var/log/qnwis/error.log
/var/log/qnwis/audit.log

# System logs
/var/log/syslog
/var/log/nginx/access.log
/var/log/nginx/error.log

# Centralized logging
https://logs.qnwis.mol.gov.qa (ELK/Loki)
```

### Configuration Files

```bash
# Application config
/etc/qnwis/config.yaml
/etc/qnwis/.env

# Systemd service
/etc/systemd/system/qnwis.service

# Nginx/Traefik
/etc/nginx/sites-available/qnwis.conf
/etc/traefik/traefik.yml
```

## Monitoring and Metrics

### Key Metrics to Watch

#### Application Metrics (`/metrics`)

```
# Query performance
qnwis_query_duration_seconds{type="simple"} p95 < 10s
qnwis_query_duration_seconds{type="medium"} p95 < 30s
qnwis_query_duration_seconds{type="complex"} p95 < 90s

# Throughput
qnwis_queries_total rate > 0
qnwis_queries_per_minute > 10

# Error rate
qnwis_errors_total / qnwis_queries_total < 0.01 (1%)

# Cache performance
qnwis_cache_hit_rate > 0.60 (60%)

# Database connections
qnwis_db_connections_active < 80% of pool size
qnwis_db_query_duration_seconds p95 < 1s
```

#### System Metrics

```
# CPU
node_cpu_usage < 80%

# Memory
node_memory_usage < 85%

# Disk
node_disk_usage < 80%
node_disk_io_wait < 10%

# Network
node_network_errors_total rate < 1/min
```

### Grafana Dashboards

**Main Dashboard**: https://grafana.qnwis.mol.gov.qa/d/qnwis-ops

Panels:
- Query volume and response times
- Error rates by endpoint
- Cache hit rates
- Database connection pool
- Agent performance breakdown
- SLO compliance tracking

### Accessing Metrics

```bash
# Prometheus metrics endpoint (requires ops role)
curl -H "Authorization: Bearer $TOKEN" https://api.qnwis.mol.gov.qa/metrics

# Health check (no auth required)
curl https://api.qnwis.mol.gov.qa/health

# Detailed health (requires auth)
curl -H "Authorization: Bearer $TOKEN" https://api.qnwis.mol.gov.qa/health/detailed
```

## SLOs and Alerts

### Service Level Objectives

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Availability | 99.5% | 30 days |
| Simple Query Response | < 10s (p95) | 24 hours |
| Medium Query Response | < 30s (p95) | 24 hours |
| Complex Query Response | < 90s (p95) | 24 hours |
| Dashboard Load Time | < 3s (p95) | 24 hours |
| Error Rate | < 1% | 24 hours |
| Cache Hit Rate | > 60% | 24 hours |

### Alert Definitions

**Critical Alerts** (Page immediately)

```yaml
# High error rate
- alert: HighErrorRate
  expr: rate(qnwis_errors_total[5m]) > 0.05
  for: 5m
  severity: critical
  action: Page on-call, investigate immediately

# Service down
- alert: ServiceDown
  expr: up{job="qnwis"} == 0
  for: 2m
  severity: critical
  action: Page on-call, check service status

# Database connection failure
- alert: DatabaseDown
  expr: qnwis_db_connections_active == 0
  for: 1m
  severity: critical
  action: Page on-call, check database
```

**Warning Alerts** (Slack/email)

```yaml
# SLO breach
- alert: QueryLatencyHigh
  expr: histogram_quantile(0.95, qnwis_query_duration_seconds) > 15
  for: 10m
  severity: warning
  action: Investigate performance, check slow queries

# Low cache hit rate
- alert: LowCacheHitRate
  expr: qnwis_cache_hit_rate < 0.50
  for: 15m
  severity: warning
  action: Check Redis, review cache configuration

# High memory usage
- alert: HighMemoryUsage
  expr: node_memory_usage > 0.85
  for: 10m
  severity: warning
  action: Check for memory leaks, consider scaling
```

## Common Operational Tasks

### Checking System Status

```bash
# Quick health check
curl https://api.qnwis.mol.gov.qa/health | jq

# Detailed status
ssh app-01.qnwis.mol.gov.qa
sudo systemctl status qnwis
sudo journalctl -u qnwis -n 100 --no-pager

# Check all services
for host in app-01 app-02 app-03; do
  echo "=== $host ==="
  ssh $host "systemctl is-active qnwis"
done
```

### Viewing Logs

```bash
# Real-time application logs
ssh app-01.qnwis.mol.gov.qa
sudo tail -f /var/log/qnwis/app.log | jq

# Error logs only
sudo tail -f /var/log/qnwis/error.log

# Search for specific query
sudo grep "query_id=q_2024_001234" /var/log/qnwis/app.log | jq

# Audit trail for user
sudo grep "user_id=analyst_123" /var/log/qnwis/audit.log | jq

# Last 1000 errors
sudo tail -n 1000 /var/log/qnwis/error.log | grep ERROR
```

### Database Operations

```bash
# Connect to primary database
psql -h db-primary.qnwis.mol.gov.qa -U qnwis -d qnwis_prod

# Check connection count
SELECT count(*) FROM pg_stat_activity WHERE datname = 'qnwis_prod';

# Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Check table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

# Check replication lag
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

### Redis Operations

```bash
# Connect to Redis
redis-cli -h redis-01.qnwis.mol.gov.qa

# Check memory usage
INFO memory

# Check cache hit rate
INFO stats | grep keyspace

# View cache keys
KEYS qnwis:cache:*

# Clear specific cache
DEL qnwis:cache:query:q_2024_001234

# Clear all cache (use with caution!)
FLUSHDB
```

### Restarting Services

```bash
# Restart single application server (zero-downtime)
ssh app-01.qnwis.mol.gov.qa
sudo systemctl restart qnwis
sudo systemctl status qnwis

# Rolling restart (all servers)
for host in app-01 app-02 app-03; do
  echo "Restarting $host..."
  ssh $host "sudo systemctl restart qnwis"
  sleep 30  # Wait for health check
  curl https://api.qnwis.mol.gov.qa/health || echo "WARNING: $host may be unhealthy"
done

# Restart Redis (with failover)
ssh redis-01.qnwis.mol.gov.qa
sudo systemctl restart redis
```

## Deployment Procedures

### Pre-Deployment Checklist

- [ ] Code reviewed and approved
- [ ] All tests passing in CI/CD
- [ ] Database migrations tested in staging
- [ ] Backup completed and verified
- [ ] Change window scheduled and communicated
- [ ] Rollback plan documented

### Blue-Green Deployment

```bash
# 1. Deploy to green environment
cd /opt/qnwis
git fetch origin
git checkout v1.0.1  # New version tag

# 2. Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Restart green servers
for host in app-green-01 app-green-02; do
  ssh $host "cd /opt/qnwis && sudo systemctl restart qnwis"
done

# 5. Smoke test green environment
curl https://green.qnwis.mol.gov.qa/health
curl https://green.qnwis.mol.gov.qa/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "test query"}'

# 6. Switch traffic to green
# Update load balancer configuration
sudo vim /etc/traefik/traefik.yml
# Change backend from blue to green
sudo systemctl reload traefik

# 7. Monitor for 15 minutes
watch -n 10 'curl -s https://api.qnwis.mol.gov.qa/health | jq'

# 8. If successful, update blue to new version
# If issues, rollback by switching traffic back to blue
```

### Tag-Based Rollback

```bash
# 1. Identify current version
git describe --tags

# 2. Checkout previous version
git checkout v1.0.0  # Previous stable version

# 3. Rollback database migrations (if needed)
alembic downgrade <previous_revision>

# 4. Restart services
sudo systemctl restart qnwis

# 5. Verify rollback
curl https://api.qnwis.mol.gov.qa/health
```

### Emergency Hotfix

```bash
# 1. Create hotfix branch
git checkout -b hotfix/critical-bug main

# 2. Apply minimal fix
# Edit files...

# 3. Test locally
pytest tests/ -v

# 4. Commit and tag
git commit -m "fix(critical): resolve production issue"
git tag v1.0.1-hotfix
git push origin v1.0.1-hotfix

# 5. Deploy immediately (skip staging if critical)
# Follow blue-green deployment process

# 6. Post-incident review within 24 hours
```

## Backup and Restore

### Backup Schedule

- **Database**: Daily at 02:00 UTC, retained 30 days
- **Redis**: Daily snapshot, retained 7 days
- **Configuration**: Version controlled in Git
- **Logs**: Retained 90 days in centralized logging

### Manual Database Backup

```bash
# Full backup
ssh db-primary.qnwis.mol.gov.qa
sudo -u postgres pg_dump qnwis_prod | gzip > /backups/qnwis_$(date +%Y%m%d_%H%M%S).sql.gz

# Copy to backup server
scp /backups/qnwis_*.sql.gz backup-server:/backups/qnwis/

# Verify backup
gunzip -c /backups/qnwis_*.sql.gz | head -n 100
```

### Database Restore

```bash
# 1. Stop application servers
for host in app-01 app-02 app-03; do
  ssh $host "sudo systemctl stop qnwis"
done

# 2. Create restore point
sudo -u postgres pg_dump qnwis_prod > /tmp/pre_restore_backup.sql

# 3. Restore from backup
gunzip -c /backups/qnwis_20250112_020000.sql.gz | sudo -u postgres psql qnwis_prod

# 4. Verify data
psql -U qnwis qnwis_prod -c "SELECT count(*) FROM qtr_employment_stats;"

# 5. Restart application
for host in app-01 app-02 app-03; do
  ssh $host "sudo systemctl start qnwis"
done

# 6. Smoke test
curl https://api.qnwis.mol.gov.qa/health
```

### Backup Verification Drill

**Monthly Procedure:**

```bash
# 1. Restore to test environment
ssh test-db.qnwis.mol.gov.qa
gunzip -c /backups/latest.sql.gz | psql qnwis_test

# 2. Run validation queries
psql qnwis_test <<EOF
SELECT count(*) FROM qtr_employment_stats;
SELECT max(created_at) FROM audit.query_log;
SELECT count(DISTINCT table_name) FROM information_schema.tables WHERE table_schema = 'public';
EOF

# 3. Document results
echo "Backup verification: $(date)" >> /var/log/backup_verification.log
```

## Incident Response

### Incident Severity Levels

**SEV-1 (Critical)**
- Complete service outage
- Data loss or corruption
- Security breach
- Response: Immediate page, all hands

**SEV-2 (High)**
- Partial service degradation
- SLO breach affecting multiple users
- Response: Page on-call, escalate if not resolved in 30 min

**SEV-3 (Medium)**
- Single component failure with redundancy
- Performance degradation
- Response: Slack alert, resolve within 4 hours

**SEV-4 (Low)**
- Minor issues, no user impact
- Response: Create ticket, resolve in next sprint

### Incident Response Workflow

```
1. ACKNOWLEDGE (< 15 min)
   ├─ Update status page
   ├─ Notify stakeholders
   └─ Begin investigation

2. DIAGNOSE (< 30 min)
   ├─ Check logs and metrics
   ├─ Identify root cause
   └─ Document findings

3. MITIGATE (< 1 hour)
   ├─ Apply temporary fix
   ├─ Restore service
   └─ Verify resolution

4. RESOLVE (< 4 hours)
   ├─ Apply permanent fix
   ├─ Deploy to production
   └─ Monitor for recurrence

5. POST-MORTEM (< 48 hours)
   ├─ Write incident report
   ├─ Identify action items
   └─ Update runbook
```

### Common Incident Scenarios

#### Scenario 1: High Error Rate

```bash
# 1. Check error logs
ssh app-01.qnwis.mol.gov.qa
sudo tail -n 500 /var/log/qnwis/error.log | grep ERROR

# 2. Identify error pattern
# Common causes: DB connection, Redis timeout, external API failure

# 3. Check dependencies
curl https://api.qnwis.mol.gov.qa/health/detailed

# 4. If database issue:
psql -h db-primary.qnwis.mol.gov.qa -U qnwis -c "SELECT count(*) FROM pg_stat_activity;"

# 5. If connection pool exhausted, restart app
sudo systemctl restart qnwis

# 6. Monitor recovery
watch -n 5 'curl -s https://api.qnwis.mol.gov.qa/metrics | grep error_rate'
```

#### Scenario 2: Slow Query Performance

```bash
# 1. Check current slow queries
psql qnwis_prod <<EOF
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC;
EOF

# 2. Kill long-running query if necessary
psql qnwis_prod -c "SELECT pg_terminate_backend(12345);"

# 3. Check for missing indexes
psql qnwis_prod -c "SELECT * FROM pg_stat_user_tables WHERE seq_scan > 1000 ORDER BY seq_scan DESC LIMIT 10;"

# 4. Analyze query plan
psql qnwis_prod -c "EXPLAIN ANALYZE <slow_query>;"

# 5. Add index if needed (coordinate with dev team)
```

#### Scenario 3: Memory Leak

```bash
# 1. Check memory usage
ssh app-01.qnwis.mol.gov.qa
free -h
ps aux | grep uvicorn | awk '{print $2, $4, $11}'

# 2. Identify leaking process
top -o %MEM

# 3. Restart affected worker
sudo systemctl restart qnwis

# 4. Monitor memory over time
watch -n 60 'free -h && ps aux | grep uvicorn | awk "{print \$2, \$4, \$11}"'

# 5. Escalate to dev team if recurring
```

## Maintenance Windows

### Scheduled Maintenance

**Timing**: Every 2nd Sunday, 02:00-04:00 UTC (low traffic period)

**Notification**: 48 hours advance notice via:
- Status page
- Email to stakeholders
- In-app banner

**Procedure:**

```bash
# 1. Enable maintenance mode
curl -X POST https://api.qnwis.mol.gov.qa/admin/maintenance \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"enabled": true, "message": "Scheduled maintenance in progress"}'

# 2. Perform maintenance tasks
# - Database vacuum and analyze
# - Index rebuilding
# - Log rotation
# - Security updates

# 3. Verify system health
pytest tests/system/ -v

# 4. Disable maintenance mode
curl -X POST https://api.qnwis.mol.gov.qa/admin/maintenance \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"enabled": false}'

# 5. Monitor for 30 minutes
```

### Emergency Maintenance

For critical security patches or urgent fixes:

1. **Notify immediately**: Status page + email
2. **Minimize downtime**: Use blue-green deployment if possible
3. **Document**: Record all actions taken
4. **Post-mortem**: Review within 24 hours

## Security Operations

### Security Monitoring

```bash
# Check failed authentication attempts
sudo grep "authentication failed" /var/log/qnwis/audit.log | tail -n 100

# Check rate limit violations
sudo grep "rate_limit_exceeded" /var/log/qnwis/app.log | tail -n 100

# Check suspicious query patterns
psql qnwis_prod -c "SELECT user_id, count(*) FROM audit.query_log WHERE created_at > now() - interval '1 hour' GROUP BY user_id HAVING count(*) > 100;"
```

### Security Incident Response

**If security breach suspected:**

1. **Isolate**: Disconnect affected systems
2. **Preserve**: Capture logs and memory dumps
3. **Notify**: Security team immediately
4. **Investigate**: Determine scope and impact
5. **Remediate**: Apply fixes and patches
6. **Report**: Document incident per compliance requirements

### Certificate Renewal

```bash
# Check certificate expiry
echo | openssl s_client -servername api.qnwis.mol.gov.qa -connect api.qnwis.mol.gov.qa:443 2>/dev/null | openssl x509 -noout -dates

# Renew Let's Encrypt certificate (automated)
sudo certbot renew --dry-run

# Manual renewal if needed
sudo certbot certonly --standalone -d api.qnwis.mol.gov.qa

# Reload web server
sudo systemctl reload nginx
```

## Performance Tuning

### Database Optimization

```sql
-- Vacuum and analyze
VACUUM ANALYZE;

-- Reindex heavily used tables
REINDEX TABLE qtr_employment_stats;

-- Update statistics
ANALYZE qtr_employment_stats;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### Cache Optimization

```bash
# Warm up cache after deployment
python scripts/warm_cache.py

# Monitor cache hit rate
redis-cli INFO stats | grep keyspace_hits

# Adjust TTL if needed
# Edit /etc/qnwis/config.yaml
# REDIS_CACHE_TTL=3600
```

### Application Tuning

```bash
# Adjust worker count (CPU cores * 2 + 1)
# Edit /etc/systemd/system/qnwis.service
# ExecStart=/opt/qnwis/venv/bin/uvicorn ... --workers 8

# Adjust database connection pool
# Edit /etc/qnwis/.env
# DATABASE_POOL_SIZE=20
# DATABASE_MAX_OVERFLOW=10
```

## Disaster Recovery

See [Step 36 DR Implementation](../STEP32_DR_IMPLEMENTATION_COMPLETE.md) for complete disaster recovery procedures.

**RTO (Recovery Time Objective)**: 4 hours  
**RPO (Recovery Point Objective)**: 1 hour

**Quick DR Activation:**

```bash
# 1. Promote replica to primary
ssh db-replica.qnwis.mol.gov.qa
sudo -u postgres /usr/lib/postgresql/14/bin/pg_ctl promote -D /var/lib/postgresql/14/main

# 2. Update application config
for host in app-01 app-02 app-03; do
  ssh $host "sudo sed -i 's/db-primary/db-replica/g' /etc/qnwis/.env"
  ssh $host "sudo systemctl restart qnwis"
done

# 3. Verify failover
curl https://api.qnwis.mol.gov.qa/health
```

## Contacts and Escalation

### On-Call Schedule
- **PagerDuty**: https://mol-qatar.pagerduty.com
- **Rotation**: Weekly, Monday 09:00 UTC

### Key Contacts
- **Operations Lead**: ops-lead@mol.gov.qa
- **Development Lead**: dev-lead@mol.gov.qa
- **Security Team**: security@mol.gov.qa
- **Database Admin**: dba@mol.gov.qa

### Escalation Matrix

| Severity | Initial Response | Escalation (30 min) | Escalation (1 hour) |
|----------|-----------------|---------------------|---------------------|
| SEV-1 | On-call engineer | Senior SRE + Dev Lead | CTO |
| SEV-2 | On-call engineer | Senior SRE | Dev Lead |
| SEV-3 | On-call engineer | Senior SRE (next day) | - |
| SEV-4 | Ticket | - | - |

---

**This runbook is a living document. Update after each incident or operational change.**

**Last Review**: 2025-01-12  
**Next Review**: 2025-02-12
