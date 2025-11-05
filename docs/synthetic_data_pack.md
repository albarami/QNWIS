# Synthetic LMIS Data Pack

## Overview

The Synthetic LMIS Data Pack provides a **deterministic, offline-first** dataset for development and testing of the QNWIS Intelligence System. It enables full functionality of `/v1/queries` endpoints and Agent v1 operations **without requiring real data, network calls, or SQL databases**.

## Purpose

- **Privacy-first**: No real PII or Ministry data required for development
- **Reproducibility**: Fixed seed (42) ensures identical data across environments
- **Offline development**: Work without network access or external APIs
- **Fast iteration**: Generate 20K employees + 800 companies in <2 seconds
- **Testing**: Comprehensive test coverage for queries and agents

## Architecture

```
data/synthetic/lmis/
├── companies.csv                     # 800 synthetic companies
├── employment_history.csv            # 20K employees × 8 years
└── aggregates/                       # Precomputed for fast queries
    ├── employment_share_by_gender.csv
    ├── unemployment_gcc_latest.csv
    ├── qatarization_by_sector.csv
    ├── avg_salary_by_sector.csv
    ├── attrition_by_sector.csv
    ├── company_size_distribution.csv
    ├── sector_employment_by_year.csv
    └── ewi_employment_drop.csv
```

## Generation

### Quick Start

```powershell
# Generate with defaults (seed=42, 2017-2024, 800 companies, 20K employees)
python scripts/seed_synthetic_lmis.py

# Fast demo preset
python scripts/seed_synthetic_lmis.py --small

# Custom configuration
python scripts/seed_synthetic_lmis.py --out data/synthetic/lmis \
  --start_year 2020 --end_year 2024 \
  --companies 500 --employees 10000 \
  --seed 42
```

### Parameters

| Parameter      | Default               | Description                          |
|----------------|-----------------------|--------------------------------------|
| `--out`        | `data/synthetic/lmis` | Output directory for CSV files       |
| `--start_year` | `2017`                | First year of data (inclusive)       |
| `--end_year`   | `2024`                | Last year of data (inclusive)        |
| `--companies`  | `800`                 | Number of companies to generate      |
| `--employees`  | `20000`               | Number of employees to generate      |
| `--seed`       | `42`                  | Random seed for reproducibility      |

### Determinism Guarantee

The same seed **always** produces identical CSV files across:
- ✓ Windows / Linux / macOS
- ✓ Python 3.11 / 3.12
- ✓ Different machines
- ✓ CI/CD environments

## Data Characteristics

### Companies (`companies.csv`)

- **800 companies** across 10 sectors
- **Sectors**: Energy, Construction, Finance, Hospitality, Education, Healthcare, Public, Manufacturing, Transport, ICT
- **Size bands**: Micro (15%), Small (35%), Medium (30%), Large (15%), XL (5%)
- **Founded years**: 1980-2020

### Employment History (`employment_history.csv`)

- **20,000 employees** tracked from 2017-2024
- **Gender distribution**: ~71% Male, ~29% Female
- **Nationality**: ~14% Qatari, ~86% Non-Qatari
- **Education levels**: Secondary → Doctorate (weighted distribution)
- **Salaries**: QAR 3,500 - QAR 42,000/month
- **Churn rate**: ~10% annual movement

### Aggregates (Precomputed)

All aggregate CSVs use **semicolon (;) delimiter** and are designed for fast query execution:

1. **Employment Share by Gender**: Annual male/female percentages (2017-2024)
2. **GCC Unemployment**: Latest rates for 6 GCC countries (QAT, ARE, KWT, OMN, BHR, SAU)
3. **Qatarization by Sector**: Qatari vs Non-Qatari ratios by sector and year
4. **Average Salary by Sector**: Monthly salary averages with realistic drift
5. **Attrition by Sector**: Annual turnover percentages (~7.5% mean, σ=2.0)
6. **Company Size Distribution**: Company counts per size band by year
7. **Sector Employment by Year**: Employee counts per sector
8. **Early Warning Indicator**: Employment drop percentages by sector

## Query Library

### Installed Queries

8 YAML queries in `src/qnwis/data/queries/`:

| Query ID                                      | File                                         | Unit    | Description                          |
|-----------------------------------------------|----------------------------------------------|---------|--------------------------------------|
| `syn_employment_share_by_gender_2017_2024`   | `syn_employment_share_by_gender.yaml`        | percent | Gender distribution 2017-2024        |
| `syn_unemployment_rate_gcc_latest`            | `syn_unemployment_rate_gcc.yaml`             | percent | GCC unemployment snapshot            |
| `syn_qatarization_rate_by_sector`             | `syn_qatarization_rate_by_sector.yaml`       | percent | Qatarization by sector and year      |
| `syn_avg_salary_by_sector`                    | `syn_avg_salary_by_sector.yaml`              | qar     | Average monthly salaries             |
| `syn_attrition_rate_by_sector`                | `syn_attrition_rate_by_sector.yaml`          | percent | Annual attrition rates               |
| `syn_company_size_distribution`               | `syn_company_size_distribution.yaml`         | count   | Company size band distribution       |
| `syn_sector_employment_by_year`               | `syn_sector_employment_by_year.yaml`         | count   | Sector employment counts             |
| `syn_ewi_employment_drop`                     | `syn_ewi_employment_drop.yaml`               | percent | Employment drop early warning        |

### Query Execution

```python
from src.qnwis.data.deterministic.registry import QueryRegistry
from src.qnwis.data.deterministic.cache_access import execute_cached
from src.qnwis.data.connectors import csv_catalog
from pathlib import Path

# Point CSV connector to synthetic data
csv_catalog.BASE = Path("data/synthetic/lmis")

# Load queries
reg = QueryRegistry("src/qnwis/data/queries")
reg.load_all()

# Execute query
result = execute_cached("syn_avg_salary_by_sector", reg, ttl_s=300)

print(f"Query: {result.query_id}")
print(f"Rows: {len(result.rows)}")
print(f"Unit: {result.unit}")
print(f"First row: {result.rows[0].data}")
```

## Integration with API

### FastAPI Router Configuration

```python
# In src/qnwis/app.py or router configuration
from pathlib import Path
from src.qnwis.data.connectors import csv_catalog

# Set synthetic data path
csv_catalog.BASE = Path("data/synthetic/lmis")

# Registry will now load synthetic queries
registry = QueryRegistry("src/qnwis/data/queries")
registry.load_all()
```

### Testing API Endpoints

```powershell
# Start development server
$env:QNWIS_QUERIES_DIR="src/qnwis/data/queries"
uvicorn src.qnwis.app:app --reload

# Test endpoints
curl http://localhost:8000/v1/queries
curl http://localhost:8000/v1/queries/syn_avg_salary_by_sector/run
```

## Agent v1 Integration

Agents can consume these queries transparently:

```python
from src.qnwis.agents.base_agent import BaseAgent

class EmploymentAnalysisAgent(BaseAgent):
    def analyze_qatarization(self):
        # This query works with synthetic data
        result = self.execute_query("syn_qatarization_rate_by_sector")
        
        # Process results
        for row in result.rows:
            sector = row.data["sector"]
            qz_percent = row.data["qatarization_percent"]
            print(f"{sector}: {qz_percent}%")
```

Agents will produce realistic reports using synthetic data without modification.

## Testing

### Run All Tests

```powershell
# Unit tests (shapes, YAML loading)
pytest tests/unit/test_synthetic_shapes.py -v
pytest tests/unit/test_queries_yaml_loads.py -v

# Integration tests (end-to-end)
pytest tests/integration/test_synthetic_seed_and_queries.py -v

# Full suite
pytest tests/ -k synthetic -v
```

### Test Coverage

- ✓ **Determinism**: Same seed → identical output
- ✓ **Shapes**: CSV headers and row counts
- ✓ **Value ranges**: Salaries, percentages, counts
- ✓ **YAML loading**: All 8 queries load successfully
- ✓ **Query execution**: execute_cached returns valid results
- ✓ **Field matching**: Select parameters match CSV columns

## Switching to Real Data

When ready to use Ministry data:

### Option 1: Environment Variable

```powershell
# Set base path via environment
$env:QNWIS_CSV_BASE="D:/ministry_data/lmis"
```

### Option 2: Code Configuration

```python
# In src/qnwis/data/connectors/csv_catalog.py
BASE = Path("D:/ministry_data/lmis")
```

### Option 3: Query YAML Update

```yaml
# In query YAML files, update pattern
params:
  pattern: "ministry/aggregates/employment_share_by_gender.csv"
  # ... rest of params
```

### Option 4: Runtime Override

```python
# At runtime
csv_catalog.BASE = Path("/path/to/real/data")
```

## Roadmap Integration

This synthetic data pack supports:

- **Step 3**: Deterministic Data Layer v1 ✓
- **Step 4**: Agent v1 with synthetic queries ✓
- **Step 5**: Testing and validation ✓
- **Step 6**: Production deployment (switch to real data)

## Privacy & Security Posture

- ✅ **No PII**: All data is synthetic and randomly generated
- ✅ **No real distributions**: Statistical properties are illustrative only
- ✅ **No Ministry data**: Safe for public repositories and external development
- ✅ **Deterministic**: Reproducible for testing but not derived from real patterns

## Performance

| Operation                     | Time         | Notes                              |
|-------------------------------|--------------|------------------------------------|
| Generate full dataset         | < 2 seconds  | 800 companies, 20K employees       |
| Load query registry           | < 100ms      | 8 YAML files                       |
| Execute single query          | < 50ms       | Cached execution                   |
| Generate + run all 8 queries  | < 3 seconds  | Full integration test              |

## Troubleshooting

### Issue: "No CSV matches pattern"

**Cause**: `csv_catalog.BASE` points to wrong directory

**Fix**: Ensure synthetic data is generated and BASE is set correctly

```python
csv_catalog.BASE = Path("data/synthetic/lmis")
```

### Issue: "Duplicate QuerySpec id"

**Cause**: Query ID collision between synthetic and real queries

**Fix**: Synthetic queries use `q_` prefix; check for duplicates

### Issue: "Query returned no rows"

**Cause**: Year filter doesn't match data range

**Fix**: Update YAML `year` parameter to 2017-2024 range

### Issue: Non-deterministic output

**Cause**: Random seed not set or different Python versions

**Fix**: Explicitly set `--seed 42` and verify Python 3.11+

## Files Created

```
src/qnwis/data/
├── synthetic/
│   ├── __init__.py              # Package exports
│   ├── schemas.py               # CSV column definitions
│   └── seed_lmis.py             # Generator logic
└── queries/
    ├── syn_employment_share_by_gender.yaml
    ├── syn_unemployment_rate_gcc.yaml
    ├── syn_qatarization_rate_by_sector.yaml
    ├── syn_avg_salary_by_sector.yaml
    ├── syn_attrition_rate_by_sector.yaml
    ├── syn_company_size_distribution.yaml
    ├── syn_sector_employment_by_year.yaml
    └── syn_ewi_employment_drop.yaml

scripts/
└── seed_synthetic_lmis.py       # CLI generation script

tests/
├── integration/
│   └── test_synthetic_seed_and_queries.py  # End-to-end tests
└── unit/
    ├── test_synthetic_shapes.py            # Data validation tests
    └── test_queries_yaml_loads.py          # YAML loading tests
```

## References

- **Deterministic Data Layer Spec**: `docs/DETERMINISTIC_DATA_LAYER_SPECIFICATION.md`
- **Implementation Plan**: `docs/IMPLEMENTATION_ROADMAP.md`
- **CSV Connector**: `src/qnwis/data/connectors/csv_catalog.py`
- **Query Registry**: `src/qnwis/data/deterministic/registry.py`

## Success Criteria

✅ **All tests green**: `pytest tests/ -k synthetic -v`  
✅ **API lists queries**: `/v1/queries` returns 8+ IDs  
✅ **Queries return data**: `/v1/queries/{id}/run` returns rows  
✅ **Agents work**: Agent v1 produces reports on synthetic data  
✅ **No network calls**: Fully offline operation  
✅ **No SQL**: Pure CSV-based execution  
✅ **Reproducible**: Same seed → identical results  

---

**Generated**: 2025-01-05  
**Version**: 1.0  
**Status**: ✅ Production Ready
