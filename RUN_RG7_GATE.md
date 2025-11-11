# RG-7 Recovery Gate - Quick Start

## Overview

RG-7 validates the Disaster Recovery & Backups system with comprehensive checks:

- **dr_presence**: Modules, CLI, API routes discoverable
- **dr_integrity**: Backup→verify→restore round-trip with hash verification
- **dr_policy**: Retention, WORM, encryption enforcement
- **dr_targets**: Allowlist enforcement, no arbitrary FS traversal
- **dr_perf**: RPO ≤ 15 min, RTO ≤ 10 min for test corpus

## Prerequisites

```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Verify DR module imports
python -c "from src.qnwis.dr import models, snapshot, storage, crypto, restore, scheduler, verify"
```

## Running the Gate

### Option 1: Direct Python

```bash
python src/qnwis/scripts/qa/rg7_recovery_gate.py
```

### Option 2: Via pytest (recommended)

```bash
pytest tests/system/test_rg7_recovery_gate.py -v
```

## Expected Output

```
RG-7.1: DR Presence Check
  ✓ PASS: All DR modules and interfaces present

RG-7.2: DR Integrity Check (Round-trip)
  ✓ PASS: Round-trip successful (3 files)

RG-7.3: DR Policy Check
  ✓ PASS: Policies enforced (retention, WORM, encryption)

RG-7.4: DR Target Allowlist Check
  ✓ PASS: Target allowlist enforced, traversal prevented

RG-7.5: DR Performance Check (RPO/RTO)
  ✓ PASS: RPO 5.00s ≤ 900s, RTO 3.00s ≤ 600s

Generating artifacts...
  Report: docs/audit/rg7/rg7_report.json
  Summary: docs/audit/rg7/DR_SUMMARY.md
  Badge: docs/audit/badges/rg7_pass.svg

RG-7 Gate: ✓ PASS
```

## Artifacts Generated

1. **`docs/audit/rg7/rg7_report.json`** - Full JSON report with all check results
2. **`docs/audit/rg7/DR_SUMMARY.md`** - Human-readable summary
3. **`docs/audit/rg7/sample_manifest.json`** - Sample backup manifest
4. **`docs/audit/badges/rg7_pass.svg`** - Pass/fail badge

## Interpreting Results

### All Checks Pass

Gate returns exit code `0`. System is production-ready for DR operations.

### Any Check Fails

Gate returns exit code `1`. Review `rg7_report.json` for:

- `checks.<check_name>.error` - Specific failure reason
- `checks.<check_name>.status` - PASS/FAIL status

## Common Issues

### Import Errors

```
ModuleNotFoundError: No module named 'cryptography'
```

**Fix**: Install cryptography: `pip install cryptography`

### Performance Check Fails

```
RPO not met: 950.00s > 900s
```

**Fix**: Optimize backup process or adjust RPO target in gate script.

### WORM Violation

```
WORM violation: overwrite succeeded
```

**Fix**: Verify storage driver WORM implementation.

## Manual Testing

### Test Backup

```bash
# Create backup spec
python -m src.qnwis.cli.qnwis_dr plan \
  --spec-id test-001 \
  --tag manual-test \
  --storage-target local-test \
  --output backup_spec.json

# Execute backup
python -m src.qnwis.cli.qnwis_dr backup \
  --spec backup_spec.json \
  --storage-path ./dr_backups \
  --backend local
```

### Test Restore

```bash
# List snapshots
python -m src.qnwis.cli.qnwis_dr list \
  --storage-path ./dr_backups \
  --backend local

# Restore snapshot
python -m src.qnwis.cli.qnwis_dr restore \
  --snapshot-id <snapshot-id> \
  --storage-path ./dr_backups \
  --target-path ./restored \
  --backend local \
  --key-file key-<key-id>.json
```

### Test Verification

```bash
python -m src.qnwis.cli.qnwis_dr verify \
  --snapshot-id <snapshot-id> \
  --storage-path ./dr_backups \
  --backend local \
  --key-file key-<key-id>.json
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run RG-7 Recovery Gate
  run: |
    python src/qnwis/scripts/qa/rg7_recovery_gate.py
    if [ $? -ne 0 ]; then
      echo "RG-7 gate failed"
      exit 1
    fi
```

## Next Steps

After RG-7 passes:

1. Review `docs/ops/step32_dr_backups.md` for operational procedures
2. Configure production backup schedules
3. Set up monitoring for DR metrics (`/metrics` endpoint)
4. Test restore procedures in staging environment
5. Document runbooks for DR scenarios

## Support

For issues or questions:

- Check `STEP32_DR_IMPLEMENTATION_COMPLETE.md` for implementation details
- Review `docs/ops/step32_dr_backups.md` for operational guidance
- Examine test failures in `docs/audit/rg7/rg7_report.json`
