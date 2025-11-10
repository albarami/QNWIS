"""Time Machine agent HTTP endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...agents.time_machine import TimeMachineAgent
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ..models import AgentRequest, AgentResponse
from ._shared import (
    build_response,
    ensure_intent,
    get_clock,
    get_data_client,
)

router = APIRouter(prefix="/agents/time", tags=["agents.time"])
ROLE_DEP = require_roles(*allowed_roles("agents_time"))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _run_agent(
    request: Request,
    agent_fn: str,
    *,
    params: dict[str, Any],
) -> AgentResponse:
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()

    client = get_data_client(request)
    agent = TimeMachineAgent(client)

    metric = params["metric"]
    try:
        narrative = getattr(agent, agent_fn)(
            metric=metric,
            sector=params.get("sector"),
            start=params.get("start"),
            end=params.get("end"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected agent bug
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    agent_finished = clock.time()
    series_qid = agent.series_map.get(metric)
    if not series_qid:
        raise HTTPException(status_code=400, detail=f"Unknown metric '{metric}'")
    source_result = client.run(series_qid)

    principal: Principal = request.state.principal
    request_model: AgentRequest = request.state.agent_request
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return build_response(
        request_model=request_model,
        request_id=request_id,
        principal=principal,
        payload={
            "intent": request_model.intent,
            "narrative": narrative,
        },
        sources=[source_result],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )


def _prepare_request(request_model: AgentRequest) -> dict[str, Any]:
    metric = request_model.params.get("metric")
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="params.metric is required",
        )
    sector = request_model.params.get("sector")
    start = _parse_date(request_model.params.get("start_date"))
    end = _parse_date(request_model.params.get("end_date"))
    return {"metric": metric, "sector": sector, "start": start, "end": end}


@router.post("/baseline", response_model=AgentResponse)
async def baseline(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "time.baseline")
    request.state.principal = principal
    request.state.agent_request = payload
    return _run_agent(request, "baseline_report", params=_prepare_request(payload))


@router.post("/trend", response_model=AgentResponse)
async def trend(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "time.trend")
    request.state.principal = principal
    request.state.agent_request = payload
    return _run_agent(request, "trend_report", params=_prepare_request(payload))


@router.post("/breaks", response_model=AgentResponse)
async def breaks(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "time.breaks")
    request.state.principal = principal
    request.state.agent_request = payload
    return _run_agent(request, "breaks_report", params=_prepare_request(payload))
