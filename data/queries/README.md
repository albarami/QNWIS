# QNWIS Query Registry

This directory contains deterministic query definitions used by all agents.

## Query Definition Format

Each .yaml file defines a query with:
- `query_id`: Unique identifier (e.g., "unemployment_by_gender")
- `description`: Human-readable description
- `dataset`: Data source (LMIS, GCC_STAT, WORLD_BANK, VISION_2030)
- `sql`: SQL query template with named parameters (`:param_name`)
- `parameters`: List of allowed parameters with types/defaults
- `output_schema`: Expected output columns and types
- `cache_ttl`: Cache time-to-live in seconds
- `freshness_sla`: Maximum age before data considered stale
- `access_level`: Required permission level (public, restricted, confidential)
- `tags`: Optional list of tags for categorization

## Example Query

```yaml
query_id: unemployment_rate_latest
description: Most recent unemployment rate for Qatar nationals
dataset: LMIS
sql: |
  SELECT
    month,
    gender,
    education_level,
    COUNT(CASE WHEN status = 'unemployed' THEN 1 END)::float /
      NULLIF(COUNT(*), 0) * 100 as unemployment_rate,
    COUNT(*) as sample_size
  FROM employment_records
  WHERE nationality = 'Qatari'
    AND month = (SELECT MAX(month) FROM employment_records)
  GROUP BY month, gender, education_level
  ORDER BY month DESC, gender, education_level
output_schema:
  - {name: month, type: date}
  - {name: gender, type: string}
  - {name: education_level, type: string}
  - {name: unemployment_rate, type: float}
  - {name: sample_size, type: integer}
cache_ttl: 3600  # 1 hour
freshness_sla: 86400  # 24 hours
access_level: public
tags: [unemployment, demographics]
```

## Available Queries

See individual YAML files for complete specifications.

## Usage

Queries are loaded by the `QueryRegistry` class and executed via the `DataClient`:

```python
from qnwis.data.deterministic.registry import QueryRegistry

registry = QueryRegistry()
query_def = registry.get("unemployment_rate_latest")
result = registry.run("unemployment_rate_latest", params={}, engine=engine)
```
