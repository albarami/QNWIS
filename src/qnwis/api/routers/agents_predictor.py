"""Predictor agent endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...agents.predictor import PredictorAgent
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ..models import AgentRequest, AgentResponse
from ._shared import build_response, ensure_intent, get_clock, get_data_client

router = APIRouter(prefix="/agents/predictor", tags=["agents.predictor"])
ROLE_DEP = require_roles(*allowed_roles("agents_predictor"))


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}: {exc}") from exc


def _metric(payload: AgentRequest) -> str:
    metric = payload.params.get("metric")
    if not metric:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="params.metric is required")
    return str(metric)


@router.post("/forecast", response_model=AgentResponse)
async def forecast(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "predictor.forecast")
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = PredictorAgent(client)
    metric = _metric(payload)
    sector = payload.params.get("sector")
    horizon = int(payload.params.get("horizon_months", 6))
    clock = get_clock(request)
    today = clock.now().date()
    start = _parse_date(payload.params.get("start_date"), "start_date") or today.replace(year=today.year - 3)
    end = _parse_date(payload.params.get("end_date"), "end_date") or today
    started = clock.time()
    agent_started = clock.time()
    try:
        narrative = agent.forecast_baseline(
            metric=metric,
            sector=sector,
            start=start,
            end=end,
            horizon_months=horizon,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    agent_finished = clock.time()

    query_id = agent._resolve_query_id(metric)  # type: ignore[attr-defined]
    source = client.run(query_id)
    request_id = getattr(request.state, "request_id", "predictor-forecast")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload={"intent": payload.intent, "narrative": narrative},
        sources=[source],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )


@router.post("/warnings", response_model=AgentResponse)
async def warnings(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "predictor.warnings")
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = PredictorAgent(client)
    metric = _metric(payload)
    sector = payload.params.get("sector")
    clock = get_clock(request)
    today = clock.now().date()
    end = _parse_date(payload.params.get("end_date"), "end_date") or today
    horizon = int(payload.params.get("horizon_months", 3))

    started = clock.time()
    agent_started = clock.time()
    try:
        narrative = agent.early_warning(
            metric=metric,
            sector=sector,
            end=end,
            horizon_months=horizon,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    agent_finished = clock.time()

    query_id = agent._resolve_query_id(metric)  # type: ignore[attr-defined]
    source = client.run(query_id)
    request_id = getattr(request.state, "request_id", "predictor-warnings")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload={"intent": payload.intent, "narrative": narrative},
        sources=[source],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )
