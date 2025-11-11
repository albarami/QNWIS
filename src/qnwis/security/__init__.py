"""Security infrastructure for QNWIS API (JWT, API keys, RBAC, rate limiting)."""

from .audit import RequestAuditMiddleware, audit_log
from .auth import (
    ApiKeyRecord,
    ApiKeyStore,
    AuthProvider,
    JWTConfig,
    Principal,
    TokenPayload,
    create_jwt_token,
    decode_jwt,
    generate_api_key,
    verify_jwt_token,
)
from .csp import ensure_csp_nonce, get_csp_nonce
from .csrf import CSRFMiddleware
from .headers import SecurityHeadersMiddleware
from .https import StrictTransportMiddleware
from .range_guard import RangeHeaderGuardMiddleware
from .rate_limiter import RateLimiter as RateLimiterNew
from .rate_limiter import limiter, rate_limit
from .ratelimit import RateLimiter, RateLimitResult
from .rbac import require_roles
from .rbac_helpers import require_roles as require_roles_new
from .sanitizer import sanitize_html, sanitize_text
from .security_settings import (
    SecuritySettings,
    get_security_settings,
    override_security_settings,
    reset_security_settings,
)
from .validators import validate_date_yyyy_mm_dd, validate_safe_string, validate_uuid

__all__ = [
    # Legacy auth
    "ApiKeyRecord",
    "ApiKeyStore",
    "AuthProvider",
    "JWTConfig",
    "Principal",
    "TokenPayload",
    "create_jwt_token",
    "decode_jwt",
    "generate_api_key",
    "verify_jwt_token",
    "require_roles",
    "RateLimiter",
    "RateLimitResult",
    # New security hardening
    "SecuritySettings",
    "get_security_settings",
    "override_security_settings",
    "reset_security_settings",
    "SecurityHeadersMiddleware",
    "CSRFMiddleware",
    "StrictTransportMiddleware",
    "RangeHeaderGuardMiddleware",
    "RateLimiterNew",
    "limiter",
    "rate_limit",
    "require_roles_new",
    "sanitize_html",
    "sanitize_text",
    "ensure_csp_nonce",
    "get_csp_nonce",
    "audit_log",
    "RequestAuditMiddleware",
    "validate_uuid",
    "validate_date_yyyy_mm_dd",
    "validate_safe_string",
]
