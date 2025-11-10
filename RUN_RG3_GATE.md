# Running RG-3 Operations Gate

## Quick Test Commands

Run these commands from the project root to validate the Alert Center implementation:

### 1. Test Imports
```powershell
python -c "from src.qnwis.alerts import AlertEngine, AlertRegistry, AlertReportRenderer, AlertRule; print('✓ Imports OK')"
python -c "from src.qnwis.agents import AlertCenterAgent; print('✓ Agent import OK')"
```

### 2. Validate Sample Rules
```powershell
python -m src.qnwis.cli.qnwis_alerts validate --rules-file examples/alert_rules_sample.yaml
```

Expected output:
```
✅ Validation PASSED: 5 rules loaded successfully
```

### 3. Run Unit Tests
```powershell
# Test alert modules
pytest tests/unit/alerts/ -v

# Test agent
pytest tests/unit/agents/test_alert_center.py -v

# Test integration
pytest tests/integration/agents/test_alert_flow.py -v

# Performance benchmarks
pytest tests/unit/alerts/test_microbench.py -v
```

### 4. Run RG-3 Operations Gate
```powershell
python src/qnwis/scripts/qa/ops_gate.py
```

Expected output:
```
==================================================================
RG-3 OPERATIONS GATE - Alert Center Validation
==================================================================

Running gate: alerts_completeness...
  ✅ PASS: All modules loaded and rules validated

Running gate: alerts_accuracy...
  ✅ PASS: All accuracy tests passed

Running gate: alerts_performance...
  ✅ PASS: Performance target met: p95=XX.XXms

Running gate: alerts_audit...
  ✅ PASS: Audit pack generation successful

==================================================================
🎉 RG-3 OPERATIONS GATE: PASSED
==================================================================

Results exported to: docs/audit/alerts/rg3_ops_gate_results.json
```

### 5. Check Test Coverage
```powershell
pytest tests/unit/alerts/ tests/unit/agents/test_alert_center.py --cov=src/qnwis/alerts --cov=src/qnwis/agents/alert_center --cov-report=term-missing
```

Expected: ≥90% coverage

## Manual Testing

### Test CLI Commands

```powershell
# Show status
python -m src.qnwis.cli.qnwis_alerts status --rules-file examples/alert_rules_sample.yaml

# Run evaluation (will need DataClient setup)
python -m src.qnwis.cli.qnwis_alerts run --rules-file examples/alert_rules_sample.yaml

# Silence a rule
python -m src.qnwis.cli.qnwis_alerts silence --rules-file examples/alert_rules_sample.yaml --rule-id retention_drop_construction --until 2025-12-31
```

## Troubleshooting

### If imports fail
- Ensure you're in the project root: `d:\lmis_int`
- Check Python path: `$env:PYTHONPATH = "d:\lmis_int"`

### If pytest not found
```powershell
pip install pytest pytest-cov pydantic pyyaml
```

### If RG-3 gate fails
Check individual components:
1. Module imports
2. Rule validation
3. Engine evaluation
4. Report generation

## Success Criteria

All of the following must pass:
- ✅ All imports work
- ✅ Sample rules validate
- ✅ Unit tests pass (115 tests)
- ✅ Coverage ≥90%
- ✅ RG-3 gate all 4 checks PASS
- ✅ Performance: p95 < 150ms for 200 rules
