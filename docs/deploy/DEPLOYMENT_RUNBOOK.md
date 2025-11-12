# QNWIS Deployment Runbook (Production)

## Overview
This runbook describes how to build, configure, launch, monitor, back up, and roll back the QNWIS service. It assumes Docker or systemd on a single VM.

**Security:** Honors Step 34 (CSP, HTTPS, CSRF, RBAC, rate limiting) and uses env-only secrets.  
**Performance:** Preserves Step 35 metrics (`/metrics`) and connection pooling.

## Environment Matrix

| Environment | Purpose / Scope | Traffic policy | Data / Secrets | Deployment mode | Rollback lever |
|-------------|-----------------|----------------|----------------|-----------------|----------------|
| `prod` | Live service for ministers | Public HTTPS via reverse proxy with HSTS + CSP | Real LMIS data; secrets in Vault or `.env` injected at boot | Docker Compose stack on hardened VM, rootless container runtime (`USER qnwis`) | Switch image digest, or promote standby from blue/green |
| `staging` | Pre-prod + drills | Restricted VPN; `/metrics` reachable only from Prometheus network | Synthetic pack with anonymized API keys | Docker Compose or systemd mirror | Re-run deploy with last known good tag |
| `drills` (`dr`, `ops`) | Continuity tests + backup verification | Private subnet only | Sanitized snapshots; throwaway secrets | Ephemeral VM + systemd | Destroy VM after test; keep snapshot manifest only |

Refer to [SECURE_ENV_REFERENCE.md](./SECURE_ENV_REFERENCE.md) for the full variable catalog (required/optional flags, defaults, and handling guidance).

## Prerequisites
- Docker 24+, Docker Compose v2
- A DNS name; TLS termination via reverse proxy or platform ingress
- Postgres 16, Redis 7 (compose provided)

---

## Build & Launch

### Using Docker Compose (Recommended)

1. **Copy environment template:**
   ```bash
   cp /ops/docker/.env.example /ops/docker/.env
   # Edit .env and set all secrets (POSTGRES_PASSWORD, CSRF_SECRET, SESSION_SECRET, etc.)
   ```

2. **Start the stack (non-root image + pinned digest):**
   ```bash
   cd /ops/docker
   docker compose -f docker-compose.prod.yml pull
   # Optional: export QNWIS_IMAGE=ghcr.io/albarami/qnwis@sha256:<digest>
   docker compose -f docker-compose.prod.yml up -d
   ```
   The runtime container already runs as `qnwis` (see `Dockerfile`). Pinning an image digest keeps blue/green releases deterministic.

3. **Verify health/observability (health is public, metrics restricted):**
   ```bash
   curl -fsS https://HOST/health/live
   curl -fsS https://HOST/health/ready
   # /metrics must only be called from the Prometheus network segment
   curl -fsS http://PROMETHEUS_NODE:8000/metrics
   ```
   `/health/*` returns minimal JSON (`{"status": ...}`) and is intentionally unauthenticated per `src/qnwis/utils/health.py`.

4. **Smoke test container after first deploy (ensures deterministic data + router path):**
   ```bash
   docker compose exec api pytest tests/system/test_api_readiness.py -k "test_router_smoke" --maxfail=1 -q
   ```

### Using systemd (Single VM)

1. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3.11 python3.11-venv postgresql-client redis-tools
   ```

2. **Deploy application:**
   ```bash
   sudo mkdir -p /opt/qnwis
   sudo cp -r . /opt/qnwis/
   sudo useradd -r -s /bin/false qnwis
   sudo chown -R qnwis:qnwis /opt/qnwis
   ```

3. **Configure environment:**
   ```bash
   sudo cp /opt/qnwis/ops/docker/.env.example /opt/qnwis/.env
   # Edit /opt/qnwis/.env with production secrets
   ```

4. **Install systemd unit:**
   ```bash
   sudo cp /opt/qnwis/ops/systemd/qnwis.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable qnwis
   sudo systemctl start qnwis
   ```

5. **Check status:**
   ```bash
   sudo systemctl status qnwis
   sudo journalctl -u qnwis -f
   ```

### Pre-stop hooks & graceful drains

- **Docker Compose:** `docker-compose.prod.yml` sets `stop_signal: SIGTERM` and `stop_grace_period: 45s`. Use `docker compose stop --timeout 45 api` (or `docker stop --time 45 qnwis-api-1`) so Gunicorn can finish in-flight requests (`graceful_timeout=30s` in `configs/gunicorn.conf.py`).
- **systemd:** The unit file now declares `KillSignal=SIGTERM`, `ExecStop=/bin/kill -s SIGTERM $MAINPID`, and `TimeoutStopSec=45`. `systemctl stop qnwis` will wait for Gunicorn to drain before sending SIGKILL.
- **Load balancer hint:** Before stopping, remove instance from rotation (e.g., flip DNS weight, or for Traefik toggle `traefik.enable=false`) to avoid 5xx bursts.

---

## Backups

### Automated Nightly Backups

Add to crontab (as root or qnwis user):
```bash
0 2 * * * /bin/bash -lc 'cd /app && scripts/pg_backup.sh /app/backups'
```

For Docker deployments:
```bash
0 2 * * * docker exec qnwis-api-1 /bin/bash -lc 'scripts/pg_backup.sh /app/backups'
```

### Manual Backup
```bash
# Docker
docker exec qnwis-api-1 /bin/bash -lc 'scripts/pg_backup.sh /app/backups'

# Systemd
cd /opt/qnwis && scripts/pg_backup.sh /opt/qnwis/backups
```

Backups are stored as `qnwis_YYYYmmdd_HHMMSS.dump` with automatic rotation (keeps last 14).

### Backup/restore verification (quarterly)
1. Export a disposable `DATABASE_URL` pointing at staging or a throwaway Postgres (can be a local container).
2. Run the scripts:
   ```bash
   scripts/pg_backup.sh /tmp/qnwis_backups
   scripts/pg_restore.sh /tmp/qnwis_backups/qnwis_<timestamp>.dump
   ```
3. Capture the stdout transcript and attach it to the release checklist. The scripts enforce the 14-file retention policy via `ls | tail -n +15 | xargs rm`, so confirm the directory never exceeds 14 files.
4. Destroy the temporary database when finished.

---

## Restore

### From Backup Snapshot

1. **Stop the application:**
   ```bash
   # Docker
   docker compose -f /ops/docker/docker-compose.prod.yml stop api
   
   # Systemd
   sudo systemctl stop qnwis
   ```

2. **Restore database:**
   ```bash
   # Docker
   docker exec qnwis-api-1 /bin/bash -lc 'scripts/pg_restore.sh /app/backups/qnwis_20251112_020000.dump'
   
   # Systemd
   cd /opt/qnwis && scripts/pg_restore.sh /opt/qnwis/backups/qnwis_20251112_020000.dump
   ```

3. **Restart application:**
   ```bash
   # Docker
   docker compose -f /ops/docker/docker-compose.prod.yml start api
   
   # Systemd
   sudo systemctl start qnwis
   ```

---

## Rollback

### Blue/Green container swap (Docker)

1. **Keep both stacks warm:** run production as `-p qnwis-blue` and pre-stage new release as `-p qnwis-green`.
   ```bash
   cd /ops/docker
   docker compose -p qnwis-green -f docker-compose.prod.yml pull
   docker compose -p qnwis-green -f docker-compose.prod.yml up -d
   ```
2. **Health + smoke:** hit `/health/ready` on the green stack (use the stack-specific reverse proxy label or temporary port) and run:
   ```bash
   docker compose -p qnwis-green exec api pytest tests/system/test_api_readiness.py -k "test_router_smoke" --maxfail=1 -q
   ```
3. **Flip traffic:** update the reverse proxy labels (`traefik.http.routers.qnwis.rule=...`) or DNS/CNAME to point at the green stack.
4. **Rollback:** if issues arise, flip the route back to blue; containers stay running so cutover is instant.

### Image/digest rollback (single stack)

1. **Find previous digest:**
   ```bash
   docker image ls ghcr.io/albarami/qnwis --digests | head
   ```
2. **Update Compose/.env:** set `QNWIS_IMAGE=ghcr.io/albarami/qnwis@sha256:<last-good>` and redeploy:
   ```bash
   docker compose -f /ops/docker/docker-compose.prod.yml up -d
   ```
3. **systemd:** edit `/opt/qnwis/.env` or `Environment=QNWIS_VERSION=...`, then `sudo systemctl restart qnwis`.
4. **Verification:** always re-run the smoke command plus `curl -fsS https://HOST/health/ready` before declaring success.

---

## Observability

### Health Checks
- **Liveness:** `GET /health/live` returns HTTP 200 as long as the process is up.
- **Readiness:** `GET /health/ready` returns HTTP 200 once DB + Redis connections succeed.

### Metrics
- **Endpoint:** `GET /metrics` (Prometheus text format)
- **Scrape interval:** 15s recommended
- **Network policy:** Only expose `/metrics` to the Prometheus subnet. For Compose, attach the Prometheus container via `metrics_net` (internal network) and omit any public port. For Kubernetes, add a `NetworkPolicy` that matches `app=qnwis` and allows ingress only from the Prometheus namespace. At the reverse proxy, deny `/metrics` for public listeners (e.g., `location /metrics { return 403; }`).
- **Key metrics:**
  - `qnwis_requests_total` - Total HTTP requests
  - `qnwis_latency_seconds` - Request latency histogram
  - `qnwis_active_requests` - Active requests gauge
  - `qnwis_db_latency_seconds` - Database operation latency
  - `qnwis_cache_hits_total` / `qnwis_cache_misses_total` - Cache performance

### Logs
- **Format:** Structured JSON (stdout/stderr)
- **Docker:** `docker compose logs -f api`
- **Systemd:** `journalctl -u qnwis -f`

---

## Security

### Secrets Management
- **Never commit secrets to Git**
- Use `.env` file (Docker) or systemd `EnvironmentFile`
- Rotate secrets quarterly minimum
- Required secrets:
  - `POSTGRES_PASSWORD` - Database password
  - `CSRF_SECRET` - CSRF token signing key (32+ chars)
  - `SESSION_SECRET` - Session signing key (32+ chars)

### TLS Termination
- Terminate TLS at reverse proxy (Traefik, Nginx, ALB)
- Enable HSTS headers (already configured in app)
- Application enforces secure headers via Step 34 middleware

### Rate Limiting
- Configured per-principal in Step 34
- Headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Adjust limits via `RATE_LIMIT_*` env vars

### Runtime Hardening
- Containers run as the non-root `qnwis` user (see `Dockerfile`) and only mount a log directory.
- CSP, HSTS, and other secure headers are enforced centrally in `src/qnwis/security/headers.py`; keep TLS termination at the proxy and forward `X-Forwarded-Proto`.
- `/health/*` responses remain constant-size JSON without internal details, so they can stay unauthenticated.
- `/metrics` should never traverse the public internet; rely on the network policies described earlier plus firewall rules (e.g., allowlist Prometheus subnet on SG).

## Deterministic Data Layer & SQL Safety

- All analytical queries are defined as YAML specs in `data/queries` and are loaded through `src/qnwis/data/deterministic/registry.py`. The runtime `QueryRegistry` computes a checksum so deployments can verify they are executing the intended dataset.
- Execution always flows through `src/qnwis/data/deterministic/access.py`, which fans into approved connectors (`csv_catalog`, `world_bank_det`) and runs validation (`number_verifier`). There is no code path for arbitrary SQL.
- Parameterized SQL enforcement: `tests/unit/test_query_registry_injection_guard.py` and `tests/unit/test_queries_yaml_loads.py` fail the build if a query introduces string interpolation. When writing migrations, stick to Alembic scripts or parameterized psycopg statements.
- Deterministic caches (`cache_access.py`) and materialization routines (`data/materialized/postgres.py`) only accept query text emitted by the registry. Never exec user-provided SQL in production shells.

## Reliability Notes

- `scripts/entrypoint.sh` blocks on Postgres readiness (30 attempts) before starting Gunicorn and runs `alembic upgrade head`, so migrations stay idempotent.
- Readiness checks call into the same health helper, ensuring `/health/ready` only flips true after DB + Redis connections are successful.
- Gunicorn (`configs/gunicorn.conf.py`) uses `workers=2`, `timeout=120`, `keepalive=5` to balance latency and memory. Increase workers to `min(2 * CPU, 8)` and keep `timeout <= 120` to avoid stuck connections.
- Compose/service units always restart (`restart: always`, `systemd Restart=always`) so the process comes back after a crash; combine with smoke tests to confirm functionality after restarts.

---

## Disaster Recovery

### Monthly DR Drill
1. **Restore latest backup to staging:**
   ```bash
   scripts/pg_restore.sh /app/backups/qnwis_latest.dump
   ```

2. **Run readiness tests:**
   ```bash
   pytest tests/system/test_readiness_gate.py -v
   ```

3. **Verify health endpoints:**
   ```bash
   curl http://staging:8000/health/ready
   ```

### RTO/RPO Targets
- **RTO (Recovery Time Objective):** 30 minutes
- **RPO (Recovery Point Objective):** 24 hours (nightly backups)

---

## Scaling

### Horizontal Scaling (Docker)
```bash
docker compose -f docker-compose.prod.yml up -d --scale api=3
```

### Vertical Scaling (Gunicorn Workers)
Edit `configs/gunicorn.conf.py`:
```python
workers = max(2, cpu_count * 2)  # keep <= 8 on 2 vCPU hosts
timeout = 120
graceful_timeout = 30
keepalive = 5
```
`keepalive=5s` prevents idle sockets from keeping load balancers busy, while `timeout=120s` + `graceful_timeout=30s` aligns with pre-stop hooks.

### Database Connection Pool
Adjust in `.env`:
```bash
PERF_POOL_MIN=10
PERF_POOL_MAX=50
PERF_POOL_TIMEOUT=30
```

---

## Troubleshooting

### Application Won't Start
1. Check logs: `docker compose logs api` or `journalctl -u qnwis`
2. Verify DATABASE_URL is correct
3. Ensure Postgres is reachable: `pg_isready -h postgres -U qnwis`
4. Check Redis: `redis-cli -h redis ping`

### High Latency
1. Check `/metrics` for `qnwis_latency_seconds` p95/p99
2. Review database query performance
3. Verify cache hit rate: `qnwis_cache_hits_total` / `qnwis_cache_misses_total`
4. Increase workers if CPU-bound

### Memory Issues
1. Monitor container memory: `docker stats`
2. Reduce workers or connection pool size
3. Check for memory leaks in logs

---

## Support Contacts

- **Technical Lead:** [Your Name]
- **On-Call:** [On-Call Rotation]
- **Escalation:** [Ministry of Labour IT Contact]

---

## Appendix: Environment Variables

See [SECURE_ENV_REFERENCE.md](./SECURE_ENV_REFERENCE.md) for complete environment variable documentation.
