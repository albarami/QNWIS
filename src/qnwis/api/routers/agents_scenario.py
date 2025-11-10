"""Scenario agent endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...agents.scenario_agent import ScenarioAgent
from ...scenario.dsl import ScenarioSpec, parse_scenario
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ..models import AgentRequest, AgentResponse
from ._shared import build_response, ensure_intent, get_clock, get_data_client

router = APIRouter(prefix="/agents/scenario", tags=["agents.scenario"])
ROLE_DEP = require_roles(*allowed_roles("agents_scenario"))


def _scenario_spec(source: Any, fmt: str) -> ScenarioSpec:
    try:
        return parse_scenario(source, format=fmt)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _spec_format(params: dict[str, Any]) -> str:
    fmt = params.get("format", "yaml")
    if fmt not in {"yaml", "json", "dict"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format '{fmt}'")
    return fmt


@router.post("/apply", response_model=AgentResponse)
async def scenario_apply(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "scenario.apply")
    spec_source = payload.params.get("spec")
    if spec_source is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="params.spec is required")

    fmt = _spec_format(payload.params)
    spec = _scenario_spec(spec_source, fmt)

    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = ScenarioAgent(client)
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()
    narrative = agent.apply(scenario_spec=spec_source, spec_format=fmt)
    agent_finished = clock.time()
    baseline = agent._fetch_baseline_forecast(spec.metric, spec.sector, spec.horizon_months)
    request_id = getattr(request.state, "request_id", "scenario-apply")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload={"intent": payload.intent, "narrative": narrative},
        sources=[baseline],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )


@router.post("/compare", response_model=AgentResponse)
async def scenario_compare(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "scenario.compare")
    specs_input = payload.params.get("specs")
    if not isinstance(specs_input, list) or not specs_input:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="params.specs must be a non-empty list")
    fmt = _spec_format(payload.params)
    specs = [_scenario_spec(spec_item, fmt) for spec_item in specs_input]
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = ScenarioAgent(client)
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()
    narrative = agent.compare(scenario_specs=specs_input, spec_format=fmt)
    agent_finished = clock.time()
    baseline = agent._fetch_baseline_forecast(specs[0].metric, specs[0].sector, specs[0].horizon_months)
    request_id = getattr(request.state, "request_id", "scenario-compare")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload={"intent": payload.intent, "narrative": narrative},
        sources=[baseline],
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )
