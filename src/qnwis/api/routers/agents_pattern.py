"""Pattern Detective agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...agents.pattern_detective import PatternDetectiveAgent
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ..models import AgentRequest, AgentResponse
from ._shared import build_response, ensure_intent, get_clock, get_data_client

router = APIRouter(prefix="/agents/pattern", tags=["agents.pattern"])
ROLE_DEP = require_roles(*allowed_roles("agents_pattern"))


def _prepare_request(payload: AgentRequest, required_params: tuple[str, ...] = ()) -> dict[str, float]:
    params: dict[str, float] = {}
    for key in required_params:
        if key not in payload.params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"params.{key} is required",
            )
    if "z_threshold" in payload.params:
        params["z_threshold"] = float(payload.params["z_threshold"])
    if "min_sample_size" in payload.params:
        params["min_sample_size"] = int(payload.params["min_sample_size"])
    if "min_correlation" in payload.params:
        params["min_correlation"] = float(payload.params["min_correlation"])
    if "method" in payload.params:
        params["method"] = str(payload.params["method"])
    return params


@router.post("/anomalies", response_model=AgentResponse)
async def anomalies(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "pattern.anomalies")
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = PatternDetectiveAgent(client)
    params = _prepare_request(payload)
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()
    report = agent.detect_anomalous_retention(
        z_threshold=params.get("z_threshold", 2.5),
        min_sample_size=params.get("min_sample_size", 3),
    )
    agent_finished = clock.time()
    source = client.run("syn_attrition_by_sector_latest")
    request_id = getattr(request.state, "request_id", "pattern-anomalies")
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


@router.post("/correlations", response_model=AgentResponse)
async def correlations(
    payload: AgentRequest,
    request: Request,
    principal: Principal = Depends(ROLE_DEP),
) -> AgentResponse:
    ensure_intent(payload, "pattern.correlations")
    request.state.principal = principal
    request.state.agent_request = payload
    client = get_data_client(request)
    agent = PatternDetectiveAgent(client)
    params = _prepare_request(payload)
    clock = get_clock(request)
    started = clock.time()
    agent_started = clock.time()
    report = agent.find_correlations(
        method=params.get("method", "spearman"),
        min_correlation=params.get("min_correlation", 0.5),
        min_sample_size=params.get("min_sample_size", 5),
    )
    agent_finished = clock.time()
    sources = [
        client.run("syn_qatarization_by_sector_latest"),
        client.run("syn_attrition_by_sector_latest"),
    ]
    request_id = getattr(request.state, "request_id", "pattern-correlations")
    return build_response(
        request_model=payload,
        request_id=request_id,
        principal=principal,
        payload=report,
        sources=sources,
        started_ts=started,
        agent_started_ts=agent_started,
        agent_finished_ts=agent_finished,
        clock=clock,
    )
