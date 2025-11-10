from typing import Any, IO

class YAMLError(Exception): ...

def safe_load(stream: str | bytes | IO[str] | IO[bytes]) -> Any: ...
def safe_dump(
    data: Any,
    stream: IO[str] | None = ...,
    *,
    default_flow_style: bool | None = ...,
    sort_keys: bool = ...,
) -> str | None: ...
