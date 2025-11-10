import pytest
from fastapi import HTTPException

from qnwis.security import Principal
from qnwis.security.rbac import allowed_roles, require_roles


def test_allowed_roles_from_config():
    roles = allowed_roles("agents_time")
    assert "analyst" in roles
    assert "admin" in roles


def test_require_roles_blocks():
    dependency = require_roles("admin")
    principal = Principal(subject="svc", roles=("analyst",), ratelimit_id="svc")
    with pytest.raises(HTTPException):
        dependency(principal=principal)


def test_require_roles_allows():
    dependency = require_roles("admin")
    principal = Principal(subject="svc", roles=("admin",), ratelimit_id="svc")
    assert dependency(principal=principal) == principal
