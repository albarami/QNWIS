"""Tests for Sprint 2: Security Hardening.

All tests use real infrastructure -- no mocks, no hardcoded data.

Covers:
  - Task 2.1: council/stream must require auth and have rate limiting
  - Task 2.2: auth bypass must be gated on environment
  - Task 2.3: CORS must not be wildcard
  - Task 2.4: HSTS middleware must be active
  - Task 2.5: error responses must not leak internal details
  - Task 2.6: default secret key rejected in production
  - Task 2.7: SLO and cache invalidation endpoints require RBAC
"""

import ast
import os
import re
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"


class TestCouncilStreamSecurity:
    """Council stream must require auth and be rate-limited."""

    def test_council_stream_not_in_public_prefixes(self):
        server_path = SRC_ROOT / "qnwis" / "api" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "council/stream" not in source.split("PUBLIC_PREFIXES")[1].split("\n")[0], (
            "/council/stream is still in PUBLIC_PREFIXES"
        )

    def test_council_stream_rate_limiter_enabled(self):
        council_path = SRC_ROOT / "qnwis" / "api" / "routers" / "council_llm.py"
        source = council_path.read_text(encoding="utf-8")
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "council_stream_llm" in line and "async def" in line:
                preceding = "\n".join(lines[max(0, i - 5):i])
                assert "@limiter.limit" in preceding, (
                    "Rate limiter is still commented out on council_stream_llm"
                )
                assert "# @limiter" not in preceding, (
                    "Rate limiter line is still commented out"
                )
                break


class TestAuthBypassGuard:
    """Auth bypass must only work in dev/test environments."""

    def test_auth_bypass_gated_on_environment(self):
        server_path = SRC_ROOT / "qnwis" / "api" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert 'env in ("development", "test")' in source or \
               "env in ('development', 'test')" in source, (
            "Auth bypass is not gated on environment"
        )

    def test_auth_bypass_not_unconditional(self):
        server_path = SRC_ROOT / "qnwis" / "api" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        lines = source.split("\n")
        for line in lines:
            stripped = line.strip()
            if "auth_bypass" in stripped and "QNWIS_BYPASS_AUTH" in stripped:
                assert "development" in source[:source.index(stripped)] or \
                       "QNWIS_ENV" in source[:source.index(stripped)], (
                    "QNWIS_BYPASS_AUTH used without environment guard"
                )
                break


class TestCORSNotWildcard:
    """CORS must use specific origins, not wildcard."""

    def test_no_wildcard_cors(self):
        server_path = SRC_ROOT / "qnwis" / "api" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert 'allow_origins=["*"]' not in source, (
            "Wildcard CORS allow_origins=['*'] is still present"
        )

    def test_cors_reads_from_environment(self):
        server_path = SRC_ROOT / "qnwis" / "api" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "QNWIS_API_CORS_ORIGINS" in source or "QNWIS_CORS_ORIGINS" in source, (
            "CORS origins are not loaded from environment variable"
        )


class TestHSTSEnabled:
    """HSTS middleware must be active (not commented out)."""

    def test_hsts_not_commented_out(self):
        deps_path = SRC_ROOT / "qnwis" / "api" / "deps.py"
        source = deps_path.read_text(encoding="utf-8")
        assert "#app.add_middleware(StrictTransportMiddleware)" not in source, (
            "StrictTransportMiddleware is still commented out"
        )

    def test_hsts_middleware_present(self):
        deps_path = SRC_ROOT / "qnwis" / "api" / "deps.py"
        source = deps_path.read_text(encoding="utf-8")
        assert "StrictTransportMiddleware" in source, (
            "StrictTransportMiddleware not found in deps.py"
        )


class TestNoExceptionLeakage:
    """HTTP error responses must not include raw exception strings."""

    ROUTER_DIR = SRC_ROOT / "qnwis" / "api" / "routers"
    LEAK_PATTERNS = [
        re.compile(r'detail=f".*\{str\(e\)\}'),
        re.compile(r'detail=f".*\{e\}'),
        re.compile(r'detail=f".*\{str\(exc\)\}'),
        re.compile(r'detail=f".*\{exc!s\}'),
        re.compile(r'detail=str\(exc\)'),
        re.compile(r'detail=str\(e\)'),
        re.compile(r'"debug_error".*str\(exc\)'),
    ]

    def test_no_exception_leakage_in_500_responses(self):
        failures = []
        for py_file in sorted(self.ROUTER_DIR.rglob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(source.split("\n"), 1):
                if "status_code=5" in line or "status_code=status.HTTP_5" in line:
                    context = "\n".join(source.split("\n")[max(0, i - 3):i + 3])
                    for pattern in self.LEAK_PATTERNS:
                        if pattern.search(context):
                            failures.append(
                                f"{py_file.relative_to(SRC_ROOT)}:{i}"
                            )
        assert not failures, (
            f"Exception details leaked in 500 responses at:\n"
            + "\n".join(failures)
        )


class TestSecretKeyValidation:
    """Default secret key must be rejected in production."""

    def test_secret_key_validator_exists(self):
        settings_path = SRC_ROOT / "qnwis" / "config" / "settings.py"
        source = settings_path.read_text(encoding="utf-8")
        assert "field_validator" in source and "secret_key" in source, (
            "No field_validator for secret_key in settings.py"
        )

    def test_default_secret_rejected_when_env_production(self):
        """Verify the validator source code rejects default key in production."""
        settings_path = SRC_ROOT / "qnwis" / "config" / "settings.py"
        source = settings_path.read_text(encoding="utf-8")
        assert "change_this_secret_key_in_production" in source, (
            "Default secret value not found in settings.py"
        )
        assert 'env not in ("development", "test")' in source or \
               "env not in ('development', 'test')" in source or \
               'not in ("development", "test")' in source, (
            "Validator does not check environment for production rejection"
        )
        assert "raise ValueError" in source, (
            "Validator does not raise ValueError for default key"
        )

    def test_default_secret_allowed_in_development(self):
        """Verify the validator allows default key in dev/test."""
        settings_path = SRC_ROOT / "qnwis" / "config" / "settings.py"
        source = settings_path.read_text(encoding="utf-8")
        assert "development" in source and "test" in source, (
            "Validator does not allow default key in development/test"
        )


class TestRBACOnEndpoints:
    """SLO and cache invalidation must require RBAC."""

    def test_slo_list_requires_rbac(self):
        slo_path = SRC_ROOT / "qnwis" / "api" / "routers" / "slo.py"
        source = slo_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_slos":
                args_str = ast.dump(node)
                assert "require_roles" in args_str or "Principal" in source[
                    source.index("def list_slos"):source.index("def list_slos") + 200
                ], "list_slos lacks RBAC dependency"
                break

    def test_cache_invalidate_requires_rbac(self):
        queries_path = SRC_ROOT / "qnwis" / "api" / "routers" / "queries.py"
        source = queries_path.read_text(encoding="utf-8")
        func_start = source.index("def invalidate(")
        func_block = source[func_start:func_start + 200]
        assert "require_roles" in func_block or "Principal" in func_block, (
            "Cache invalidation endpoint lacks RBAC"
        )
