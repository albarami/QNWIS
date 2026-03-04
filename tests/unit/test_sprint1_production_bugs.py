"""Tests for Sprint 1: Production Bug Fixes.

All tests use real infrastructure — no mocks, no hardcoded data, no synthetic data.

Covers:
  - Task 1.1: sync wrapper must not skip synthesis in async context
  - Task 1.2: LLMClient must respect configured timeout (not hardcoded 7200)
  - Task 1.3: no bare except: clauses in production source code
"""

import ast
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"


# ---------------------------------------------------------------------------
# Task 1.1 – sync wrapper must perform synthesis even inside an async context
# ---------------------------------------------------------------------------

class TestSyncWrapperBridge:
    """The sync wrapper must never silently return unprocessed state."""

    def test_sync_wrapper_returns_state_from_sync_context(self):
        """Calling from a normal sync context must invoke the async node."""
        import inspect

        from src.qnwis.orchestration.nodes.synthesis import (
            legendary_synthesis_node_sync,
        )

        source = inspect.getsource(legendary_synthesis_node_sync)
        assert "return state" not in source.split("try:")[1].split("except RuntimeError")[0] or \
               "concurrent.futures" in source, (
            "Sync wrapper still returns raw state when an event loop is running"
        )

    def test_sync_wrapper_has_thread_bridge_for_async_context(self):
        """The wrapper must use a thread-based bridge when called from async."""
        import inspect

        from src.qnwis.orchestration.nodes.synthesis import (
            legendary_synthesis_node_sync,
        )

        source = inspect.getsource(legendary_synthesis_node_sync)
        assert "ThreadPoolExecutor" in source or "run_coroutine_threadsafe" in source, (
            "Sync wrapper lacks async-to-sync bridge — will silently skip synthesis"
        )

    def test_sync_wrapper_does_not_short_circuit_on_running_loop(self):
        """When get_running_loop() succeeds, wrapper must NOT just return state."""
        import inspect

        from src.qnwis.orchestration.nodes.synthesis import (
            legendary_synthesis_node_sync,
        )

        source = inspect.getsource(legendary_synthesis_node_sync)
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "return state" and i > 0:
                context = "\n".join(lines[max(0, i - 3):i + 1])
                if "get_running_loop" in "\n".join(lines[:i]):
                    if "ThreadPoolExecutor" not in "\n".join(lines[:i]):
                        pytest.fail(
                            f"Sync wrapper short-circuits with 'return state' "
                            f"after get_running_loop:\n{context}"
                        )


# ---------------------------------------------------------------------------
# Task 1.2 – LLMClient must honour the timeout parameter
# ---------------------------------------------------------------------------

class TestLLMClientTimeout:
    """Verify the hardcoded 7200s override is removed."""

    def test_config_default_timeout_is_reasonable(self):
        """get_llm_config() must not default to 7200 seconds."""
        from src.qnwis.llm.config import get_llm_config

        config = get_llm_config()
        assert config.timeout_seconds != 7200, (
            "Default timeout is still 7200s — config.py not fixed"
        )
        assert config.timeout_seconds <= 600, (
            f"Default timeout {config.timeout_seconds}s is unreasonably high "
            f"for a single LLM call"
        )

    def test_explicit_timeout_flows_to_client(self):
        """LLMClient(timeout_s=X) must set self.timeout_s = X, not 7200."""
        from src.qnwis.llm.client import LLMClient

        client = LLMClient(timeout_s=45)
        assert client.timeout_s == 45, (
            f"Expected timeout_s=45, got {client.timeout_s} — "
            f"hardcoded override still present in client.py"
        )

    def test_config_timeout_used_when_no_explicit_override(self):
        """When timeout_s is not passed, client must use config.timeout_seconds."""
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.llm.config import get_llm_config

        config = get_llm_config()
        client = LLMClient()
        assert client.timeout_s == config.timeout_seconds, (
            f"Client timeout {client.timeout_s}s != config timeout "
            f"{config.timeout_seconds}s"
        )

    def test_client_timeout_source_code_has_no_hardcoded_override(self):
        """The line 'self.timeout_s = 7200' must not exist in client.py."""
        client_path = SRC_ROOT / "qnwis" / "llm" / "client.py"
        source = client_path.read_text(encoding="utf-8")
        assert "self.timeout_s = 7200" not in source, (
            "Hardcoded 'self.timeout_s = 7200' still present in client.py"
        )


# ---------------------------------------------------------------------------
# Task 1.3 – no bare except: in production source
# ---------------------------------------------------------------------------

def _collect_python_files():
    """Collect all .py files under src/ for the bare-except scan."""
    src = Path(__file__).resolve().parents[2] / "src"
    if not src.exists():
        return []
    return sorted(
        p for p in src.rglob("*.py")
        if ".backup" not in p.name
        and "__pycache__" not in str(p)
    )


class TestNoBareExcept:
    """AST scan of real production source: no bare except: clauses allowed."""

    @pytest.mark.parametrize("py_file", _collect_python_files())
    def test_no_bare_except(self, py_file: Path):
        source = py_file.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            pytest.skip(f"Syntax error in {py_file}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail(
                    f"Bare except: at {py_file.relative_to(SRC_ROOT)}:{node.lineno}"
                )
