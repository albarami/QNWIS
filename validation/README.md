# QNWIS Validation Harness

Deterministic, reproducible validation for end-to-end system testing.

## Quick Start

### Run Validation (Echo Mode - CI)

```bash
python scripts/validation/run_validation.py --mode echo
```

### Run Validation (HTTP Mode - Live System)

```bash
# Start QNWIS first
docker-compose up -d

# Run validation
python scripts/validation/run_validation.py --mode http --base-url http://localhost:8000
```

### Generate Reports

```bash
# Render case studies
python scripts/validation/render_case_studies.py

# Compare to baseline
python scripts/validation/compare_baseline.py
```

## Directory Structure

```
validation/
├── cases/              # 20 YAML test cases
├── results/            # Detailed JSON results (generated)
├── baselines/          # Consultant baseline performance
├── summary.csv         # Consolidated metrics (generated)
└── baseline_comparison.json  # Delta analysis (generated)
```

## Test Cases

- **Dashboard (2):** Real-time KPIs, <3s
- **Simple (5):** Single-source queries, <10s
- **Medium (8):** Multi-source analysis, <30s
- **Complex (5):** Multi-agent orchestration, <90s

## Success Criteria

✓ All 20 cases pass acceptance envelopes  
✓ 100% verification pass rate  
✓ Citation coverage ≥60%  
✓ Freshness indicators present  

## Documentation

- **Validation Plan:** `docs/validation/VALIDATION_PLAN.md`
- **Case Studies:** `docs/validation/CASE_STUDIES.md`
- **Demo Script:** `docs/demo/EXEC_DEMO_SCRIPT.md`

## CI Integration

```yaml
# .github/workflows/validation.yml
- name: Run Validation
  run: python scripts/validation/run_validation.py --mode echo
```

---

*Part of QNWIS Production Readiness Validation*
