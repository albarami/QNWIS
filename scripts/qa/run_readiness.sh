#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"
export TZ="UTC"
export LC_ALL="C"
export PYTHONHASHSEED="${PYTHONHASHSEED:-0}"

python3 "${ROOT}/src/qnwis/scripts/qa/readiness_gate.py" "$@"
