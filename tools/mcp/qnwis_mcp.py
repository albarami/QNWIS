"""
QNWIS MCP Server - Secure stdio-based Model Context Protocol server.

Exposes tools for safe file reading, git operations, secret scanning, and env discovery.
Implements security via allowlist, secret redaction, and env filtering.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from subprocess import TimeoutExpired
from typing import Any

_MCP_AVAILABLE = False

try:
    _server_module = importlib.import_module("mcp.server")
    _stdio_module = importlib.import_module("mcp.server.stdio")
    _types_module = importlib.import_module("mcp.types")
except ImportError:

    @dataclass
    class _Tool:
        name: str
        description: str
        inputSchema: dict[str, Any]

    @dataclass
    class _TextContent:
        type: str
        text: str

    class _Server:
        """Fallback server when 'mcp' package is unavailable."""

        def __init__(self, name: str) -> None:
            self.name = name

        def call_tool(self):
            """No-op decorator when MCP is unavailable."""

            def decorator(func):
                return func

            return decorator

        def list_tools(self):
            """No-op decorator for tool listing."""

            def decorator(func):
                return func

            return decorator

        def create_initialization_options(self) -> dict[str, Any]:
            return {}

        async def run(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("mcp package is required to run the MCP server.")

    class _MissingStdioServer:
        async def __aenter__(self):
            raise RuntimeError("mcp package is required to run the MCP server.")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def _stdio_server() -> _MissingStdioServer:
        return _MissingStdioServer()

    Server = _Server
    stdio_server = _stdio_server
    TextContent = _TextContent
    Tool = _Tool
else:
    _MCP_AVAILABLE = True
    Server = _server_module.Server
    stdio_server = _stdio_module.stdio_server
    TextContent = _types_module.TextContent
    Tool = _types_module.Tool

ROOT = Path(__file__).resolve().parents[2]  # D:\lmis_int
ALLOWLIST_PATH = ROOT / "tools" / "mcp" / "allowlist.json"
MAX_FS_READ_BYTES = 1_000_000
GIT_SHOW_MAX_BYTES = 100_000
GIT_TIMEOUT_S = 3.0  # keep tests snappy on Windows

SECRET_REGEX = re.compile(r"([A-Za-z0-9_\-]{32,})")
STRICT_SECRET_REGEX = re.compile(r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z0-9_\-]{32,}")
SAFE_ENV_PREFIXES = ("QNWIS_", "WORLD_BANK_", "QATAR_OPENDATA_", "SEMANTIC_SCHOLAR_")

server = Server("qnwis-mcp")
PathLikeStr = str | os.PathLike[str]
_ALLOWLIST_CACHE: list[Path] | None = None


def _normalize_path_input(path: PathLikeStr) -> Path:
    """
    Normalize an incoming path to an absolute path within the repository root.

    Args:
        path: Path-like value provided by the caller.

    Returns:
        Absolute, normalized Path instance.
    """
    path_obj = Path(path).expanduser()
    if not path_obj.is_absolute():
        path_obj = ROOT / path_obj
    resolved = path_obj.resolve()
    return Path(os.path.normcase(str(resolved)))


def _allowlist_paths() -> list[Path]:
    """
    Return the cached allowlist as normalized Path objects.

    Returns:
        List of normalized allowlist Path objects.

    Raises:
        RuntimeError: If the allowlist contains invalid entries.
    """
    global _ALLOWLIST_CACHE
    if _ALLOWLIST_CACHE is None:
        entries = _load_allowlist()
        paths: list[Path] = []
        for entry in entries:
            try:
                paths.append(_normalize_path_input(entry))
            except Exception as exc:  # pragma: no cover - defensive check
                raise RuntimeError(f"Invalid allowlist entry '{entry}': {exc}") from exc
        _ALLOWLIST_CACHE = paths
    return list(_ALLOWLIST_CACHE)


def _is_normalized_allowed(path: Path) -> bool:
    """
    Determine if a normalized path resides within the allowlist.

    Args:
        path: Normalized absolute Path to validate.

    Returns:
        True if the path is allowed, False otherwise.
    """
    for allowed in _allowlist_paths():
        if path == allowed:
            return True
        if allowed.is_dir():
            try:
                path.relative_to(allowed)
            except ValueError:
                continue
            return True
    return False


def _assert_allowed_path(path: PathLikeStr) -> Path:
    """
    Normalize a path and ensure it resides within the allowlist.

    Args:
        path: Path-like value provided by the caller.

    Returns:
        Normalized Path instance.

    Raises:
        ValueError: If the path is outside of the configured allowlist.
    """
    normalized = _normalize_path_input(path)
    if not _is_normalized_allowed(normalized):
        raise ValueError(f"Access denied: '{normalized}' is not within the allowlist.")
    return normalized


def _load_allowlist() -> list[str]:
    """
    Load the allowlist of paths that can be read.

    Returns:
        List of allowed path strings.

    Raises:
        RuntimeError: If the allowlist file is missing or malformed.
    """
    try:
        with ALLOWLIST_PATH.open(encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Allowlist file not found: {ALLOWLIST_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Allowlist file '{ALLOWLIST_PATH}' is not valid JSON: {exc}") from exc

    if not isinstance(data, list) or not all(isinstance(entry, str) for entry in data):
        raise RuntimeError("Allowlist file must contain a JSON array of string paths.")

    return data


def _is_allowed(path: PathLikeStr) -> bool:
    """
    Check if a path is within the allowlist.

    Args:
        path: Path to check.

    Returns:
        True if path is allowed, False otherwise.
    """
    normalized = _normalize_path_input(path)
    return _is_normalized_allowed(normalized)


def fs_read_text(path: PathLikeStr, max_bytes: int = 200_000) -> dict[str, Any]:
    """
    Safely read a text file within the allowlist.

    Args:
        path: File path to read. Must resolve under an allowlisted root.
        max_bytes: Maximum bytes to read (default 200KB, must be 1 ≤ n ≤ 1,000,000).

    Returns:
        Dictionary with path and text content.

    Raises:
        ValueError: If path is not in allowlist or arguments are invalid.
        RuntimeError: If the file cannot be read.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer.")
    if max_bytes > MAX_FS_READ_BYTES:
        raise ValueError(f"max_bytes cannot exceed {MAX_FS_READ_BYTES} bytes.")

    normalized_path = _assert_allowed_path(path)
    if normalized_path.is_dir():
        raise ValueError(f"Cannot read directory '{normalized_path}'.")

    try:
        with normalized_path.open("rb") as file_obj:
            data = file_obj.read(max_bytes)
    except OSError as exc:
        raise RuntimeError(f"Failed to read '{normalized_path}': {exc}") from exc

    return {"path": str(normalized_path), "text": data.decode("utf-8", errors="replace")}


def _run_git_command(*args: str, text: bool = True) -> str | bytes:
    """
    Execute a git command rooted at the repository and capture its output.

    Args:
        *args: Git command arguments.
        text: Whether to decode stdout to text. Defaults to True.

    Returns:
        Command stdout as text or bytes based on the `text` flag.

    Raises:
        RuntimeError: If git is unavailable, the command fails, or exceeds the timeout.
    """
    command = ["git", "-C", str(ROOT), *args]
    try:
        result = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=text,
            timeout=GIT_TIMEOUT_S,
        )
        return result  # type: ignore[no-any-return]
    except FileNotFoundError as exc:
        raise RuntimeError("Git executable not found in PATH.") from exc
    except TimeoutExpired as exc:
        joined = " ".join(args)
        raise RuntimeError(
            f"Git command timed out after {GIT_TIMEOUT_S:.1f}s ({joined})."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stdout = exc.stdout or ("" if text else b"")
        if text and isinstance(stdout, str):
            message = stdout.strip() or str(exc)
        elif not text and isinstance(stdout, bytes):
            message = stdout.decode("utf-8", errors="replace").strip() or str(exc)
        else:
            message = str(exc)
        if "not a git repository" in message.lower():
            raise RuntimeError(f"Repository path '{ROOT}' is not a Git repository.") from exc
        raise RuntimeError(f"Git command failed ({' '.join(args)}): {message}") from exc


def git_status() -> dict[str, Any]:
    """
    Return 'git status --porcelain=v1' for the repo root.

    Returns:
        Dictionary with status output.

    Raises:
        RuntimeError: If git fails or the command exceeds the configured timeout (3.0s).
    """
    out = _run_git_command("status", "--porcelain=v1")
    assert isinstance(out, str)
    return {"status": out}


def git_diff(target: str = "HEAD") -> dict[str, Any]:
    """
    Return 'git diff --name-only <target>'.

    Args:
        target: Git reference to diff against (default HEAD). Must be a valid git ref.

    Returns:
        Dictionary with list of changed files.

    Raises:
        RuntimeError: If git fails or the command exceeds the timeout.
    """
    out = _run_git_command("diff", "--name-only", target)
    assert isinstance(out, str)
    return {"diff_files": [line for line in out.splitlines() if line.strip()]}


def git_show(file: PathLikeStr, rev: str = "HEAD") -> dict[str, Any]:
    """
    Show file contents from a specific revision, limited to 100kB.

    Args:
        file: File path to display. Must resolve under the allowlist.
        rev: Git revision (default HEAD). Limited to outputs ≤ 100,000 bytes.

    Returns:
        Dictionary with relative path, revision, text content, and truncation flag.
    """
    normalized_path = _assert_allowed_path(file)
    try:
        relative_path = normalized_path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(
            f"Path '{normalized_path}' is not inside repository root '{ROOT}'."
        ) from exc

    git_identifier = f"{rev}:{relative_path.as_posix()}"
    raw_output = _run_git_command("show", git_identifier, text=False)
    assert isinstance(raw_output, (bytes, bytearray))
    limited = raw_output[:GIT_SHOW_MAX_BYTES]
    text = limited.decode("utf-8", errors="replace")
    truncated = len(raw_output) > len(limited)
    return {
        "path": str(relative_path),
        "rev": rev,
        "text": text,
        "truncated": truncated,
    }


def secrets_scan(
    glob_exclude: list[str] | None = None,
    secrets_scan_strict: bool = False,
) -> dict[str, Any]:
    """
    Naive secret-like token scan for ≥32 character alnum/_/- tokens.

    Excludes `external_data`, images, `.git`, `.venv`, and `__pycache__` paths by default.

    Args:
        glob_exclude: Optional list of repo-relative prefixes to skip from scanning.
        secrets_scan_strict: When True, require uppercase, lowercase, and digit characters.

    Returns:
        Dictionary with findings (redacted) and match count.
    """

    excludes = set(glob_exclude or [])

    results: list[dict[str, Any]] = []

    pattern = STRICT_SECRET_REGEX if secrets_scan_strict else SECRET_REGEX

    for dirpath, _, filenames in os.walk(ROOT):

        if any(
            x in dirpath for x in ("external_data", ".git", ".venv", "__pycache__", "node_modules")
        ):

            continue

        for name in filenames:

            if any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".pdf", ".parquet")):

                continue

            p = Path(dirpath) / name

            rel = str(p.relative_to(ROOT))

            if any(rel.startswith(e) for e in excludes):

                continue

            try:

                text = p.read_text(encoding="utf-8", errors="ignore")

            except Exception:

                continue

            for match in pattern.finditer(text):

                token = match.group(0)

                redacted = f"{token[:4]}..." if token else ""

                results.append(
                    {
                        "file": rel,
                        "match": redacted,
                        "pos": match.start(),
                        "strict": secrets_scan_strict,
                    }
                )

    return {"findings": results, "count": len(results)}


def env_list(prefix: str | None = None) -> dict[str, Any]:
    """
    Return environment variable names filtered by SAFE_ENV_PREFIXES or by a custom prefix.

    Args:
        prefix: Optional custom prefix to filter by. When omitted, defaults to SAFE_ENV_PREFIXES.

    Returns:
        Dictionary containing the filtered environment variable names. Values are never returned.
    """
    names = []
    for k in os.environ:
        if prefix:
            if k.startswith(prefix):
                names.append(k)
        else:
            if k.startswith(SAFE_ENV_PREFIXES):
                names.append(k)
    return {"env_vars": names}


# Register tools with MCP server
@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="fs_read_text",
            description="Safely read a text file within the allowlist",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "max_bytes": {
                        "type": "integer",
                        "description": "Maximum bytes to read (default 200KB, capped at 1MB)",
                        "default": 200000,
                        "minimum": 1,
                        "maximum": MAX_FS_READ_BYTES,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="git_status",
            description="Return 'git status --porcelain=v1' for the repo root",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="git_diff",
            description="Return 'git diff --name-only <target>'",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Git reference to diff against",
                        "default": "HEAD",
                    }
                },
            },
        ),
        Tool(
            name="git_show",
            description="Show file contents from a specific revision (limited to 100kB).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Path to the file to display",
                    },
                    "rev": {
                        "type": "string",
                        "description": "Git revision to read from",
                        "default": "HEAD",
                    },
                },
                "required": ["file"],
            },
        ),
        Tool(
            name="secrets_scan",
            description="Naive secret-like token scan (>=32 char alnum/_/-). Excludes external_data and images by default; optional stricter entropy rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "glob_exclude": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of glob patterns to exclude",
                    },
                    "secrets_scan_strict": {
                        "type": "boolean",
                        "description": "Require uppercase, lowercase, and digit characters in matches",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="env_list",
            description="Return environment variables filtered by SAFE_ENV_PREFIXES or by provided prefix. Values are NOT returned, only names.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": "Optional custom prefix to filter by",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "fs_read_text":
            result = fs_read_text(**arguments)
        elif name == "git_status":
            result = git_status()
        elif name == "git_diff":
            result = git_diff(**arguments)
        elif name == "git_show":
            result = git_show(**arguments)
        elif name == "secrets_scan":
            result = secrets_scan(**arguments)
        elif name == "env_list":
            result = env_list(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        error_payload = {
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }
        }
        return [TextContent(type="text", text=json.dumps(error_payload, indent=2))]


async def main() -> None:
    """Run the MCP server."""
    if not _MCP_AVAILABLE:
        raise RuntimeError("mcp package is required to run the MCP server.")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
