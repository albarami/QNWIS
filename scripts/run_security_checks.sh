#!/usr/bin/env bash
# Security scanning script for QNWIS
set -euo pipefail

echo "========================================="
echo "QNWIS Security Scan"
echo "========================================="

echo ""
echo "== Bandit (Python Security Linter) =="
bandit -r src -ll -ii || {
    echo "WARNING: Bandit found security issues"
}

echo ""
echo "== Safety (Dependency Vulnerability Check) =="
safety check --full-report || {
    echo "WARNING: Safety found vulnerable dependencies"
}

echo ""
echo "== pip-audit (PyPI Vulnerability Scanner) =="
pip-audit || {
    echo "WARNING: pip-audit found vulnerable packages"
}

echo ""
echo "========================================="
echo "Security scan complete"
echo "========================================="
