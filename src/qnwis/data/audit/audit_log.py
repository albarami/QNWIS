from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class FileAuditLog:
    """Append-only newline-delimited JSON audit log writer."""

    def __init__(self, path: str) -> None:
        """Initialise the audit log and ensure the parent directory exists."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Mapping[str, Any] | dict[str, Any]) -> None:
        """Append an event, automatically stamping an RFC3339 UTC timestamp."""
        payload = dict(event)
        payload["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")
