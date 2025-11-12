# QNWIS Security Documentation

**Version:** 1.0.0  
**Classification:** Internal  
**Last Updated:** 2025-01-12

## Overview

This document describes the security controls implemented in QNWIS (Step 34 hardening) and secure coding practices for the development team.

## Security Architecture

### Defense in Depth

QNWIS implements multiple security layers:

```
┌─────────────────────────────────────────┐
│  1. Network Layer (TLS 1.2+, Firewall) │
├─────────────────────────────────────────┤
│  2. Application Layer (CSRF, CORS, CSP)│
├─────────────────────────────────────────┤
│  3. Authentication (JWT, SSO)           │
├─────────────────────────────────────────┤
│  4. Authorization (RBAC)                │
├─────────────────────────────────────────┤
│  5. Data Layer (Encryption, Audit)      │
├─────────────────────────────────────────┤
│  6. Monitoring (Alerts, Logging)        │
└─────────────────────────────────────────┘
```

## Transport Security

### HTTPS/TLS Configuration

**Requirements:**
- TLS 1.2 minimum (TLS 1.3 preferred)
- Strong cipher suites only
- Perfect Forward Secrecy (PFS)
- HTTP Strict Transport Security (HSTS)

**nginx Configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.qnwis.mol.gov.qa;

    # TLS configuration
    ssl_certificate /etc/ssl/certs/qnwis.crt;
    ssl_certificate_key /etc/ssl/private/qnwis.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS (31536000 seconds = 1 year)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # CSP
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.qnwis.mol.gov.qa;
    return 301 https://$server_name$request_uri;
}
```

**Verification:**

```bash
# Test TLS configuration
openssl s_client -connect api.qnwis.mol.gov.qa:443 -tls1_2
openssl s_client -connect api.qnwis.mol.gov.qa:443 -tls1_3

# Check certificate
echo | openssl s_client -servername api.qnwis.mol.gov.qa -connect api.qnwis.mol.gov.qa:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer

# Test HSTS
curl -I https://api.qnwis.mol.gov.qa | grep Strict-Transport-Security

# SSL Labs test
https://www.ssllabs.com/ssltest/analyze.html?d=api.qnwis.mol.gov.qa
```

## Authentication

### JWT Token-Based Authentication

**Token Structure:**

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "analyst_123",
    "email": "analyst@mol.gov.qa",
    "roles": ["analyst", "viewer"],
    "iat": 1699776000,
    "exp": 1699779600
  }
}
```

**Implementation:**

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.qnwis.config import settings

def create_access_token(user_id: str, roles: List[str]) -> str:
    """
    Create JWT access token.
    
    Token expires after 1 hour.
    Signed with HS256 using SECRET_KEY.
    """
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "user_id": user_id,
        "roles": roles,
        "iat": datetime.utcnow(),
        "exp": expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token.
    
    Raises JWTError if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

**Security Requirements:**

1. **Secret Key**: Minimum 32 characters, cryptographically random
2. **Token Lifetime**: 1 hour (configurable)
3. **Refresh Tokens**: Separate refresh token with 7-day lifetime
4. **Token Storage**: Never log tokens, store securely client-side
5. **Revocation**: Implement token blacklist for logout

### SSO Integration

QNWIS integrates with Ministry SSO (SAML 2.0):

```python
from fastapi import APIRouter, Depends
from src.qnwis.auth.sso import SAMLAuth

router = APIRouter()
saml_auth = SAMLAuth(
    entity_id="https://api.qnwis.mol.gov.qa",
    acs_url="https://api.qnwis.mol.gov.qa/auth/saml/acs",
    idp_metadata_url="https://sso.mol.gov.qa/metadata"
)

@router.get("/auth/saml/login")
async def saml_login():
    """Initiate SAML authentication."""
    return saml_auth.create_login_request()

@router.post("/auth/saml/acs")
async def saml_acs(saml_response: str):
    """Handle SAML assertion."""
    user_data = saml_auth.process_response(saml_response)
    token = create_access_token(user_data["user_id"], user_data["roles"])
    return {"access_token": token, "token_type": "bearer"}
```

## Authorization

### Role-Based Access Control (RBAC)

**Roles:**

| Role | Permissions | Use Case |
|------|-------------|----------|
| `viewer` | Read-only access to public data | General staff |
| `analyst` | Query system, view detailed data | Data analysts |
| `ops` | Access metrics, logs, admin functions | Operations team |
| `admin` | Full system access, user management | System administrators |

**Implementation:**

```python
from fastapi import Depends, HTTPException
from src.qnwis.auth.dependencies import get_current_user

def require_role(required_role: str):
    """
    Dependency to enforce role-based access.
    
    Usage:
        @app.get("/admin/users", dependencies=[Depends(require_role("admin"))])
    """
    def role_checker(user: User = Depends(get_current_user)):
        if required_role not in user.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    return role_checker

# Usage example
@router.get("/api/v1/admin/users", dependencies=[Depends(require_role("admin"))])
async def list_users():
    """Admin-only endpoint."""
    pass

@router.post("/api/v1/query", dependencies=[Depends(require_role("analyst"))])
async def submit_query(request: QueryRequest):
    """Analyst-only endpoint."""
    pass
```

### Data Access Control

**Data Classification:**

- **Public**: Aggregated statistics (no restrictions)
- **Internal**: Detailed analytics (requires `analyst` role)
- **Confidential**: Sensitive metrics (requires `admin` role)
- **Restricted**: PII (not accessible via QNWIS)

**Row-Level Security:**

```python
from sqlalchemy import select
from src.qnwis.models import Employment

def get_employment_data(user: User, sector: str):
    """
    Fetch employment data with row-level security.
    
    Filters data based on user's data access permissions.
    """
    query = select(Employment).where(Employment.sector == sector)
    
    # Apply data classification filter
    if "admin" not in user.roles:
        query = query.where(Employment.classification.in_(["public", "internal"]))
    
    # Apply organizational filter (if applicable)
    if user.organization:
        query = query.where(Employment.organization == user.organization)
    
    return db.execute(query).scalars().all()
```

## CSRF Protection

### Implementation

**Token Generation:**

```python
from fastapi import Request, HTTPException
from secrets import token_urlsafe

CSRF_TOKEN_LENGTH = 32
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

def generate_csrf_token() -> str:
    """Generate cryptographically secure CSRF token."""
    return token_urlsafe(CSRF_TOKEN_LENGTH)

def set_csrf_cookie(response: Response) -> str:
    """Set CSRF token in cookie."""
    token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="strict",
        max_age=3600  # 1 hour
    )
    return token
```

**Token Validation:**

```python
from fastapi import Request, HTTPException

async def verify_csrf_token(request: Request):
    """
    Verify CSRF token for state-changing requests.
    
    Compares token from cookie with token from header.
    """
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        
        if not cookie_token or not header_token:
            raise HTTPException(status_code=403, detail="CSRF token missing")
        
        if cookie_token != header_token:
            raise HTTPException(status_code=403, detail="CSRF token invalid")
```

**Middleware:**

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce CSRF protection."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for safe methods and health checks
        if request.method in ["GET", "HEAD", "OPTIONS"] or request.url.path == "/health":
            return await call_next(request)
        
        # Verify CSRF token
        await verify_csrf_token(request)
        
        return await call_next(request)

app = FastAPI()
app.add_middleware(CSRFMiddleware)
```

## CORS Configuration

**Allowed Origins:**

```python
from fastapi.middleware.cors import CORSMiddleware
from src.qnwis.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),  # Explicit whitelist
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=3600
)
```

**Configuration:**

```bash
# .env
ALLOWED_ORIGINS=https://app.qnwis.mol.gov.qa,https://dashboard.qnwis.mol.gov.qa
```

**Security Notes:**

- Never use `allow_origins=["*"]` in production
- Always specify explicit origin whitelist
- Use `allow_credentials=True` only with explicit origins
- Validate Origin header in application code

## Rate Limiting

### Implementation

**Redis-Based Rate Limiter:**

```python
from fastapi import Request, HTTPException
from redis import Redis
from src.qnwis.config import settings

redis_client = Redis.from_url(settings.REDIS_URL)

async def rate_limit(request: Request, limit: int = 100, window: int = 3600):
    """
    Rate limit requests per user per time window.
    
    Args:
        request: FastAPI request object
        limit: Maximum requests per window (default: 100)
        window: Time window in seconds (default: 3600 = 1 hour)
    """
    user_id = request.state.user.user_id
    key = f"rate_limit:user:{user_id}"
    
    # Increment counter
    current = redis_client.incr(key)
    
    # Set expiry on first request
    if current == 1:
        redis_client.expire(key, window)
    
    # Check limit
    if current > limit:
        ttl = redis_client.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + ttl),
                "Retry-After": str(ttl)
            }
        )
    
    # Add rate limit headers to response
    request.state.rate_limit_remaining = limit - current
    request.state.rate_limit_reset = int(time.time()) + redis_client.ttl(key)
```

**Middleware:**

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Apply rate limit
        await rate_limit(request)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)
        
        return response
```

**Configuration:**

```bash
# .env
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_BURST=10
```

### Metrics Endpoint Security

The `/metrics` endpoint exposes Prometheus-compatible system metrics for monitoring:

**Access Control:**
- Authentication required (JWT token or API key)
- Restricted to `ops` role only
- Internal network access only (blocked at firewall for external traffic)
- Rate limited: 10 requests per minute

**Exposed Metrics:**
```python
# System metrics (safe to expose internally)
- request_count_total
- request_duration_seconds
- active_connections
- cache_hit_rate
- query_execution_count

# Excluded metrics (sensitive data)
- database_connection_strings
- api_keys
- user_credentials
```

**nginx Configuration:**
```nginx
# Restrict /metrics to internal network
location /metrics {
    # Only allow from internal monitoring system
    allow 10.0.0.0/8;
    deny all;

    proxy_pass http://localhost:8000/metrics;
}
```

## Audit Logging

### Complete Activity Trail

**All security-relevant events are logged:**

```python
from src.qnwis.models.audit import AuditLog
from datetime import datetime

async def log_audit_event(
    user_id: str,
    action: str,
    resource: str,
    result: str,
    ip_address: str,
    user_agent: str,
    details: Dict[str, Any] = None
):
    """
    Log security audit event.
    
    Args:
        user_id: User performing action
        action: Action type (login, query, admin_action, etc.)
        resource: Resource accessed
        result: success or failure
        ip_address: Client IP
        user_agent: Client user agent
        details: Additional context
    """
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        result=result,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(audit_entry)
    await db.commit()
```

**Events Logged:**

- Authentication attempts (success/failure)
- Authorization failures
- Query submissions
- Data access
- Configuration changes
- Admin actions
- Rate limit violations
- CSRF token failures
- Suspicious activity

**Audit Log Schema:**

```sql
CREATE TABLE audit.security_log (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    result VARCHAR(20) NOT NULL,  -- success, failure, denied
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_security_log_user ON audit.security_log(user_id, timestamp);
CREATE INDEX idx_security_log_action ON audit.security_log(action, timestamp);
CREATE INDEX idx_security_log_result ON audit.security_log(result, timestamp);
```

**Retention:** 2 years minimum (compliance requirement)

## Secrets Management

### Environment Variables

**Never hardcode secrets:**

```python
# ❌ BAD
DATABASE_URL = "postgresql://user:password@localhost/db"
SECRET_KEY = "my-secret-key"

# ✅ GOOD
from src.qnwis.config import settings

DATABASE_URL = settings.DATABASE_URL
SECRET_KEY = settings.SECRET_KEY
```

### Configuration Management

**Production Secrets:**

```bash
# /etc/qnwis/.env (permissions: 600, owner: qnwis)
DATABASE_URL=postgresql://qnwis:${DB_PASSWORD}@db-primary.qnwis.mol.gov.qa/qnwis_prod
SECRET_KEY=${SECRET_KEY}
CSRF_SECRET=${CSRF_SECRET}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis-01.qnwis.mol.gov.qa:6379/0
```

**Secret Rotation:**

1. Generate new secret
2. Update environment variable
3. Restart application
4. Verify functionality
5. Document rotation in audit log

**Rotation Schedule:**
- SECRET_KEY: Every 90 days
- Database passwords: Every 90 days
- API keys: Every 180 days
- TLS certificates: Auto-renewed 30 days before expiry

## Input Validation

### SQL Injection Prevention

**Always use parameterized queries:**

```python
from sqlalchemy import select, text

# ❌ BAD - SQL Injection vulnerable
def get_user_bad(user_id: str):
    query = f"SELECT * FROM users WHERE user_id = '{user_id}'"
    return db.execute(text(query)).fetchone()

# ✅ GOOD - Parameterized query
def get_user_good(user_id: str):
    query = select(User).where(User.user_id == user_id)
    return db.execute(query).scalar_one_or_none()

# ✅ GOOD - Parameterized text query
def get_user_text(user_id: str):
    query = text("SELECT * FROM users WHERE user_id = :user_id")
    return db.execute(query, {"user_id": user_id}).fetchone()
```

### XSS Prevention

**Output encoding:**

```python
from markupsafe import escape

def render_user_input(user_input: str) -> str:
    """Escape user input to prevent XSS."""
    return escape(user_input)
```

**Content Security Policy (CSP):**

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:
```

### Request Validation

**Pydantic models for all inputs:**

```python
from pydantic import BaseModel, Field, validator
import re

class QueryRequest(BaseModel):
    """Validated query request."""
    
    question: str = Field(..., min_length=5, max_length=1000)
    user_id: str = Field(..., regex=r"^[a-z0-9_]+$")
    
    @validator("question")
    def sanitize_question(cls, v: str) -> str:
        """Remove potentially dangerous characters."""
        # Remove control characters
        v = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', v)
        return v.strip()
    
    @validator("user_id")
    def validate_user_id(cls, v: str) -> str:
        """Validate user ID format."""
        if len(v) < 3 or len(v) > 50:
            raise ValueError("user_id must be 3-50 characters")
        return v
```

## Security Monitoring

### Metrics to Monitor

```
# Failed authentication attempts
qnwis_auth_failures_total{reason="invalid_token"} > 10/min → Alert

# Rate limit violations
qnwis_rate_limit_violations_total > 50/hour → Alert

# CSRF failures
qnwis_csrf_failures_total > 5/min → Alert

# Suspicious query patterns
qnwis_suspicious_queries_total > 10/hour → Alert

# Unauthorized access attempts
qnwis_authorization_failures_total > 20/hour → Alert
```

### Alerting Rules

```yaml
# High authentication failure rate
- alert: HighAuthFailureRate
  expr: rate(qnwis_auth_failures_total[5m]) > 0.1
  for: 5m
  severity: warning
  annotations:
    summary: "High authentication failure rate detected"
    description: "{{ $value }} auth failures per second"

# Potential brute force attack
- alert: PotentialBruteForce
  expr: sum(rate(qnwis_auth_failures_total{reason="invalid_password"}[1m])) by (user_id) > 5
  for: 1m
  severity: critical
  annotations:
    summary: "Potential brute force attack on user {{ $labels.user_id }}"
```

## Incident Response

### Security Incident Classification

**SEV-1 (Critical):**
- Data breach or unauthorized access
- System compromise
- Active attack in progress

**SEV-2 (High):**
- Suspected breach attempt
- Vulnerability exploitation
- Privilege escalation

**SEV-3 (Medium):**
- Multiple failed authentication attempts
- Suspicious activity patterns
- Configuration issues

### Incident Response Workflow

```
1. DETECT (Automated alerts)
   ├─ Monitor security metrics
   ├─ Review audit logs
   └─ User reports

2. CONTAIN (< 15 minutes)
   ├─ Isolate affected systems
   ├─ Block malicious IPs
   ├─ Revoke compromised credentials
   └─ Enable additional logging

3. INVESTIGATE (< 1 hour)
   ├─ Identify attack vector
   ├─ Determine scope
   ├─ Collect evidence
   └─ Document findings

4. REMEDIATE (< 4 hours)
   ├─ Apply security patches
   ├─ Rotate secrets
   ├─ Update firewall rules
   └─ Verify fix

5. RECOVER (< 24 hours)
   ├─ Restore normal operations
   ├─ Monitor for recurrence
   └─ Update security controls

6. POST-MORTEM (< 48 hours)
   ├─ Write incident report
   ├─ Identify lessons learned
   ├─ Update runbooks
   └─ Implement preventive measures
```

## Compliance

### Data Protection

**GDPR/Data Privacy Principles:**

1. **Data Minimization**: Collect only necessary data
2. **Purpose Limitation**: Use data only for stated purpose
3. **Storage Limitation**: Retain data only as long as needed
4. **Integrity and Confidentiality**: Protect data with appropriate security

**Implementation:**

- PII is not stored in QNWIS (aggregated data only)
- Audit logs retained for 2 years (compliance requirement)
- Data classification enforced at database level
- Encryption at rest and in transit

### Security Standards

**Compliance Frameworks:**

- ISO 27001 (Information Security Management)
- NIST Cybersecurity Framework
- Qatar National Cybersecurity Framework

**Security Controls Implemented:**

- Access control (AC)
- Audit and accountability (AU)
- Identification and authentication (IA)
- System and communications protection (SC)
- System and information integrity (SI)

## Secure Coding Guidelines

### Checklist for Developers

- [ ] Never hardcode secrets or credentials
- [ ] Use parameterized queries (prevent SQL injection)
- [ ] Validate and sanitize all inputs
- [ ] Escape output (prevent XSS)
- [ ] Implement proper error handling (don't leak info)
- [ ] Use HTTPS for all external communications
- [ ] Implement rate limiting on public endpoints
- [ ] Log security-relevant events
- [ ] Follow principle of least privilege
- [ ] Keep dependencies updated (security patches)

### Code Review Security Checklist

- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection for state-changing operations
- [ ] Proper authentication/authorization
- [ ] Audit logging for sensitive operations
- [ ] Error messages don't leak sensitive info
- [ ] Rate limiting implemented
- [ ] Dependencies up to date

## Security Testing

### Automated Security Scans

```bash
# Dependency vulnerability scanning
pip-audit

# SAST (Static Application Security Testing)
bandit -r src/

# Secret scanning
trufflehog --regex --entropy=False .

# Container scanning
trivy image qnwis:latest
```

### Penetration Testing

**Annual penetration testing required:**

- External penetration test
- Internal vulnerability assessment
- Social engineering assessment
- Remediation verification

## Contact Information

**Security Team**: security@mol.gov.qa  
**Security Incidents**: security-incident@mol.gov.qa (24/7)  
**Vulnerability Reports**: security-vuln@mol.gov.qa

---

**This document contains security-sensitive information. Handle according to Ministry security policies.**

**Classification**: Internal  
**Last Review**: 2025-01-12  
**Next Review**: 2025-04-12 (Quarterly)
