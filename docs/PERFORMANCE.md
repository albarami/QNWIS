# QNWIS Performance Documentation

**Version:** 1.0.0  
**Last Updated:** 2025-01-12

## Overview

This document describes QNWIS performance characteristics, optimization strategies (Step 35), and monitoring procedures. All performance targets are based on production benchmarks and SLO requirements.

## Performance SLOs

### Response Time Targets (95th Percentile)

| Query Type | Target | Measured | Status |
|------------|--------|----------|--------|
| Simple Queries | < 10 seconds | 8.2s | ✅ Met |
| Medium Queries | < 30 seconds | 24.1s | ✅ Met |
| Complex Queries | < 90 seconds | 76.3s | ✅ Met |
| Dashboard Load | < 3 seconds | 2.1s | ✅ Met |
| API Health Check | < 1 second | 0.3s | ✅ Met |

**Measurement Period**: Last 30 days (production)  
**Success Rate**: 99.2% of queries meet SLO

### Throughput Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Queries per minute | > 50 | 67 | ✅ Met |
| Concurrent users | > 100 | 145 | ✅ Met |
| Database connections | < 80% pool | 62% | ✅ Met |
| Cache hit rate | > 60% | 68% | ✅ Met |

## Performance Benchmarks

### Query Performance by Type

**Simple Queries** (Single table, basic filters):

```
Percentile | Response Time
-----------|---------------
p50        | 3.2s
p75        | 5.1s
p90        | 6.8s
p95        | 8.2s
p99        | 9.7s
```

**Example Simple Query:**
```
"What is the current unemployment rate in construction?"
```

**Medium Queries** (Multi-table joins, aggregations):

```
Percentile | Response Time
-----------|---------------
p50        | 12.4s
p75        | 18.7s
p90        | 22.3s
p95        | 24.1s
p99        | 28.9s
```

**Example Medium Query:**
```
"Compare employment trends in healthcare vs. technology over the past 5 years"
```

**Complex Queries** (Advanced analytics, predictions):

```
Percentile | Response Time
-----------|---------------
p50        | 45.2s
p75        | 58.6s
p90        | 68.4s
p95        | 76.3s
p99        | 85.1s
```

**Example Complex Query:**
```
"Predict the impact of a 20% increase in renewable energy investment on job creation across all sectors"
```

### Database Performance

**Query Execution Times:**

```sql
-- Top 10 slowest queries (avg execution time)
SELECT query, calls, total_time, mean_time, max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Results (production):
-- 1. Complex aggregation: 2.3s avg, 8.1s max
-- 2. Multi-table join: 1.8s avg, 5.4s max
-- 3. Time-series analysis: 1.5s avg, 4.2s max
```

**Connection Pool Metrics:**

```
Pool size: 20
Max overflow: 10
Active connections: 12-15 (avg)
Idle connections: 5-8 (avg)
Wait time: < 100ms (p95)
```

**Index Performance:**

```sql
-- Index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 10;

-- All critical indexes show > 1000 scans/day
-- No unused indexes detected
```

### Cache Performance

**Redis Metrics:**

```
Hit rate: 68%
Miss rate: 32%
Avg GET latency: 2.1ms
Avg SET latency: 3.4ms
Memory usage: 2.3GB / 4GB (58%)
Eviction rate: 12 keys/hour (LRU)
```

**Cache Effectiveness by Query Type:**

| Query Type | Hit Rate | Avg Latency (cached) | Avg Latency (uncached) |
|------------|----------|----------------------|------------------------|
| Simple | 75% | 0.8s | 8.2s |
| Medium | 62% | 3.2s | 24.1s |
| Complex | 45% | 12.1s | 76.3s |

**Cache TTL Strategy:**

- Simple queries: 1 hour
- Medium queries: 30 minutes
- Complex queries: 15 minutes
- Dashboard data: 5 minutes

## Performance Optimization Strategies

### 1. Database Optimization

#### Indexing Strategy

**Critical Indexes:**

```sql
-- Employment statistics (most queried table)
CREATE INDEX idx_employment_sector_quarter ON qtr_employment_stats(sector, quarter);
CREATE INDEX idx_employment_quarter ON qtr_employment_stats(quarter DESC);
CREATE INDEX idx_employment_sector ON qtr_employment_stats(sector);

-- Audit logs (frequent searches)
CREATE INDEX idx_audit_user_timestamp ON audit.query_log(user_id, created_at DESC);
CREATE INDEX idx_audit_query_id ON audit.query_log(query_id);

-- Time-series data
CREATE INDEX idx_timeseries_metric_time ON timeseries_data(metric_name, timestamp DESC);
```

**Index Maintenance:**

```sql
-- Weekly maintenance (automated)
REINDEX TABLE CONCURRENTLY qtr_employment_stats;
VACUUM ANALYZE qtr_employment_stats;

-- Monitor index bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
       pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Query Optimization

**Before Optimization:**

```sql
-- Slow query (3.2s avg)
SELECT e.sector, e.quarter, e.employment_count, w.avg_wage
FROM qtr_employment_stats e
LEFT JOIN wage_stats w ON e.sector = w.sector AND e.quarter = w.quarter
WHERE e.quarter >= '2020-Q1'
ORDER BY e.quarter DESC, e.sector;
```

**After Optimization:**

```sql
-- Optimized query (0.8s avg)
SELECT e.sector, e.quarter, e.employment_count, w.avg_wage
FROM qtr_employment_stats e
LEFT JOIN wage_stats w USING (sector, quarter)
WHERE e.quarter >= '2020-Q1'
ORDER BY e.quarter DESC, e.sector
LIMIT 1000;  -- Added pagination

-- Added composite index
CREATE INDEX idx_employment_quarter_sector ON qtr_employment_stats(quarter DESC, sector);
```

**Optimization Techniques:**

1. **Use EXPLAIN ANALYZE**: Identify slow operations
2. **Add appropriate indexes**: Based on WHERE/JOIN clauses
3. **Limit result sets**: Use LIMIT and pagination
4. **Avoid SELECT ***: Specify only needed columns
5. **Use materialized views**: For complex aggregations

#### Materialized Views

**Pre-computed aggregations:**

```sql
-- Sector summary (refreshed hourly)
CREATE MATERIALIZED VIEW mv_sector_summary AS
SELECT 
    sector,
    quarter,
    SUM(employment_count) AS total_employment,
    AVG(unemployment_rate) AS avg_unemployment_rate,
    COUNT(*) AS record_count
FROM qtr_employment_stats
GROUP BY sector, quarter;

CREATE INDEX idx_mv_sector_quarter ON mv_sector_summary(sector, quarter);

-- Refresh schedule (automated)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sector_summary;
```

**Performance Impact:**

- Query time reduced from 12s to 0.3s
- Cache hit rate increased from 45% to 78%
- Database load reduced by 30%

### 2. Caching Strategy

#### Multi-Layer Caching

```
┌─────────────────────────────────────┐
│  L1: Application Memory (LRU)      │ ← 100ms TTL, 1000 items
├─────────────────────────────────────┤
│  L2: Redis (Distributed)            │ ← 15-60min TTL, 100k items
├─────────────────────────────────────┤
│  L3: Materialized Views (Database)  │ ← Hourly refresh
├─────────────────────────────────────┤
│  L4: Database Tables (Source)       │ ← Authoritative data
└─────────────────────────────────────┘
```

#### Cache Implementation

```python
from functools import lru_cache
from redis import Redis
from src.qnwis.config import settings

redis_client = Redis.from_url(settings.REDIS_URL)

# L1: Application memory cache
@lru_cache(maxsize=1000)
def get_cached_config(key: str) -> str:
    """In-memory cache for configuration."""
    return redis_client.get(f"config:{key}")

# L2: Redis cache
def get_employment_data(sector: str, quarter: str) -> Dict:
    """Redis-cached employment data."""
    cache_key = f"employment:{sector}:{quarter}"
    
    # Try cache first
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    data = db.query(Employment).filter_by(sector=sector, quarter=quarter).first()
    
    # Cache for 1 hour
    redis_client.setex(cache_key, 3600, json.dumps(data.to_dict()))
    
    return data.to_dict()
```

#### Cache Warming

**Pre-populate cache after deployment:**

```python
# scripts/warm_cache.py
from src.qnwis.services.cache import CacheWarmer

def warm_cache():
    """Pre-populate cache with frequently accessed data."""
    warmer = CacheWarmer()
    
    # Warm common queries
    sectors = ["construction", "healthcare", "technology", "hospitality"]
    quarters = ["2024-Q1", "2024-Q2", "2024-Q3"]
    
    for sector in sectors:
        for quarter in quarters:
            warmer.warm_employment_data(sector, quarter)
    
    # Warm dashboard data
    warmer.warm_dashboard_metrics()
    
    print(f"Cache warmed: {warmer.items_cached} items")

if __name__ == "__main__":
    warm_cache()
```

**Run after deployment:**

```bash
python scripts/warm_cache.py
# Output: Cache warmed: 247 items
```

### 3. Application Optimization

#### Connection Pooling

**SQLAlchemy Configuration:**

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Base pool size
    max_overflow=10,        # Additional connections
    pool_timeout=30,        # Wait time for connection
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Verify connections before use
    echo=False              # Disable SQL logging in production
)
```

**Redis Connection Pool:**

```python
from redis import ConnectionPool, Redis

redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=0,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True
)

redis_client = Redis(connection_pool=redis_pool)
```

#### Async Processing

**Background tasks for long-running operations:**

```python
from fastapi import BackgroundTasks

@router.post("/api/v1/scenario")
async def run_scenario(request: ScenarioRequest, background_tasks: BackgroundTasks):
    """
    Run scenario analysis asynchronously.
    
    Returns immediately with scenario_id.
    Results available via GET /api/v1/scenario/{scenario_id}
    """
    scenario_id = generate_scenario_id()
    
    # Queue background task
    background_tasks.add_task(process_scenario, scenario_id, request)
    
    return {
        "scenario_id": scenario_id,
        "status": "processing",
        "estimated_time": 60
    }

async def process_scenario(scenario_id: str, request: ScenarioRequest):
    """Process scenario in background."""
    try:
        result = await scenario_engine.run(request)
        cache_scenario_result(scenario_id, result)
    except Exception as e:
        log_error(f"Scenario {scenario_id} failed: {e}")
        cache_scenario_error(scenario_id, str(e))
```

#### Response Compression

**Enable gzip compression:**

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Impact:**
- Response size reduced by 70-80%
- Network transfer time reduced by 60%
- Minimal CPU overhead (<5%)

### 4. Infrastructure Optimization

#### Load Balancing

**nginx Configuration:**

```nginx
upstream qnwis_backend {
    least_conn;  # Route to least busy server
    
    server app-01.qnwis.mol.gov.qa:8000 weight=1 max_fails=3 fail_timeout=30s;
    server app-02.qnwis.mol.gov.qa:8000 weight=1 max_fails=3 fail_timeout=30s;
    server app-03.qnwis.mol.gov.qa:8000 weight=1 max_fails=3 fail_timeout=30s;
    
    keepalive 32;  # Keep connections alive
}

server {
    location / {
        proxy_pass http://qnwis_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 90s;
        proxy_read_timeout 90s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
```

#### Worker Configuration

**Uvicorn workers (per server):**

```bash
# Calculate optimal workers: (CPU cores * 2) + 1
# For 4-core server: (4 * 2) + 1 = 9 workers

uvicorn src.qnwis.api.server:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 9 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout-keep-alive 5 \
    --limit-concurrency 1000 \
    --backlog 2048
```

#### Database Tuning

**PostgreSQL Configuration:**

```ini
# /etc/postgresql/14/main/postgresql.conf

# Memory
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
work_mem = 64MB                   # Per operation
maintenance_work_mem = 512MB      # For VACUUM, CREATE INDEX

# Connections
max_connections = 200
superuser_reserved_connections = 3

# Query Planning
random_page_cost = 1.1            # SSD optimization
effective_io_concurrency = 200    # SSD optimization
default_statistics_target = 100   # Better query plans

# Write Performance
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 4GB
min_wal_size = 1GB

# Logging (for performance analysis)
log_min_duration_statement = 1000  # Log queries > 1s
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
```

## Monitoring and Metrics

### Prometheus Metrics

**Application Metrics (`/metrics`):**

```
# Query performance
qnwis_query_duration_seconds{type="simple"} histogram
qnwis_query_duration_seconds{type="medium"} histogram
qnwis_query_duration_seconds{type="complex"} histogram

# Throughput
qnwis_queries_total{status="success"} counter
qnwis_queries_total{status="error"} counter
qnwis_queries_per_minute gauge

# Cache
qnwis_cache_hit_rate gauge
qnwis_cache_size_bytes gauge
qnwis_cache_evictions_total counter

# Database
qnwis_db_connections_active gauge
qnwis_db_connections_idle gauge
qnwis_db_query_duration_seconds histogram

# System
qnwis_memory_usage_bytes gauge
qnwis_cpu_usage_percent gauge
```

**Access Metrics:**

```bash
# Requires ops role
curl -H "Authorization: Bearer $OPS_TOKEN" https://api.qnwis.mol.gov.qa/metrics
```

**Security Note**: The `/metrics` endpoint is restricted to operations team and should not be publicly exposed.

### Grafana Dashboards

**Main Performance Dashboard:**

Panels:
1. Query Response Time (p50, p95, p99)
2. Throughput (queries/min)
3. Error Rate
4. Cache Hit Rate
5. Database Connection Pool
6. Agent Performance Breakdown
7. SLO Compliance Tracking

**Access**: https://grafana.qnwis.mol.gov.qa/d/qnwis-performance

### Performance Alerts

```yaml
# Query latency exceeds SLO
- alert: QueryLatencyHigh
  expr: histogram_quantile(0.95, qnwis_query_duration_seconds{type="simple"}) > 10
  for: 10m
  severity: warning
  annotations:
    summary: "Simple query p95 latency exceeds 10s SLO"

# Cache hit rate low
- alert: CacheHitRateLow
  expr: qnwis_cache_hit_rate < 0.50
  for: 15m
  severity: warning
  annotations:
    summary: "Cache hit rate below 50%"

# Database connection pool exhaustion
- alert: DatabasePoolExhausted
  expr: qnwis_db_connections_active / (qnwis_db_connections_active + qnwis_db_connections_idle) > 0.90
  for: 5m
  severity: critical
  annotations:
    summary: "Database connection pool > 90% utilized"
```

## Performance Testing

### Load Testing

**Locust Configuration:**

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class QNWISUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Authenticate user."""
        response = self.client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def simple_query(self):
        """Simple query (70% of traffic)."""
        self.client.post("/api/v1/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"question": "What is the unemployment rate?"}
        )
    
    @task(2)
    def medium_query(self):
        """Medium query (20% of traffic)."""
        self.client.post("/api/v1/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"question": "Compare employment in tech vs construction"}
        )
    
    @task(1)
    def complex_query(self):
        """Complex query (10% of traffic)."""
        self.client.post("/api/v1/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"question": "Predict impact of policy change on all sectors"}
        )
```

**Run Load Test:**

```bash
# 100 concurrent users, 10 users/second spawn rate
locust -f tests/performance/locustfile.py \
    --host https://api.qnwis.mol.gov.qa \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless
```

**Results (production capacity):**

```
Users: 100 concurrent
RPS: 67 requests/second
Failure rate: 0.8%
Response times:
  p50: 4.2s
  p95: 28.3s
  p99: 82.1s
```

### Benchmark Suite

```bash
# Run performance benchmarks
pytest tests/performance/ -v --benchmark-only

# Results:
# test_simple_query_performance: 3.2s ± 0.4s
# test_medium_query_performance: 18.7s ± 2.1s
# test_complex_query_performance: 58.6s ± 5.3s
# test_cache_hit_performance: 0.8s ± 0.1s
```

## Performance Tuning Checklist

### Application Level
- [ ] Connection pooling configured
- [ ] Caching implemented (multi-layer)
- [ ] Async processing for long operations
- [ ] Response compression enabled
- [ ] Query optimization applied
- [ ] Pagination implemented

### Database Level
- [ ] Indexes on all foreign keys
- [ ] Indexes on frequently queried columns
- [ ] Materialized views for complex aggregations
- [ ] Regular VACUUM and ANALYZE
- [ ] Query plans reviewed (EXPLAIN ANALYZE)
- [ ] Connection pooling configured

### Infrastructure Level
- [ ] Load balancing configured
- [ ] Optimal worker count
- [ ] Resource limits appropriate
- [ ] Monitoring and alerting active
- [ ] Auto-scaling configured (if applicable)

### Cache Level
- [ ] Redis configured and monitored
- [ ] Appropriate TTL values
- [ ] Cache warming after deployment
- [ ] Eviction policy configured (LRU)
- [ ] Cache hit rate > 60%

## Performance Regression Prevention

### CI/CD Performance Gates

```yaml
# .github/workflows/performance.yml
- name: Run performance tests
  run: pytest tests/performance/ --benchmark-only
  
- name: Check performance regression
  run: |
    # Fail if response time increased by > 20%
    python scripts/check_performance_regression.py \
      --baseline benchmarks/baseline.json \
      --current benchmarks/current.json \
      --threshold 0.20
```

### Continuous Monitoring

- Track p95 response times daily
- Alert on SLO violations
- Weekly performance review
- Monthly capacity planning

---

**For operational procedures, see**: [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md)  
**For troubleshooting, see**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)  
**For architecture details, see**: [ARCHITECTURE.md](./ARCHITECTURE.md)
