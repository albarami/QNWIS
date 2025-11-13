"""
FastAPI router for LLM-powered council endpoints.

Provides streaming (SSE) and complete (JSON) endpoints for the multi-stage
LLM council workflow: classify -> prefetch -> agents -> verify -> synthesize.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...agents.base import AgentReport, DataClient
from ...classification.classifier import Classifier
from ...llm.client import LLMClient
from ...orchestration.streaming import run_workflow_stream

logger = logging.getLogger(__name__)
router = APIRouter(tags=["council-llm"])


class CouncilRequest(BaseModel):
    """Validated request payload for LLM council endpoints."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="Ministerial question to route through the multi-agent workflow.",
        examples=["What are the biggest attrition risks in healthcare for Q2?"],
    )
    provider: Literal["anthropic", "openai", "stub"] = Field(
        "anthropic",
        description="LLM provider identifier. Must match configured providers.",
    )
    model: str | None = Field(
        None,
        max_length=120,
        description="Optional provider/model override (e.g., claude-3-sonnet).",
    )

    @field_validator("question")
    @classmethod
    def _normalize_question(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("question must contain at least 3 non-space characters")
        return normalized

    @field_validator("provider", mode="before")
    @classmethod
    def _normalize_provider(cls, value: str | None) -> str:
        if value is None:
            return "anthropic"
        return str(value).strip().lower()

    @field_validator("model")
    @classmethod
    def _normalize_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class StageMetadata(BaseModel):
    """Per-stage latency and timestamp information."""

    latency_ms: float | None = Field(
        None, ge=0, description="Stage completion latency in milliseconds."
    )
    timestamp: str | None = Field(
        None, description="ISO-8601 timestamp captured when the stage completed."
    )


class CouncilMetadata(BaseModel):
    """Metadata describing the workflow execution."""

    question: str = Field(..., description="Sanitized original question.")
    provider: Literal["anthropic", "openai", "stub"]
    model: str | None = Field(None, description="Resolved provider model used by the workflow.")
    stages: dict[str, StageMetadata] = Field(
        default_factory=dict,
        description="Map of stage name to latency/timestamp metadata.",
    )


class CouncilRunLLMResponse(BaseModel):
    """Structured response for non-streaming council executions."""

    synthesis: str | None = Field(None, description="Final synthesized recommendation.")
    classification: dict[str, Any] | None = Field(
        None, description="Classification output from the workflow."
    )
    agent_reports: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Serialized agent reports generated during the workflow.",
    )
    verification: dict[str, Any] | None = Field(
        None, description="Verification payload emitted by the workflow."
    )
    metadata: CouncilMetadata = Field(
        ..., description="Execution metadata including stage timings."
    )


class CouncilErrorResponse(BaseModel):
    """Standardized error payload for council endpoints."""

    error: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-friendly summary of the failure.")
    request_id: str = Field(description="Correlates logs with the failed request.")


def _serialize_agent_report(report: AgentReport | dict[str, Any]) -> dict[str, Any]:
    if isinstance(report, dict):
        return report
    if not isinstance(report, AgentReport):
        return {"agent": "unknown", "payload": report}

    def _serialize_insight(insight: Any) -> Any:
        if is_dataclass(insight):
            return asdict(insight)
        if hasattr(insight, "model_dump"):
            return insight.model_dump()
        if isinstance(insight, dict):
            return insight
        return str(insight)

    return {
        "agent": report.agent,
        "findings": [_serialize_insight(i) for i in (report.findings or [])],
        "warnings": list(report.warnings),
        "narrative": report.narrative,
        "metadata": dict(report.metadata),
    }


def _error_detail(request_id: str) -> CouncilErrorResponse:
    return CouncilErrorResponse(
        error="council_workflow_failed",
        message="LLM council execution failed. Retry later or contact operations.",
        request_id=request_id,
    )


@router.post(
    "/council/stream",
    responses={
        500: {
            "model": CouncilErrorResponse,
            "description": "Workflow failure. Inspect logs using the provided request_id.",
        }
    },
)
async def council_stream_llm(req: CouncilRequest) -> StreamingResponse:
    """
    Stream the multi-stage LLM council via Server-Sent Events (SSE).

    Example cURL (note `-N` keeps the connection open):

    ```
    curl -N -X POST "http://localhost:8000/api/v1/council/stream" \
      -H "Content-Type: application/json" \
      -d '{"question":"How is attrition trending?","provider":"stub"}'
    ```

    Deploy behind an API gateway or reverse proxy that enforces rate limiting.
    SSE buffering is disabled via `X-Accel-Buffering: no` for compatibility
    with Traefik and Nginx streaming setups.
    """

    request_id = uuid4().hex

    try:
        data_client = DataClient()
        llm_client = LLMClient(provider=req.provider, model=req.model)
        classifier = Classifier()

        async def event_generator() -> AsyncIterator[str]:
            heartbeat = json.dumps(
                {
                    "stage": "heartbeat",
                    "status": "ready",
                    "payload": {},
                    "latency_ms": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
            )
            yield f"event: heartbeat\ndata: {heartbeat}\n\n"

            async for event in run_workflow_stream(
                question=req.question,
                data_client=data_client,
                llm_client=llm_client,
                classifier=classifier,
            ):
                envelope = jsonable_encoder(
                    {
                        "stage": event.stage,
                        "status": event.status,
                        "payload": event.payload,
                        "latency_ms": event.latency_ms,
                        "timestamp": getattr(event, "timestamp", None),
                    },
                    exclude_none=True,
                )
                yield f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
                "X-Request-ID": request_id,
            },
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "council_stream_llm failed (request_id=%s, provider=%s)",
            request_id,
            req.provider,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error_detail(request_id).model_dump(),
        ) from None


@router.post(
    "/council/run-llm",
    response_model=CouncilRunLLMResponse,
    responses={
        500: {
            "model": CouncilErrorResponse,
            "description": "Workflow failure. Inspect logs using the provided request_id.",
        }
    },
)
async def council_run_llm(req: CouncilRequest) -> CouncilRunLLMResponse:
    """
    Execute the LLM council and return a structured JSON payload.

    Example cURL:

    ```
    curl -X POST "http://localhost:8000/api/v1/council/run-llm" \
      -H "Content-Type: application/json" \
      -d '{"question":"Which sectors drive attrition?","provider":"stub"}'
    ```
    """

    request_id = uuid4().hex

    try:
        data_client = DataClient()
        llm_client = LLMClient(provider=req.provider, model=req.model)
        classifier = Classifier()

        classification: dict[str, Any] | None = None
        agent_reports: list[AgentReport | dict[str, Any]] = []
        verification: dict[str, Any] | None = None
        synthesis: str | None = None
        stages_meta: dict[str, StageMetadata] = {}

        async for event in run_workflow_stream(
            question=req.question,
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier,
        ):
            if event.status == "complete":
                stages_meta[event.stage] = StageMetadata(
                    latency_ms=event.latency_ms,
                    timestamp=getattr(event, "timestamp", None),
                )
                if event.stage == "classify":
                    classification = event.payload.get("classification")
                elif event.stage.startswith("agent:") and "report" in event.payload:
                    agent_reports.append(event.payload["report"])
                elif event.stage == "verify":
                    verification = event.payload
                elif event.stage == "synthesize":
                    synthesis = event.payload.get("synthesis")
                elif event.stage == "done":
                    if not agent_reports:
                        done_reports = event.payload.get("agent_reports") or []
                        agent_reports.extend(done_reports)
                    synthesis = synthesis or event.payload.get("synthesis", synthesis)

        metadata = CouncilMetadata(
            question=req.question,
            provider=req.provider,
            model=llm_client.model,
            stages=stages_meta,
        )

        return CouncilRunLLMResponse(
            synthesis=synthesis,
            classification=classification,
            agent_reports=[_serialize_agent_report(r) for r in agent_reports],
            verification=verification,
            metadata=metadata,
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "council_run_llm failed (request_id=%s, provider=%s)",
            request_id,
            req.provider,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error_detail(request_id).model_dump(),
        ) from None
