# QNWIS Deployment Runbook (Production)

## Overview
This runbook describes how to build, configure, launch, monitor, back up, and roll back the QNWIS service. It assumes Docker or systemd on a single VM.

**Security:** Honors Step 34 (CSP, HTTPS, CSRF, RBAC, rate limiting) and uses env-only secrets.  
**Performance:** Preserves Step 35 metrics (`/metrics`) and connection pooling.

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

2. **Start the stack:**
   ```bash
   cd /ops/docker
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **Verify health:**
   ```bash
   curl http://HOST:8000/health/live    # → 200 (liveness)
   curl http://HOST:8000/health/ready   # → 200 (readiness)
   curl http://HOST:8000/metrics        # → Prometheus text format
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

### Image Rollback (Docker)

1. **Identify previous image:**
   ```bash
   docker images ghcr.io/your-org/qnwis
   ```

2. **Update .env with previous tag:**
   ```bash
   QNWIS_IMAGE=ghcr.io/your-org/qnwis:abc123
   ```

3. **Restart stack:**
   ```bash
   docker compose -f /ops/docker/docker-compose.prod.yml up -d
   ```

### Code Rollback (systemd)

1. **Checkout previous commit:**
   ```bash
   cd /opt/qnwis
   sudo -u qnwis git checkout <previous-commit-hash>
   ```

2. **Restart service:**
   ```bash
   sudo systemctl restart qnwis
   ```

---

## Observability

### Health Checks
- **Liveness:** `GET /health/live` → 200 (process alive)
- **Readiness:** `GET /health/ready` → 200 (dependencies ready)

### Metrics
- **Endpoint:** `GET /metrics` (Prometheus text format)
- **Scrape interval:** 15s recommended
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
workers = 4  # 2-4x CPU cores recommended
```

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
