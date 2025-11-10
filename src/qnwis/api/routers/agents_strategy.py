"""National strategy agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...agents.national_strategy import NationalStrategyAgent
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ..models import AgentRequest, AgentResponse
from ._shared import build_response, ensure_intent, get_clock, get_data_client

router = APIRouter(prefix="/agents/strategy", tags=["agents.strategy"])
ROLE_DEP = require_roles(*allowed_roles("agents_strategy"))


@router.post("/benchmark", response_model=AgentResponse)
async def gcc_benchmark(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "strategy.benchmark")
    min_countries = int(payload.params.get("min_countries", 3))
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = NationalStrategyAgent(client)
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()
    try:
        report = agent.gcc_benchmark(min_countries=min_countries)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    agent_finished = clock.time()
    source = client.run("syn_unemployment_rate_gcc_latest")
    request_id = getattr(request.state, "request_id", "strategy-benchmark")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload=report,
        sources=[source],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )


@router.post("/vision", response_model=AgentResponse)
async def vision_alignment(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "strategy.vision")
    target_year = int(payload.params.get("target_year", 2030))
    current_year = int(payload.params.get("current_year", 2024))
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = NationalStrategyAgent(client)
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()
    try:
        report = agent.vision2030_alignment(target_year=target_year, current_year=current_year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    agent_finished = clock.time()
    source = client.run("syn_qatarization_by_sector_latest")
    request_id = getattr(request.state, "request_id", "strategy-vision")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload=report,
        sources=[source],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )
