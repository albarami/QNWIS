"""Centralized security configuration for QNWIS."""

from __future__ import annotations

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    # HTTP Security
    require_https: bool = True
    hsts_enabled: bool = True
    hsts_max_age: int = 63072000  # 2 years
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True

    # CSP (tight defaults; extend in env if needed)
    csp_default_src: str = "'self'"
    csp_script_src: str = "'self'"
    csp_style_src: str = "'self' 'unsafe-inline'"
    csp_img_src: str = "'self' data: blob:"
    csp_font_src: str = "'self' data:"
    csp_connect_src: str = "'self'"
    csp_frame_ancestors: str = "'none'"
    csp_enable_nonce: bool = True
    csp_nonce_length: int = 16  # urlsafe tokens are ~1.3x this size

    # CSRF
    csrf_cookie_name: str = "csrftoken"
    csrf_header_name: str = "X-CSRF-Token"
    csrf_secure: bool = True
    csrf_samesite: str = "strict"

    # Rate limiting
    rate_limit_window_sec: int = 60
    rate_limit_max_requests: int = 60

    # Redis (optional; fallback to memory if unset)
    redis_url: Optional[str] = None

    # Allowed origins (CORS if used)
    allowed_origins: List[str] = []

    # RBAC/JWT (roles often provided by an upstream gateway)
    roles_header: str = "X-User-Roles"
    https_localhost_allowlist: List[str] = ["127.0.0.1", "::1", "localhost", "testserver"]

    @field_validator("csrf_samesite")
    @classmethod
    def _samesite_valid(cls, v: str) -> str:
        """Validate CSRF SameSite attribute."""
        allowed = {"lax", "strict", "none"}
        if v.lower() not in allowed:
            raise ValueError("csrf_samesite must be one of: lax|strict|none")
        return v.lower()

    class Config:
        """Pydantic configuration."""

        env_prefix = "QNWIS_SECURITY_"


_settings_instance: Optional[SecuritySettings] = None


def get_security_settings() -> SecuritySettings:
    """
    Get singleton security settings instance.

    Returns:
        SecuritySettings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SecuritySettings()
    return _settings_instance


def override_security_settings(**kwargs) -> SecuritySettings:
    """
    Override cached security settings (primarily for testing).

    Args:
        **kwargs: SecuritySettings overrides

    Returns:
        New SecuritySettings instance
    """
    global _settings_instance
    _settings_instance = SecuritySettings(**kwargs)
    return _settings_instance


def reset_security_settings() -> None:
    """Reset cached settings so next access reloads from environment."""
    global _settings_instance
    _settings_instance = None
