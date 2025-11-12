#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Waiting for Postgres..."
until python - <<'PY'
import os,sys,time
import psycopg
url = os.environ.get("DATABASE_URL")
assert url, "DATABASE_URL not set"
for _ in range(30):
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                print("DB ready")
                sys.exit(0)
    except Exception as e:
        time.sleep(1)
print("DB not reachable", file=sys.stderr)
sys.exit(1)
PY
do sleep 1; done

# Run migrations if Alembic present
if [ -f "alembic.ini" ]; then
  echo "[entrypoint] Running alembic upgrade head..."
  alembic upgrade head
fi

echo "[entrypoint] Starting app..."
exec gunicorn -c configs/gunicorn.conf.py "src.qnwis.api.server:create_app()"
