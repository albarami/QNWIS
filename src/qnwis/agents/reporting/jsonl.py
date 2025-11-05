"""
JSONL (NDJSON) reporting utilities for agent outputs.

Reports are appended to newline-delimited JSON files for downstream audit
pipelines. The writer operates in append-only mode and creates parent
directories as needed.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..base import AgentReport


def _serialize_report(report: AgentReport) -> dict[str, Any]:
    """Convert an AgentReport into a JSON-serializable payload."""
    payload = asdict(report)
    return payload


def write_report(report: AgentReport, path: str | Path) -> None:
    """
    Append an agent report to a newline-delimited JSON file.

    Args:
        report: The AgentReport instance to serialize.
        path: Destination file path for the JSONL entry.
    """
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _serialize_report(report)
    with target_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")
