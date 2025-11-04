"""Ensure reference scripts cannot be imported by runtime code."""

from __future__ import annotations

import importlib
import importlib.util

import pytest

REFERENCE_MODULES = [
    "references.orchestration_reference",
    "references.prompts_reference",
    "references.rag_system_reference",
]


@pytest.mark.parametrize("module_name", REFERENCE_MODULES)
def test_reference_modules_raise_import_error(module_name: str) -> None:
    """Reference scripts should not be imported as modules."""
    spec = importlib.util.find_spec(module_name)
    assert spec is not None, f"Expected {module_name} to be discoverable for guard enforcement"

    with pytest.raises(ImportError):
        importlib.import_module(module_name)
