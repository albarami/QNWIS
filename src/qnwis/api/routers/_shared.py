"""Shared helpers for agent routers."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import HTTPException, Request, status

from ...agents.base import AgentReport, DataClient, Insight
from ...data.deterministic.models import QueryResult
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ...utils.clock import Clock
from ..models import (
    AgentRequest,
    AgentResponse,
    Citation,
    ConfidenceScore,
    FreshnessInfo,
    TimingsMs,
)


def get_clock(request: Request) -> Clock:
    clock = getattr(request.app.state, "clock", None)
    if isinstance(clock, Clock):
        return clock
    new_clock = Clock()
    request.app.state.clock = new_clock
    return new_clock


def get_data_client(request: Request) -> DataClient:
    factory = getattr(request.app.state, "data_client_factory", None)
    if callable(factory):
        client = factory()
        if isinstance(client, DataClient):
            return client
    return DataClient()


def ensure_intent(request_model: AgentRequest, expected: str) -> None:
    if request_model.intent != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"intent '{request_model.intent}' does not match expected '{expected}'",
        )


def _freshness_info(results: Sequence[QueryResult]) -> FreshnessInfo | None:
    if not results:
        return None
    dates = [res.freshness.asof_date for res in results if res.freshness.asof_date]
    updated = [res.freshness.updated_at for res in results if res.freshness.updated_at]
    if not dates:
        return None
    sources = {res.query_id: res.freshness.asof_date for res in results}
    return FreshnessInfo(
        asof_min=min(dates),
        asof_max=max(dates),
        updated_max=max(updated) if updated else None,
        sources=sources,
    )


def _citations(results: Sequence[QueryResult]) -> list[Citation]:
    citations: list[Citation] = []
    for res in results:
        citations.append(
            Citation(
                qid=res.query_id,
                note=f"Source dataset {res.provenance.dataset_id}",
                source=res.provenance.source,
            )
        )
    return citations


def _confidence(results: Sequence[QueryResult]) -> ConfidenceScore:
    warnings = sum(len(res.warnings) for res in results)
    coverage_penalty = min(30, warnings * 5)
    score = max(40, 95 - coverage_penalty)
    if score >= 85:
        band = "very_high"
    elif score >= 70:
        band = "high"
    elif score >= 55:
        band = "med"
    else:
        band = "low"
    return ConfidenceScore(
        score=score,
        band=band,
        components={
            "data_quality": round(max(0, 100 - warnings * 10) / 100, 2),
            "freshness": 0.95,
            "coverage": round((100 - coverage_penalty) / 100, 2),
        },
    )


def _serialize_report(report: AgentReport | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(report, str):
        return {"narrative": report}
    if isinstance(report, dict):
        return report
    if isinstance(report, AgentReport):
        findings = [_serialize_insight(insight) for insight in report.findings]
        return {
            "agent": report.agent,
            "findings": findings,
            "warnings": list(report.warnings),
        }
    raise TypeError(f"Unsupported agent payload: {type(report)}")


def _serialize_insight(insight: Insight) -> dict[str, Any]:
    if is_dataclass(insight):
        return asdict(insight)
    return dict(insight)  # pragma: no cover - defensive


def build_response(
    *,
    request_model: AgentRequest,
    request_id: str,
    _principal: Principal,
    payload: AgentReport | dict[str, Any] | str,
    sources: Sequence[QueryResult],
    started_ts: float,
    agent_started_ts: float,
    agent_finished_ts: float,
    clock: Clock,
) -> AgentResponse:
    freshness = _freshness_info(sources)
    citations = _citations(sources) if request_model.options.enforce_citations else []
    confidence = _confidence(sources) if request_model.options.verify_numbers else None
    audit_id = str(uuid.uuid4()) if request_model.options.audit_pack else None

    total_ms = int(max(0.0, clock.time() - started_ts) * 1000)
    agent_ms = int(max(0.0, agent_finished_ts - agent_started_ts) * 1000)

    return AgentResponse(
        request_id=request_id,
        audit_id=audit_id,
        confidence=confidence,
        freshness=freshness,
        result=_serialize_report(payload),
        citations=citations,
        timings_ms=TimingsMs(total=total_ms, agent=agent_ms),
        warnings=[],
    )


__all__ = [
    "allowed_roles",
    "build_response",
    "ensure_intent",
    "get_clock",
    "get_data_client",
    "require_roles",
]
