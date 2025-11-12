# Database Performance Tuning Guide

**Target**: Optimize PostgreSQL queries to support <10s simple, <30s medium, <90s complex query targets.

---

## 🎯 Optimization Strategy

### 1. Identify Slow Queries

Use the DB tuning helpers to analyze query performance:

```python
from qnwis.perf.db_tuning import explain, analyze
from sqlalchemy import create_engine

engine = create_engine(os.getenv("QNWIS_DB_URL"))

# Analyze a query
query = """
SELECT sector, AVG(salary) as avg_salary, COUNT(*) as count
FROM jobs
WHERE year = :year
GROUP BY sector
"""
params = {"year": 2024}

# Get execution plan
plan = explain(engine, query, params)
print(f"Node Type: {plan['Plan']['Node Type']}")
print(f"Total Cost: {plan['Plan']['Total Cost']}")

# Full analysis with timing
stats = analyze(engine, query, params)
print(f"Execution Time: {stats['Execution Time']}ms")
print(f"Planning Time: {stats['Planning Time']}ms")
```

### 2. Common Query Patterns

#### Pattern 1: Sector Filtering
```sql
-- Common query
SELECT * FROM jobs WHERE sector = 'IT';

-- Recommended index
CREATE INDEX idx_jobs_sector ON jobs(sector);
```

#### Pattern 2: Year-Based Aggregations
```sql
-- Common query
SELECT year, sector, COUNT(*) 
FROM jobs 
WHERE year >= 2020 
GROUP BY year, sector;

-- Recommended index
CREATE INDEX idx_jobs_year_sector ON jobs(year, sector);
```

#### Pattern 3: Salary Statistics
```sql
-- Common query
SELECT sector, AVG(salary), MIN(salary), MAX(salary)
FROM jobs
WHERE year = 2024
GROUP BY sector;

-- Recommended materialized view
CREATE MATERIALIZED VIEW mv_salary_stats AS
SELECT 
    year,
    sector,
    AVG(salary) as avg_salary,
    MIN(salary) as min_salary,
    MAX(salary) as max_salary,
    STDDEV(salary) as stddev_salary,
    COUNT(*) as count
FROM jobs
GROUP BY year, sector;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_salary_stats;
```

### 3. Index Recommendations

Based on common query patterns, consider these indexes:

```sql
-- Jobs table
CREATE INDEX idx_jobs_sector ON jobs(sector);
CREATE INDEX idx_jobs_year ON jobs(year);
CREATE INDEX idx_jobs_year_sector ON jobs(year, sector);
CREATE INDEX idx_jobs_nationality ON jobs(nationality);
CREATE INDEX idx_jobs_education_level ON jobs(education_level);

-- Composite indexes for common filters
CREATE INDEX idx_jobs_sector_year_salary ON jobs(sector, year, salary);

-- Partial indexes for active records
CREATE INDEX idx_jobs_active ON jobs(id) WHERE status = 'active';
```

### 4. Query Optimization Techniques

#### Use EXPLAIN ANALYZE
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT sector, COUNT(*) 
FROM jobs 
WHERE year = 2024 
GROUP BY sector;
```

#### Avoid SELECT *
```sql
-- Bad
SELECT * FROM jobs WHERE sector = 'IT';

-- Good
SELECT id, title, salary, sector FROM jobs WHERE sector = 'IT';
```

#### Use LIMIT for Large Results
```sql
-- Add pagination
SELECT * FROM jobs 
WHERE sector = 'IT' 
ORDER BY created_at DESC 
LIMIT 1000 OFFSET 0;
```

#### Optimize JOINs
```sql
-- Ensure JOIN columns are indexed
CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_jobs_id ON jobs(id);

-- Use INNER JOIN when possible
SELECT j.title, a.status
FROM jobs j
INNER JOIN applications a ON j.id = a.job_id
WHERE j.sector = 'IT';
```

### 5. Connection Pool Configuration

```python
from qnwis.perf.db_tuning import configure_pool

# At application startup
configure_pool(
    engine,
    pool_size=30,        # Base connections
    max_overflow=10,     # Additional connections under load
    timeout=30,          # Wait time for connection
    recycle=3600         # Recycle connections every hour
)
```

### 6. Statement Timeouts

```python
from qnwis.perf.db_tuning import with_timeout

# Set timeout for long-running queries
with with_timeout(engine, seconds=60):
    result = session.execute(complex_query)
```

### 7. Work Memory Tuning

```python
from qnwis.perf.db_tuning import set_work_mem

# Increase work_mem for complex aggregations
set_work_mem(engine, mb=256)
result = session.execute(aggregation_query)
```

---

## 📊 Performance Monitoring

### Track Query Performance

```python
from qnwis.perf.metrics import DB_LATENCY
import time

start = time.perf_counter()
result = session.execute(query)
duration = time.perf_counter() - start

DB_LATENCY.labels(operation="select_jobs").observe(duration)
```

### Identify Slow Queries

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slowest queries
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## 🎯 Target Metrics

| Query Type | Target p95 | Optimization Priority |
|------------|-----------|----------------------|
| Simple SELECT | <50ms | High |
| Filtered SELECT | <100ms | High |
| Aggregations | <500ms | Medium |
| Complex JOINs | <1000ms | Medium |
| Materialized View Refresh | <5000ms | Low |

---

## ✅ Optimization Checklist

- [ ] Run EXPLAIN ANALYZE on top 5 slow queries
- [ ] Create indexes for common filter columns
- [ ] Implement materialized views for aggregates
- [ ] Configure connection pool
- [ ] Set statement timeouts
- [ ] Enable query logging
- [ ] Monitor pg_stat_statements
- [ ] Document index strategy
- [ ] Test with production-like data volume
- [ ] Validate no security regressions

---

## 🚨 Important Notes

### DO NOT
- ❌ Create indexes on every column (index bloat)
- ❌ Use SELECT * in production queries
- ❌ Disable query timeouts
- ❌ Skip EXPLAIN ANALYZE before optimization
- ❌ Create indexes without testing impact

### ALWAYS
- ✅ Use parameterized queries (prevents SQL injection)
- ✅ Test indexes with realistic data volumes
- ✅ Monitor index usage with pg_stat_user_indexes
- ✅ Refresh materialized views on schedule
- ✅ Vacuum and analyze tables regularly

---

## 📚 PostgreSQL Resources

- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [EXPLAIN Documentation](https://www.postgresql.org/docs/current/sql-explain.html)
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
