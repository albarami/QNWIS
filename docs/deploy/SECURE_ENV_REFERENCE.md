# QNWIS Environment Variables Reference

Complete reference for all production environment variables with secure defaults.

---

## Core Application

### `QNWIS_ENV`
- **Type:** String
- **Default:** `dev`
- **Production:** `prod`
- **Description:** Environment identifier (dev/staging/prod)

### `QNWIS_VERSION`
- **Type:** String
- **Default:** `dev`
- **Production:** Git commit hash or semantic version
- **Description:** Application version for tracking

### `HOST`
- **Type:** String
- **Default:** `0.0.0.0`
- **Description:** Bind address for HTTP server

### `PORT`
- **Type:** Integer
- **Default:** `8000`
- **Description:** HTTP server port

---

## Database

### `DATABASE_URL`
- **Type:** String (DSN)
- **Required:** Yes
- **Format:** `postgresql+psycopg://user:password@host:port/database`
- **Example:** `postgresql+psycopg://qnwis:secret@postgres:5432/qnwis`
- **Security:** Never log or expose this value

### `POSTGRES_DB`
- **Type:** String
- **Default:** `qnwis`
- **Description:** Database name (for Docker Compose postgres service)

### `POSTGRES_USER`
- **Type:** String
- **Default:** `qnwis`
- **Description:** Database user (for Docker Compose postgres service)

### `POSTGRES_PASSWORD`
- **Type:** String
- **Required:** Yes
- **Security:** Minimum 16 characters, alphanumeric + symbols
- **Description:** Database password (for Docker Compose postgres service)

---

## Cache

### `REDIS_URL`
- **Type:** String (URL)
- **Required:** Yes
- **Format:** `redis://host:port/db`
- **Example:** `redis://redis:6379/0`
- **Description:** Redis connection URL for caching and rate limiting

---

## Security (Step 34)

### `CSRF_SECRET`
- **Type:** String
- **Required:** Yes
- **Security:** Minimum 32 characters, cryptographically random
- **Generation:** `openssl rand -base64 32`
- **Description:** Secret key for CSRF token signing

### `SESSION_SECRET`
- **Type:** String
- **Required:** Yes
- **Security:** Minimum 32 characters, cryptographically random
- **Generation:** `openssl rand -base64 32`
- **Description:** Secret key for session signing

### `ALLOWED_ORIGINS`
- **Type:** String (comma-separated)
- **Default:** `*` (dev only)
- **Production:** `https://example.gov.qa,https://api.example.gov.qa`
- **Description:** CORS allowed origins (use specific domains in production)

### `QNWIS_BYPASS_AUTH`
- **Type:** Boolean
- **Default:** `false`
- **Production:** `false` (NEVER enable in production)
- **Description:** Bypass authentication (dev/testing only)

---

## Performance (Step 35)

### `PERF_POOL_MIN`
- **Type:** Integer
- **Default:** `5`
- **Description:** Minimum database connection pool size

### `PERF_POOL_MAX`
- **Type:** Integer
- **Default:** `30`
- **Description:** Maximum database connection pool size

### `PERF_POOL_TIMEOUT`
- **Type:** Integer
- **Default:** `30`
- **Description:** Connection pool timeout in seconds

---

## Caching & Freshness

### `QNWIS_DEFAULT_CACHE_TTL_S`
- **Type:** Integer
- **Default:** `3600` (1 hour)
- **Description:** Default cache TTL for queries

### `QNWIS_WARM_CACHE`
- **Type:** Boolean
- **Default:** `false`
- **Production:** `true` (recommended)
- **Description:** Enable cache warming on startup

### `QNWIS_WARM_QUERIES`
- **Type:** String (comma-separated)
- **Default:** `syn_employment_latest_total,syn_attrition_hotspots_latest,syn_qatarization_gap_latest`
- **Description:** Query IDs to warm on startup

### `QNWIS_WARM_MAX_WORKERS`
- **Type:** Integer
- **Default:** `4`
- **Description:** Max parallel workers for cache warming

---

## Compression

### `QNWIS_GZIP_MIN_BYTES`
- **Type:** Integer
- **Default:** `1024`
- **Description:** Minimum response size for gzip compression

### `QNWIS_ENABLE_BROTLI`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable Brotli compression (better than gzip)

### `QNWIS_BROTLI_QUALITY`
- **Type:** Integer (0-11)
- **Default:** `5`
- **Description:** Brotli compression quality (higher = better compression, slower)

### `QNWIS_BROTLI_MIN_BYTES`
- **Type:** Integer
- **Default:** `512`
- **Description:** Minimum response size for Brotli compression

---

## API Configuration

### `QNWIS_API_PREFIX`
- **Type:** String
- **Default:** `/api/v1`
- **Description:** API route prefix

### `QNWIS_ENABLE_DOCS`
- **Type:** Boolean
- **Default:** `false`
- **Production:** `false` (disable OpenAPI docs in production)
- **Description:** Enable Swagger/ReDoc documentation endpoints

---

## Logging

### `LOG_LEVEL`
- **Type:** String
- **Default:** `INFO`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Production:** `INFO` or `WARNING`
- **Description:** Application log level

---

## Rate Limiting

### `RATE_LIMIT_ENABLED`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable rate limiting

### `RATE_LIMIT_REQUESTS_PER_MINUTE`
- **Type:** Integer
- **Default:** `60`
- **Description:** Max requests per minute per principal

### `RATE_LIMIT_REQUESTS_PER_DAY`
- **Type:** Integer
- **Default:** `10000`
- **Description:** Max requests per day per principal

---

## Container-Specific

### `QNWIS_IMAGE`
- **Type:** String
- **Default:** `ghcr.io/your-org/qnwis:latest`
- **Description:** Docker image to deploy (Docker Compose only)

---

## Security Best Practices

### Secret Generation
Generate cryptographically secure secrets:
```bash
# CSRF_SECRET and SESSION_SECRET
openssl rand -base64 32

# POSTGRES_PASSWORD
openssl rand -base64 24
```

### Secret Rotation
- Rotate all secrets quarterly minimum
- Use secret management service (AWS Secrets Manager, HashiCorp Vault) for production
- Never commit secrets to Git
- Use `.env` files locally (gitignored)

### Environment File Template
```bash
# Copy and edit
cp /ops/docker/.env.example /ops/docker/.env
chmod 600 /ops/docker/.env  # Restrict permissions
```

---

## Validation Checklist

Before deploying to production, verify:

- [ ] `QNWIS_ENV=prod`
- [ ] `DATABASE_URL` uses strong password (16+ chars)
- [ ] `POSTGRES_PASSWORD` is unique and strong
- [ ] `CSRF_SECRET` is 32+ random characters
- [ ] `SESSION_SECRET` is 32+ random characters
- [ ] `ALLOWED_ORIGINS` lists only production domains (no wildcards)
- [ ] `QNWIS_BYPASS_AUTH=false`
- [ ] `QNWIS_ENABLE_DOCS=false`
- [ ] `LOG_LEVEL=INFO` or `WARNING`
- [ ] All secrets are stored securely (not in Git)
- [ ] `.env` file has restrictive permissions (600)

---

## Support

For questions about environment configuration, contact the technical lead or refer to [DEPLOYMENT_RUNBOOK.md](./DEPLOYMENT_RUNBOOK.md).
