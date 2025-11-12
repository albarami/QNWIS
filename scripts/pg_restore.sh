#!/usr/bin/env bash
set -euo pipefail
DUMP_PATH="${1:-}"
test -f "$DUMP_PATH" || { echo "Usage: $0 /path/to/qnwis_YYYYmmdd_HHMMSS.dump"; exit 1; }
echo "[restore] Restoring from ${DUMP_PATH}"
pg_restore --clean --if-exists --dbname="$DATABASE_URL" "$DUMP_PATH"
