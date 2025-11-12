#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +'%Y%m%d_%H%M%S')"
OUTDIR="${1:-/app/backups}"
mkdir -p "$OUTDIR"
echo "[backup] Writing ${OUTDIR}/qnwis_${STAMP}.dump"
pg_dump --format=custom --file="${OUTDIR}/qnwis_${STAMP}.dump" "$DATABASE_URL"
# keep last 14 backups
ls -1t "$OUTDIR"/qnwis_*.dump | tail -n +15 | xargs -r rm -f
