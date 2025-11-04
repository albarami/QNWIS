# Deterministic Data Layer (DDL)

## Overview

The Deterministic Data Layer provides a unified, auditable interface for accessing data from multiple sources (CSV files, World Bank API) with built-in validation and provenance tracking.

## Architecture

```
src/qnwis/data/
├── deterministic/
│   ├── models.py      # Pydantic models for queries and results
│   ├── registry.py    # Query specification registry
│   └── access.py      # Main execution API
├── connectors/
│   ├── csv_catalog.py # CSV file connector
│   └── world_bank_det.py # World Bank API connector
├── validation/
│   └── number_verifier.py # Result validation logic
└── audit/
    └── audit_log.py   # File-based audit logging
```

## Core Components

### Query Models
- **QuerySpec**: Defines a data query with source, parameters, and constraints
- **QueryResult**: Contains data rows, provenance, freshness, and validation warnings
- **Provenance**: Tracks data source, location, and field metadata
- **Freshness**: Captures data currency information

### Query Registry
Loads YAML query specifications from `src/qnwis/data/queries/` and provides lookup by ID.

### Connectors
- **CSV Catalog**: Reads local CSV files with automatic delimiter detection and numeric casting
- **World Bank**: Integrates with World Bank API for economic indicators

### Validation
- Unit type validation
- Sum-to-one constraint checking for percentage data
- Extensible constraint framework

### Audit Logging
File-based NDJSON logging of all data access events with timestamps.

## Usage

```python
from src.qnwis.data.deterministic.registry import QueryRegistry
from src.qnwis.data.deterministic.access import execute

# Load queries
registry = QueryRegistry("src/qnwis/data/queries")
registry.load_all()

# Execute a query
result = execute("q_employment_share_by_gender_2023", registry)

# Access validated data
for row in result.rows:
    print(row.data)

# Check warnings
if result.warnings:
    print("Validation warnings:", result.warnings)
```

## Query Specification Format

```yaml
id: unique_query_id
title: Human-readable title
description: What this query returns
source: csv|world_bank
expected_unit: count|percent|qar|usd|index|unknown
params:
  # Source-specific parameters
  pattern: "*.csv"  # CSV files
  indicator: "SL.UEM.TOTL.ZS"  # World Bank
  countries: ["QAT","SAU"]  # World Bank
  year: 2023  # Optional year filter
constraints:
  sum_to_one: true  # For percentage data
```

## Testing

- Unit tests cover individual components
- Integration tests verify end-to-end functionality
- All tests mock external dependencies (no network calls)

## Integration Points

- **Agents**: Use `deterministic.access.execute()` for all data access
- **Database**: Audit events logged to PostgreSQL via migration scripts
- **Monitoring**: File-based audit logs for compliance and debugging
