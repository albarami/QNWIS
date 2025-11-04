from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path


def sql_files(dirpath: str | os.PathLike[str]) -> Iterable[Path]:
    path = Path(dirpath)
    return sorted(file for file in path.glob("*.sql") if file.is_file())
