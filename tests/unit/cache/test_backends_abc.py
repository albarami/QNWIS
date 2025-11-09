"""Test that CacheBackend ABC is properly enforced."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add src to path for imports
SRC_ROOT = Path(__file__).parents[3] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from qnwis.data.cache.backends import CacheBackend, MemoryCacheBackend  # noqa: E402


def test_cannot_instantiate_abstract_backend():
    """CacheBackend cannot be instantiated directly (ABC enforcement)."""
    with pytest.raises(TypeError, match="abstract"):
        CacheBackend()  # type: ignore[abstract]


def test_incomplete_subclass_raises_type_error():
    """Subclass missing abstract methods cannot be instantiated."""

    class IncompleteBackend(CacheBackend):
        """Missing all required methods."""
        pass

    with pytest.raises(TypeError, match="abstract"):
        IncompleteBackend()  # type: ignore[abstract]


def test_partial_implementation_raises_type_error():
    """Subclass with only some methods implemented cannot be instantiated."""

    class PartialBackend(CacheBackend):
        """Only implements get, missing set and delete."""

        def get(self, key: str) -> str | None:
            return None

    with pytest.raises(TypeError, match="abstract"):
        PartialBackend()  # type: ignore[abstract]


def test_complete_implementation_works():
    """Subclass implementing all abstract methods can be instantiated."""

    class CompleteBackend(CacheBackend):
        """Implements all required methods."""

        def get(self, key: str) -> str | None:
            return None

        def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
            pass

        def delete(self, key: str) -> None:
            pass

    # Should not raise
    backend = CompleteBackend()
    assert isinstance(backend, CacheBackend)


def test_memory_backend_is_complete():
    """MemoryCacheBackend properly implements the ABC."""
    backend = MemoryCacheBackend()
    assert isinstance(backend, CacheBackend)

    # Test basic operations
    backend.set("test_key", "test_value", ttl_s=60)
    assert backend.get("test_key") == "test_value"

    backend.delete("test_key")
    assert backend.get("test_key") is None


def test_abstractmethod_has_ellipsis():
    """Abstract methods use ellipsis (...) not pass or NotImplementedError."""
    import inspect

    # Get the abstract methods
    abstract_methods = CacheBackend.__abstractmethods__
    assert abstract_methods == {"get", "set", "delete"}

    # Verify they don't raise NotImplementedError
    for method_name in abstract_methods:
        method = getattr(CacheBackend, method_name)
        source = inspect.getsource(method)

        # Should have ellipsis, not pass or NotImplementedError
        assert "..." in source or "pass" not in source
        assert "NotImplementedError" not in source
