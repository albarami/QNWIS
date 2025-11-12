"""Shared pytest fixtures for all tests."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Use stub provider for all tests
    os.environ["QNWIS_LLM_PROVIDER"] = "stub"
    os.environ["QNWIS_STUB_TOKEN_DELAY_MS"] = "0"
    yield
    # Cleanup not needed since these are session-level
