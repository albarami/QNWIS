"""Shared pytest fixtures for all tests."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables.

    Uses real LLM provider from environment - no stubs/mocks.
    Provider should be set via environment (QNWIS_LLM_PROVIDER).
    """
    # No longer overriding provider - tests use real LLM from environment
    # QNWIS_LLM_PROVIDER defaults to 'azure' in production
    yield
