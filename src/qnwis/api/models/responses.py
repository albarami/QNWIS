from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

StreamStatus = Literal["ready", "running", "streaming", "complete", "error"]


class StreamEventResponse(BaseModel):
    """Validated SSE envelope emitted by the council workflow."""

    stage: str = Field(..., description="Workflow stage (classify, rag, synthesize, etc.).")
    status: StreamStatus = Field(..., description="Stage status indicator.")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific payload.")
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Optional latency value captured when the stage completed.",
    )
    timestamp: Optional[str] = Field(
        default=None, description="ISO-8601 timestamp emitted by the stage."
    )
    message: Optional[str] = Field(
        default=None, description="Optional human-friendly message about the event."
    )

    @classmethod
    def heartbeat(cls) -> "StreamEventResponse":
        return cls(stage="heartbeat", status="ready", payload={})
