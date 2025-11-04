"""Test to verify environment setup."""

import sys
from pathlib import Path


def test_python_version() -> None:
    """Verify Python version is 3.11+."""
    assert sys.version_info >= (3, 11), "Python 3.11+ required"


def test_package_structure() -> None:
    """Verify package structure exists."""
    src_path = Path(__file__).parent.parent / "src" / "qnwis"
    assert src_path.exists(), "src/qnwis directory should exist"
    assert (src_path / "__init__.py").exists(), "__init__.py should exist"


def test_imports() -> None:
    """Verify key packages can be imported."""
    import fastapi  # noqa: F401
    import pydantic  # noqa: F401
    import redis  # noqa: F401
    import sqlalchemy  # noqa: F401
    import uvicorn  # noqa: F401

    # Verify qnwis package can be imported
    import qnwis  # noqa: F401

    assert True, "All imports successful"


def test_config_settings() -> None:
    """Verify settings can be loaded."""
    from qnwis.config.settings import settings

    assert settings is not None
    assert settings.environment == "development"
    assert settings.stage_a_timeout_ms == 50
    assert settings.stage_b_timeout_ms == 60
    assert settings.stage_c_timeout_ms == 40
