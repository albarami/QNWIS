# QNWIS Troubleshooting Guide

**Version:** 1.0.0  
**Last Updated:** 2025-01-12

## Overview

This guide provides solutions to common QNWIS issues. Use decision trees and diagnostic commands to quickly identify and resolve problems.

## Quick Diagnostic Commands

```bash
# System health
curl https://api.qnwis.mol.gov.qa/health | jq

# Service status
sudo systemctl status qnwis

# Recent errors
sudo tail -n 100 /var/log/qnwis/error.log | grep ERROR

# Database connections
psql qnwis_prod -c "SELECT count(*) FROM pg_stat_activity;"

# Redis status
redis-cli ping

# Check metrics
curl -H "Authorization: Bearer $TOKEN" https://api.qnwis.mol.gov.qa/metrics | grep error
```

## Common Issues

### 1. Query Timeout Errors

**Symptoms:**
- HTTP 504 Gateway Timeout
- Error: "Query exceeded maximum response time"
- Logs show: `query_timeout`

**Decision Tree:**

```
Query Timeout
├─ Simple query timing out?
│  ├─ YES → Database issue (see Database Problems)
│  └─ NO → Continue
├─ Complex query timing out?
│  ├─ YES → Expected if > 90s, optimize query
│  └─ NO → Continue
└─ All queries timing out?
   ├─ YES → System overload (see Performance Issues)
   └─ NO → Investigate specific query pattern
```

**Solutions:**

```bash
# 1. Check current query load
psql qnwis_prod -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# 2. Identify slow queries
psql qnwis_prod <<EOF
SELECT pid, now() - query_start AS duration, left(query, 100)
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '10 seconds'
ORDER BY duration DESC;
EOF

# 3. Check for blocking queries
psql qnwis_prod <<EOF
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
EOF

# 4. Kill blocking query if necessary (use with caution)
psql qnwis_prod -c "SELECT pg_terminate_backend(12345);"

# 5. Restart application if persistent
sudo systemctl restart qnwis
```

### 2. Database Connection Errors

**Symptoms:**
- HTTP 500 Internal Server Error
- Error: "could not connect to server"
- Logs show: `OperationalError: connection refused`

**Diagnostic Steps:**

```bash
# 1. Check if PostgreSQL is running
ssh db-primary.qnwis.mol.gov.qa
sudo systemctl status postgresql

# 2. Test connection from app server
psql -h db-primary.qnwis.mol.gov.qa -U qnwis -d qnwis_prod -c "SELECT 1;"

# 3. Check connection pool exhaustion
psql qnwis_prod -c "SELECT count(*), state FROM pg_stat_activity WHERE datname = 'qnwis_prod' GROUP BY state;"

# 4. Check max connections
psql qnwis_prod -c "SHOW max_connections;"
psql qnwis_prod -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions:**

```bash
# If PostgreSQL is down
sudo systemctl start postgresql
sudo systemctl status postgresql

# If connection pool exhausted
# Option 1: Restart application to reset pool
sudo systemctl restart qnwis

# Option 2: Increase pool size (requires restart)
# Edit /etc/qnwis/.env
# DATABASE_POOL_SIZE=30
# DATABASE_MAX_OVERFLOW=20
sudo systemctl restart qnwis

# If max_connections reached
# Edit /etc/postgresql/14/main/postgresql.conf
# max_connections = 200
sudo systemctl restart postgresql
```

### 3. Redis Connection Failures

**Symptoms:**
- Cache misses increase to 100%
- Error: "Error connecting to Redis"
- Logs show: `redis.exceptions.ConnectionError`

**Diagnostic Steps:**

```bash
# 1. Check Redis status
redis-cli -h redis-01.qnwis.mol.gov.qa ping

# 2. Check Redis memory
redis-cli -h redis-01.qnwis.mol.gov.qa INFO memory

# 3. Check Redis connections
redis-cli -h redis-01.qnwis.mol.gov.qa INFO clients

# 4. Test from app server
redis-cli -h redis-01.qnwis.mol.gov.qa SET test_key test_value
redis-cli -h redis-01.qnwis.mol.gov.qa GET test_key
```

**Solutions:**

```bash
# If Redis is down
ssh redis-01.qnwis.mol.gov.qa
sudo systemctl start redis
sudo systemctl status redis

# If memory full (maxmemory reached)
redis-cli -h redis-01.qnwis.mol.gov.qa CONFIG SET maxmemory 4gb
redis-cli -h redis-01.qnwis.mol.gov.qa CONFIG SET maxmemory-policy allkeys-lru

# If connection limit reached
redis-cli -h redis-01.qnwis.mol.gov.qa CONFIG SET maxclients 10000

# Clear cache if corrupted
redis-cli -h redis-01.qnwis.mol.gov.qa FLUSHDB
```

### 4. CSRF Token Errors

**Symptoms:**
- HTTP 403 Forbidden
- Error: "CSRF token missing or invalid"
- Affects POST/PUT/DELETE requests

**Diagnostic Steps:**

```bash
# 1. Check CSRF configuration
grep CSRF_SECRET /etc/qnwis/.env

# 2. Test CSRF token generation
curl -c cookies.txt https://api.qnwis.mol.gov.qa/api/v1/csrf-token
cat cookies.txt

# 3. Check request headers
curl -v -X POST https://api.qnwis.mol.gov.qa/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"question": "test"}'
```

**Solutions:**

```bash
# If CSRF secret not set
# Edit /etc/qnwis/.env
# CSRF_SECRET=<generate-32-char-secret>
sudo systemctl restart qnwis

# If CSRF tokens expired
# Increase token lifetime
# Edit src/qnwis/api/middleware/csrf.py
# CSRF_TOKEN_LIFETIME = 3600  # 1 hour

# If CORS blocking CSRF headers
# Edit /etc/qnwis/.env
# ALLOWED_ORIGINS=https://app.qnwis.mol.gov.qa,https://dashboard.qnwis.mol.gov.qa
sudo systemctl restart qnwis
```

### 5. Rate Limit Exceeded

**Symptoms:**
- HTTP 429 Too Many Requests
- Error: "Rate limit exceeded"
- Headers: `X-RateLimit-Remaining: 0`

**Diagnostic Steps:**

```bash
# 1. Check user's rate limit status
redis-cli -h redis-01.qnwis.mol.gov.qa GET "rate_limit:user:analyst_123"

# 2. Check rate limit configuration
grep RATE_LIMIT /etc/qnwis/.env

# 3. Review recent requests
psql qnwis_prod -c "SELECT count(*), user_id FROM audit.query_log WHERE created_at > now() - interval '1 hour' GROUP BY user_id ORDER BY count DESC LIMIT 10;"
```

**Solutions:**

```bash
# Reset rate limit for specific user (emergency only)
redis-cli -h redis-01.qnwis.mol.gov.qa DEL "rate_limit:user:analyst_123"

# Increase rate limit for user (requires admin)
curl -X POST https://api.qnwis.mol.gov.qa/admin/rate-limit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"user_id": "analyst_123", "limit": 200}'

# Adjust global rate limits
# Edit /etc/qnwis/.env
# RATE_LIMIT_PER_HOUR=200
# RATE_LIMIT_BURST=20
sudo systemctl restart qnwis
```

### 6. CORS Errors

**Symptoms:**
- Browser console: "CORS policy blocked"
- Error: "Access-Control-Allow-Origin missing"
- Preflight OPTIONS requests failing

**Diagnostic Steps:**

```bash
# 1. Check CORS configuration
grep ALLOWED_ORIGINS /etc/qnwis/.env

# 2. Test CORS headers
curl -H "Origin: https://app.qnwis.mol.gov.qa" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://api.qnwis.mol.gov.qa/api/v1/query -v

# 3. Check response headers
curl -I https://api.qnwis.mol.gov.qa/health
```

**Solutions:**

```bash
# Add allowed origin
# Edit /etc/qnwis/.env
# ALLOWED_ORIGINS=https://app.qnwis.mol.gov.qa,https://new-app.qnwis.mol.gov.qa
sudo systemctl restart qnwis

# Allow credentials
# Edit src/qnwis/api/middleware/cors.py
# allow_credentials=True

# Check nginx/Traefik not stripping headers
# Edit /etc/nginx/sites-available/qnwis.conf
# Ensure proxy_pass_header Access-Control-Allow-Origin;
```

### 7. Authentication Failures

**Symptoms:**
- HTTP 401 Unauthorized
- Error: "Invalid or expired token"
- User cannot log in

**Diagnostic Steps:**

```bash
# 1. Check JWT token validity
# Decode token at https://jwt.io or:
python -c "import jwt; print(jwt.decode('$TOKEN', options={'verify_signature': False}))"

# 2. Check authentication logs
sudo grep "authentication" /var/log/qnwis/audit.log | tail -n 50

# 3. Verify secret key
grep SECRET_KEY /etc/qnwis/.env

# 4. Check token expiration
curl -H "Authorization: Bearer $TOKEN" https://api.qnwis.mol.gov.qa/api/v1/user/me
```

**Solutions:**

```bash
# If token expired, user needs to re-authenticate
# Direct user to login page

# If secret key changed, invalidate all tokens
# Edit /etc/qnwis/.env
# SECRET_KEY=<new-secret>
sudo systemctl restart qnwis
# All users must re-authenticate

# If authentication service down
# Check SSO integration
curl https://sso.mol.gov.qa/health
```

### 8. High Error Rate (4xx/5xx)

**Symptoms:**
- Metrics show error_rate > 1%
- Multiple HTTP 500 errors
- Alerts firing

**Diagnostic Steps:**

```bash
# 1. Identify error patterns
sudo tail -n 500 /var/log/qnwis/error.log | grep ERROR | cut -d' ' -f5 | sort | uniq -c | sort -rn

# 2. Check specific error details
sudo grep "HTTP 500" /var/log/qnwis/error.log | tail -n 10 | jq

# 3. Check application health
curl https://api.qnwis.mol.gov.qa/health/detailed | jq

# 4. Review recent deployments
git log --oneline -n 10
```

**Solutions:**

```bash
# If caused by recent deployment
# Rollback to previous version
git checkout v1.0.0
sudo systemctl restart qnwis

# If database-related errors
# Check database health (see Database Problems)

# If memory/resource exhaustion
# Restart application
sudo systemctl restart qnwis

# If persistent, escalate to development team
# Collect diagnostics:
sudo tar -czf /tmp/qnwis-diagnostics-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/log/qnwis/*.log \
  /etc/qnwis/config.yaml \
  /var/log/syslog
```

### 9. Slow Query Performance

**Symptoms:**
- Query response time > SLO
- p95 latency increasing
- Users reporting slowness

**Diagnostic Steps:**

```bash
# 1. Check current performance metrics
curl -H "Authorization: Bearer $TOKEN" https://api.qnwis.mol.gov.qa/metrics | grep duration

# 2. Identify slow queries
psql qnwis_prod <<EOF
SELECT query, calls, total_time, mean_time, max_time
FROM pg_stat_statements
WHERE mean_time > 1000  -- > 1 second
ORDER BY mean_time DESC
LIMIT 20;
EOF

# 3. Check cache hit rate
redis-cli INFO stats | grep keyspace_hits
curl https://api.qnwis.mol.gov.qa/metrics | grep cache_hit_rate

# 4. Check database load
psql qnwis_prod -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

**Solutions:**

```bash
# Warm up cache
python scripts/warm_cache.py

# Analyze and optimize slow queries
psql qnwis_prod <<EOF
EXPLAIN ANALYZE <slow_query>;
EOF

# Add missing indexes
psql qnwis_prod <<EOF
CREATE INDEX CONCURRENTLY idx_employment_sector_quarter 
ON qtr_employment_stats(sector, quarter);
EOF

# Vacuum and analyze
psql qnwis_prod -c "VACUUM ANALYZE qtr_employment_stats;"

# Increase database resources
# Edit /etc/postgresql/14/main/postgresql.conf
# shared_buffers = 4GB
# effective_cache_size = 12GB
sudo systemctl restart postgresql
```

### 10. Memory Leaks

**Symptoms:**
- Memory usage continuously increasing
- OOM (Out of Memory) errors
- Application crashes

**Diagnostic Steps:**

```bash
# 1. Check memory usage
free -h
ps aux | grep uvicorn | awk '{print $2, $4, $6, $11}'

# 2. Monitor over time
watch -n 60 'free -h && ps aux | grep uvicorn | awk "{print \$2, \$4, \$6, \$11}"'

# 3. Check for memory leaks in logs
sudo grep "MemoryError\|OutOfMemory" /var/log/qnwis/error.log

# 4. Profile memory usage (development)
python -m memory_profiler src/qnwis/api/server.py
```

**Solutions:**

```bash
# Immediate: Restart application
sudo systemctl restart qnwis

# Short-term: Increase memory limits
# Edit /etc/systemd/system/qnwis.service
# [Service]
# MemoryLimit=8G
sudo systemctl daemon-reload
sudo systemctl restart qnwis

# Long-term: Fix memory leak
# Escalate to development team with diagnostics
# Enable memory profiling in staging
# Identify leaking code path
# Deploy fix
```

## HTTP Status Code Reference

### 4xx Client Errors

| Code | Meaning | Common Causes | Solution |
|------|---------|---------------|----------|
| 400 | Bad Request | Invalid JSON, missing required fields | Validate request format |
| 401 | Unauthorized | Missing/invalid token | Re-authenticate |
| 403 | Forbidden | Insufficient permissions, CSRF failure | Check role, CSRF token |
| 404 | Not Found | Invalid endpoint, resource doesn't exist | Check URL, verify resource |
| 429 | Too Many Requests | Rate limit exceeded | Wait for reset, request limit increase |

### 5xx Server Errors

| Code | Meaning | Common Causes | Solution |
|------|---------|---------------|----------|
| 500 | Internal Server Error | Unhandled exception, code bug | Check logs, escalate to dev |
| 502 | Bad Gateway | App server down, nginx misconfigured | Check service status |
| 503 | Service Unavailable | Maintenance mode, overload | Check health endpoint |
| 504 | Gateway Timeout | Query timeout, slow response | Check performance, optimize query |

## Database Problems

### Connection Pool Exhausted

```bash
# Symptoms
psql qnwis_prod -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'qnwis_prod';"
# Returns value close to max_connections

# Solution
sudo systemctl restart qnwis  # Reset connection pool
```

### Table Bloat

```bash
# Check bloat
psql qnwis_prod <<EOF
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
       n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
EOF

# Fix with VACUUM
psql qnwis_prod -c "VACUUM FULL ANALYZE qtr_employment_stats;"
```

### Missing Indexes

```bash
# Find tables with high sequential scans
psql qnwis_prod <<EOF
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > 1000
ORDER BY seq_scan DESC
LIMIT 10;
EOF

# Add index
psql qnwis_prod -c "CREATE INDEX CONCURRENTLY idx_name ON table_name(column);"
```

### Replication Lag

```bash
# Check lag on replica
psql -h db-replica.qnwis.mol.gov.qa qnwis_prod <<EOF
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
EOF

# If lag > 1 minute, investigate
# Check network between primary and replica
# Check replica resources (CPU, disk I/O)
# Consider promoting replica if primary is failing
```

## Performance Troubleshooting

### High CPU Usage

```bash
# Identify CPU-intensive queries
psql qnwis_prod <<EOF
SELECT pid, query, state, 
       now() - query_start AS duration
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
EOF

# Check application CPU
top -p $(pgrep -f uvicorn)

# Solution: Optimize queries, add indexes, scale horizontally
```

### High Disk I/O

```bash
# Check disk I/O
iostat -x 5

# Identify I/O-intensive queries
psql qnwis_prod <<EOF
SELECT query, shared_blks_read, shared_blks_hit,
       shared_blks_read::float / (shared_blks_read + shared_blks_hit) AS cache_miss_ratio
FROM pg_stat_statements
WHERE shared_blks_read > 1000
ORDER BY shared_blks_read DESC
LIMIT 10;
EOF

# Solution: Increase shared_buffers, add indexes, optimize queries
```

### Cache Miss Rate High

```bash
# Check Redis cache hit rate
redis-cli INFO stats | grep keyspace

# Check application cache metrics
curl https://api.qnwis.mol.gov.qa/metrics | grep cache_hit_rate

# Solutions:
# 1. Increase cache TTL
# 2. Warm up cache
python scripts/warm_cache.py
# 3. Increase Redis memory
redis-cli CONFIG SET maxmemory 8gb
```

## Log Analysis

### Finding Specific Errors

```bash
# Search by error type
sudo grep "DatabaseError" /var/log/qnwis/error.log | tail -n 20

# Search by query ID
sudo grep "query_id=q_2024_001234" /var/log/qnwis/app.log | jq

# Search by user
sudo grep "user_id=analyst_123" /var/log/qnwis/audit.log | jq

# Search by time range
sudo grep "2024-11-12T05:" /var/log/qnwis/app.log | jq
```

### Log Patterns

```bash
# Count errors by type
sudo grep ERROR /var/log/qnwis/error.log | cut -d' ' -f5 | sort | uniq -c | sort -rn

# Find most common errors
sudo tail -n 1000 /var/log/qnwis/error.log | grep ERROR | jq -r '.error_type' | sort | uniq -c | sort -rn

# Track error rate over time
for hour in {00..23}; do
  count=$(sudo grep "2024-11-12T$hour:" /var/log/qnwis/error.log | grep ERROR | wc -l)
  echo "$hour:00 - $count errors"
done
```

## Emergency Procedures

### Complete System Restart

```bash
# 1. Stop application servers
for host in app-01 app-02 app-03; do
  ssh $host "sudo systemctl stop qnwis"
done

# 2. Restart Redis
ssh redis-01.qnwis.mol.gov.qa "sudo systemctl restart redis"

# 3. Restart PostgreSQL (if needed)
ssh db-primary.qnwis.mol.gov.qa "sudo systemctl restart postgresql"

# 4. Start application servers
for host in app-01 app-02 app-03; do
  ssh $host "sudo systemctl start qnwis"
  sleep 10
done

# 5. Verify health
curl https://api.qnwis.mol.gov.qa/health | jq
```

### Emergency Rollback

```bash
# See OPERATIONS_RUNBOOK.md for detailed rollback procedures
git checkout v1.0.0  # Previous stable version
sudo systemctl restart qnwis
```

### Enable Maintenance Mode

```bash
curl -X POST https://api.qnwis.mol.gov.qa/admin/maintenance \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"enabled": true, "message": "Emergency maintenance in progress"}'
```

## Getting Help

### Information to Collect

When escalating issues, provide:

1. **Error description**: What happened, when, how often
2. **Query ID**: From error response or logs
3. **Logs**: Last 100 lines of error log
4. **Metrics**: Current performance metrics
5. **Recent changes**: Deployments, config changes
6. **Impact**: Number of users affected, severity

### Escalation

- **L1 (On-call)**: Initial troubleshooting
- **L2 (Senior SRE)**: Complex issues, system changes
- **L3 (Development)**: Code bugs, architectural issues
- **Security Team**: Security incidents

### Useful Commands for Diagnostics

```bash
# Collect all diagnostics
sudo tar -czf /tmp/qnwis-diagnostics-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/log/qnwis/*.log \
  /etc/qnwis/config.yaml \
  /var/log/syslog \
  /var/log/postgresql/*.log

# System info
uname -a
free -h
df -h
uptime

# Service status
sudo systemctl status qnwis postgresql redis nginx

# Network connectivity
ping -c 3 db-primary.qnwis.mol.gov.qa
ping -c 3 redis-01.qnwis.mol.gov.qa
```

---

**For operational procedures, see**: [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md)  
**For security issues, see**: [SECURITY.md](./SECURITY.md)  
**For performance tuning, see**: [PERFORMANCE.md](./PERFORMANCE.md)
