# QNWIS Data Dictionary

**Version:** 1.0.0  
**Last Updated:** 2025-01-12

## Overview

This document describes the LMIS database schema, table structures, field definitions, and data classifications used in QNWIS. All data adheres to the Deterministic Data Layer contract.

## Database Structure

### Schema Organization

```
qnwis_prod/
├── public/              # LMIS data tables (60+ tables)
├── audit/               # Audit and logging tables
├── cache/               # Materialized views
└── metadata/            # System metadata
```

## Core LMIS Tables

### Employment Statistics

#### `qtr_employment_stats`

**Purpose**: Quarterly employment statistics by sector  
**Classification**: Internal  
**Update Frequency**: Quarterly  
**Primary Source**: Ministry of Labour LMIS

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 12345 |
| `quarter` | VARCHAR(10) | NO | Quarter identifier (YYYY-QN) | 2024-Q3 |
| `sector` | VARCHAR(100) | NO | Economic sector | construction |
| `employment_count` | INTEGER | NO | Total employed persons | 125080 |
| `unemployment_rate` | DECIMAL(5,4) | YES | Unemployment rate (0-1) | 0.0320 |
| `qatari_count` | INTEGER | YES | Qatari nationals employed | 15600 |
| `expat_count` | INTEGER | YES | Expatriate workers | 109480 |
| `male_count` | INTEGER | YES | Male employees | 120000 |
| `female_count` | INTEGER | YES | Female employees | 5080 |
| `avg_wage_qar` | DECIMAL(10,2) | YES | Average wage (QAR) | 8500.00 |
| `data_source` | VARCHAR(50) | NO | Source system | LMIS_PROD |
| `classification` | VARCHAR(20) | NO | Data classification | internal |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |
| `updated_at` | TIMESTAMP | NO | Last update time | 2024-10-15 14:30:00 |

**Indexes**:
```sql
CREATE INDEX idx_employment_sector_quarter ON qtr_employment_stats(sector, quarter);
CREATE INDEX idx_employment_quarter ON qtr_employment_stats(quarter DESC);
CREATE INDEX idx_employment_sector ON qtr_employment_stats(sector);
```

**Constraints**:
```sql
ALTER TABLE qtr_employment_stats ADD CONSTRAINT chk_unemployment_rate 
    CHECK (unemployment_rate >= 0 AND unemployment_rate <= 1);
ALTER TABLE qtr_employment_stats ADD CONSTRAINT chk_employment_count 
    CHECK (employment_count >= 0);
```

#### `sector_employment_detail`

**Purpose**: Detailed employment breakdown by occupation  
**Classification**: Internal  
**Update Frequency**: Quarterly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 23456 |
| `quarter` | VARCHAR(10) | NO | Quarter identifier | 2024-Q3 |
| `sector` | VARCHAR(100) | NO | Economic sector | healthcare |
| `occupation` | VARCHAR(200) | NO | Occupation title | Registered Nurse |
| `occupation_code` | VARCHAR(20) | YES | ISCO-08 code | 2221 |
| `employment_count` | INTEGER | NO | Employed in occupation | 4520 |
| `avg_wage_qar` | DECIMAL(10,2) | YES | Average wage | 12300.00 |
| `education_level` | VARCHAR(50) | YES | Required education | Bachelor |
| `experience_years` | INTEGER | YES | Required experience | 3 |
| `data_source` | VARCHAR(50) | NO | Source system | LMIS_PROD |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |

**Indexes**:
```sql
CREATE INDEX idx_sector_detail_sector_quarter ON sector_employment_detail(sector, quarter);
CREATE INDEX idx_sector_detail_occupation ON sector_employment_detail(occupation);
```

### Wage Statistics

#### `wage_stats`

**Purpose**: Wage statistics by sector and occupation  
**Classification**: Internal  
**Update Frequency**: Quarterly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 34567 |
| `quarter` | VARCHAR(10) | NO | Quarter identifier | 2024-Q3 |
| `sector` | VARCHAR(100) | NO | Economic sector | technology |
| `occupation` | VARCHAR(200) | YES | Occupation title | Software Engineer |
| `avg_wage_qar` | DECIMAL(10,2) | NO | Average wage | 18500.00 |
| `median_wage_qar` | DECIMAL(10,2) | YES | Median wage | 16000.00 |
| `min_wage_qar` | DECIMAL(10,2) | YES | Minimum wage | 8000.00 |
| `max_wage_qar` | DECIMAL(10,2) | YES | Maximum wage | 45000.00 |
| `wage_growth_pct` | DECIMAL(5,2) | YES | YoY wage growth (%) | 5.20 |
| `sample_size` | INTEGER | YES | Number of observations | 1250 |
| `data_source` | VARCHAR(50) | NO | Source system | LMIS_PROD |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |

**Indexes**:
```sql
CREATE INDEX idx_wage_sector_quarter ON wage_stats(sector, quarter);
CREATE INDEX idx_wage_occupation ON wage_stats(occupation);
```

### Economic Indicators

#### `economic_indicators`

**Purpose**: Macroeconomic indicators  
**Classification**: Public  
**Update Frequency**: Quarterly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 45678 |
| `quarter` | VARCHAR(10) | NO | Quarter identifier | 2024-Q3 |
| `indicator_name` | VARCHAR(100) | NO | Indicator name | GDP_REAL |
| `indicator_value` | DECIMAL(15,2) | NO | Indicator value | 185000000000.00 |
| `unit` | VARCHAR(50) | YES | Unit of measurement | QAR |
| `growth_rate_pct` | DECIMAL(5,2) | YES | YoY growth rate (%) | 3.80 |
| `data_source` | VARCHAR(50) | NO | Source system | PSA_QATAR |
| `classification` | VARCHAR(20) | NO | Data classification | public |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |

**Common Indicators**:
- `GDP_REAL`: Real GDP (QAR)
- `GDP_NOMINAL`: Nominal GDP (QAR)
- `INFLATION_RATE`: Consumer Price Index growth (%)
- `UNEMPLOYMENT_RATE`: National unemployment rate (%)
- `LABOR_FORCE_PARTICIPATION`: Labor force participation rate (%)

**Indexes**:
```sql
CREATE INDEX idx_economic_quarter_indicator ON economic_indicators(quarter, indicator_name);
```

### Sector Trends

#### `sector_trends`

**Purpose**: Sector-level trend analysis  
**Classification**: Internal  
**Update Frequency**: Quarterly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 56789 |
| `sector` | VARCHAR(100) | NO | Economic sector | construction |
| `quarter` | VARCHAR(10) | NO | Quarter identifier | 2024-Q3 |
| `growth_rate` | DECIMAL(5,2) | YES | Employment growth (%) | 2.30 |
| `employment_change` | INTEGER | YES | Net employment change | 2800 |
| `investment_qar` | DECIMAL(15,2) | YES | Sector investment (QAR) | 5200000000.00 |
| `productivity_index` | DECIMAL(8,2) | YES | Productivity index | 105.20 |
| `business_confidence` | DECIMAL(5,2) | YES | Business confidence (0-100) | 72.50 |
| `data_source` | VARCHAR(50) | NO | Source system | LMIS_PROD |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |

**Indexes**:
```sql
CREATE INDEX idx_sector_trends_sector_quarter ON sector_trends(sector, quarter);
```

### Infrastructure Projects

#### `infrastructure_projects`

**Purpose**: Major infrastructure projects and employment impact  
**Classification**: Internal  
**Update Frequency**: Monthly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 67890 |
| `project_id` | VARCHAR(50) | NO | Unique project ID | PROJ_2024_001 |
| `project_name` | VARCHAR(255) | NO | Project name | Metro Red Line Extension |
| `sector` | VARCHAR(100) | NO | Primary sector | infrastructure |
| `start_date` | DATE | NO | Project start date | 2023-01-15 |
| `end_date` | DATE | YES | Project end date | 2026-12-31 |
| `budget_qar` | DECIMAL(15,2) | YES | Total budget (QAR) | 8500000000.00 |
| `jobs_created` | INTEGER | YES | Direct jobs created | 3500 |
| `indirect_jobs` | INTEGER | YES | Indirect jobs created | 7200 |
| `status` | VARCHAR(50) | NO | Project status | in_progress |
| `region` | VARCHAR(100) | YES | Geographic region | Doha |
| `data_source` | VARCHAR(50) | NO | Source system | ASHGHAL |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |

**Indexes**:
```sql
CREATE INDEX idx_infrastructure_sector ON infrastructure_projects(sector);
CREATE INDEX idx_infrastructure_status ON infrastructure_projects(status);
CREATE INDEX idx_infrastructure_dates ON infrastructure_projects(start_date, end_date);
```

### Skills and Training

#### `skills_inventory`

**Purpose**: Skills inventory and demand  
**Classification**: Internal  
**Update Frequency**: Quarterly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 78901 |
| `quarter` | VARCHAR(10) | NO | Quarter identifier | 2024-Q3 |
| `skill_name` | VARCHAR(200) | NO | Skill name | Python Programming |
| `skill_category` | VARCHAR(100) | NO | Skill category | Technical |
| `sector` | VARCHAR(100) | YES | Primary sector | technology |
| `demand_level` | VARCHAR(20) | YES | Demand level | high |
| `supply_level` | VARCHAR(20) | YES | Supply level | medium |
| `gap_score` | DECIMAL(5,2) | YES | Skill gap score (0-100) | 35.50 |
| `avg_wage_premium_pct` | DECIMAL(5,2) | YES | Wage premium (%) | 15.20 |
| `data_source` | VARCHAR(50) | NO | Source system | LMIS_PROD |
| `created_at` | TIMESTAMP | NO | Record creation time | 2024-10-15 14:30:00 |

**Indexes**:
```sql
CREATE INDEX idx_skills_quarter_category ON skills_inventory(quarter, skill_category);
CREATE INDEX idx_skills_sector ON skills_inventory(sector);
```

## Audit Tables

### Query Audit Log

#### `audit.query_log`

**Purpose**: Complete audit trail of all queries  
**Classification**: Confidential  
**Retention**: 2 years

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 123456 |
| `query_id` | VARCHAR(50) | NO | Unique query ID | q_2024_001234 |
| `user_id` | VARCHAR(255) | NO | User identifier | analyst_123 |
| `session_id` | VARCHAR(100) | YES | Session identifier | sess_abc123 |
| `question` | TEXT | NO | Original question | What is unemployment rate? |
| `query_type` | VARCHAR(20) | YES | Query classification | simple |
| `confidence_score` | DECIMAL(3,2) | YES | Confidence score (0-1) | 0.94 |
| `response_time_ms` | INTEGER | YES | Response time (ms) | 3200 |
| `agents_used` | TEXT[] | YES | Agents involved | {router,simple,verifier} |
| `data_sources` | JSONB | YES | Data sources accessed | {"tables": ["qtr_employment_stats"]} |
| `cache_hit` | BOOLEAN | YES | Cache hit flag | false |
| `error_message` | TEXT | YES | Error message (if failed) | NULL |
| `ip_address` | INET | YES | Client IP address | 192.168.1.100 |
| `user_agent` | TEXT | YES | Client user agent | Mozilla/5.0... |
| `created_at` | TIMESTAMP | NO | Query timestamp | 2024-11-12 05:03:00 |

**Indexes**:
```sql
CREATE INDEX idx_query_log_user_time ON audit.query_log(user_id, created_at DESC);
CREATE INDEX idx_query_log_query_id ON audit.query_log(query_id);
CREATE INDEX idx_query_log_type ON audit.query_log(query_type, created_at DESC);
```

### Data Access Log

#### `audit.data_access_log`

**Purpose**: Track all data table access  
**Classification**: Confidential  
**Retention**: 2 years

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 234567 |
| `user_id` | VARCHAR(255) | NO | User identifier | analyst_123 |
| `table_name` | VARCHAR(100) | NO | Table accessed | qtr_employment_stats |
| `row_ids` | BIGINT[] | YES | Row IDs accessed | {12345,12346} |
| `query_timestamp` | TIMESTAMP | NO | Query execution time | 2024-11-12 05:03:01 |
| `query_duration_ms` | INTEGER | YES | Query duration (ms) | 145 |
| `data_classification` | VARCHAR(20) | YES | Data classification | internal |
| `access_type` | VARCHAR(20) | YES | Access type | read |
| `query_id` | VARCHAR(50) | YES | Related query ID | q_2024_001234 |
| `created_at` | TIMESTAMP | NO | Log timestamp | 2024-11-12 05:03:01 |

**Indexes**:
```sql
CREATE INDEX idx_data_access_user_time ON audit.data_access_log(user_id, created_at DESC);
CREATE INDEX idx_data_access_table ON audit.data_access_log(table_name, created_at DESC);
CREATE INDEX idx_data_access_query ON audit.data_access_log(query_id);
```

### Security Audit Log

#### `audit.security_log`

**Purpose**: Security-relevant events  
**Classification**: Confidential  
**Retention**: 2 years

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | BIGSERIAL | NO | Primary key | 345678 |
| `user_id` | VARCHAR(255) | YES | User identifier | analyst_123 |
| `action` | VARCHAR(100) | NO | Action type | authentication_failed |
| `resource` | VARCHAR(255) | YES | Resource accessed | /api/v1/query |
| `result` | VARCHAR(20) | NO | Result | failure |
| `reason` | TEXT | YES | Failure reason | Invalid token |
| `ip_address` | INET | YES | Client IP | 192.168.1.100 |
| `user_agent` | TEXT | YES | Client user agent | Mozilla/5.0... |
| `details` | JSONB | YES | Additional details | {"attempts": 3} |
| `severity` | VARCHAR(20) | YES | Severity level | warning |
| `timestamp` | TIMESTAMP | NO | Event timestamp | 2024-11-12 05:03:00 |

**Indexes**:
```sql
CREATE INDEX idx_security_log_user ON audit.security_log(user_id, timestamp DESC);
CREATE INDEX idx_security_log_action ON audit.security_log(action, timestamp DESC);
CREATE INDEX idx_security_log_result ON audit.security_log(result, timestamp DESC);
```

## Materialized Views

### Sector Summary

#### `cache.mv_sector_summary`

**Purpose**: Pre-aggregated sector statistics  
**Refresh**: Hourly (automated)

```sql
CREATE MATERIALIZED VIEW cache.mv_sector_summary AS
SELECT 
    sector,
    quarter,
    SUM(employment_count) AS total_employment,
    AVG(unemployment_rate) AS avg_unemployment_rate,
    AVG(avg_wage_qar) AS avg_wage,
    COUNT(*) AS record_count,
    MAX(updated_at) AS last_updated
FROM qtr_employment_stats
GROUP BY sector, quarter;

CREATE INDEX idx_mv_sector_quarter ON cache.mv_sector_summary(sector, quarter);
```

### Quarterly Trends

#### `cache.mv_quarterly_trends`

**Purpose**: Quarterly trend analysis  
**Refresh**: Hourly (automated)

```sql
CREATE MATERIALIZED VIEW cache.mv_quarterly_trends AS
SELECT 
    quarter,
    SUM(employment_count) AS total_employment,
    AVG(unemployment_rate) AS avg_unemployment_rate,
    COUNT(DISTINCT sector) AS sector_count,
    MAX(updated_at) AS last_updated
FROM qtr_employment_stats
GROUP BY quarter
ORDER BY quarter DESC;

CREATE INDEX idx_mv_quarterly_quarter ON cache.mv_quarterly_trends(quarter DESC);
```

## Data Classifications

### Classification Levels

| Level | Description | Access | Examples |
|-------|-------------|--------|----------|
| **Public** | Publicly available data | All users | Aggregated statistics, published reports |
| **Internal** | Ministry internal use | Authenticated users | Detailed analytics, sector breakdowns |
| **Confidential** | Sensitive business data | Authorized users only | Individual employer data, audit logs |
| **Restricted** | Personally identifiable information | Not accessible via QNWIS | Individual worker records |

### Classification by Table

| Table | Classification | Reason |
|-------|----------------|--------|
| `qtr_employment_stats` | Internal | Detailed sector data |
| `wage_stats` | Internal | Wage information |
| `economic_indicators` | Public | Published statistics |
| `sector_trends` | Internal | Business intelligence |
| `infrastructure_projects` | Internal | Project details |
| `skills_inventory` | Internal | Skills analysis |
| `audit.query_log` | Confidential | User activity |
| `audit.data_access_log` | Confidential | Data access tracking |
| `audit.security_log` | Confidential | Security events |

## Data Quality

### Data Validation Rules

**Employment Statistics**:
- `employment_count >= 0`
- `unemployment_rate BETWEEN 0 AND 1`
- `quarter` matches format `YYYY-QN` where N in {1,2,3,4}
- `sector` in predefined sector list
- `data_source = 'LMIS_PROD'`

**Wage Statistics**:
- `avg_wage_qar > 0`
- `median_wage_qar <= avg_wage_qar * 1.5` (outlier check)
- `min_wage_qar <= median_wage_qar <= max_wage_qar`
- `sample_size >= 10` (minimum for statistical validity)

**Economic Indicators**:
- `indicator_value` non-null
- `indicator_name` in predefined list
- `unit` specified for all indicators

### Data Freshness

| Table | Update Frequency | Acceptable Lag | Current Status |
|-------|------------------|----------------|----------------|
| `qtr_employment_stats` | Quarterly | 30 days | ✅ Current |
| `wage_stats` | Quarterly | 30 days | ✅ Current |
| `economic_indicators` | Quarterly | 45 days | ✅ Current |
| `sector_trends` | Quarterly | 30 days | ✅ Current |
| `infrastructure_projects` | Monthly | 15 days | ✅ Current |
| `skills_inventory` | Quarterly | 45 days | ✅ Current |

## Privacy and Compliance

### Data Handling

**Aggregation Requirements**:
- Minimum 10 observations for any statistic
- No individual-level data exposed
- Geographic data aggregated to region level minimum

**Retention Policies**:
- LMIS data: Indefinite (historical analysis)
- Audit logs: 2 years minimum (compliance)
- Cache data: 90 days (performance)

**Access Controls**:
- Row-level security based on user role
- Data classification enforcement
- Audit logging for all access

### Compliance

**Standards**:
- Qatar National Cybersecurity Framework
- ISO 27001 (Information Security)
- Data Protection Guidelines (Qatar)

**Requirements**:
- Complete audit trail (2 years)
- Data classification enforcement
- Access control and monitoring
- Encryption at rest and in transit

## Database Maintenance

### Regular Tasks

**Daily**:
- Automated backups (02:00 UTC)
- Log rotation
- Cache refresh

**Weekly**:
- VACUUM ANALYZE on large tables
- Index maintenance
- Performance review

**Monthly**:
- Full database backup verification
- Capacity planning review
- Data quality audit

**Quarterly**:
- Schema review and optimization
- Archive old audit logs
- Security audit

### Performance Optimization

**Index Strategy**:
- All foreign keys indexed
- Composite indexes for common query patterns
- Covering indexes for frequent queries
- Regular index rebuild (REINDEX CONCURRENTLY)

**Partitioning** (future):
- Partition large tables by quarter
- Automatic partition creation
- Old partition archival

## Contact Information

**Database Administrator**: dba@mol.gov.qa  
**Data Governance**: data-governance@mol.gov.qa  
**Data Quality Issues**: data-quality@mol.gov.qa

---

**This document is authoritative for QNWIS database schema.**

**Last Review**: 2025-01-12  
**Next Review**: 2025-04-12 (Quarterly)
