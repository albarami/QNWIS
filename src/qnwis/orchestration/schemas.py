"""
Orchestration schemas for QNWIS workflow.

Defines typed inputs, outputs, and state for the LangGraph workflow.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Intent = Literal[
    "pattern.anomalies",
    "pattern.correlation",
    "pattern.root_causes",
    "pattern.best_practices",
    "strategy.gcc_benchmark",
    "strategy.talent_competition",
    "strategy.vision2030",
]


class OrchestrationTask(BaseModel):
    """
    Input task for the orchestration workflow.

    Attributes:
        intent: The analytical intent to execute
        params: Parameters specific to the intent
        user_id: Optional user identifier (for audit trails)
        request_id: Optional request tracking identifier
    """

    intent: Intent
    params: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_params(self) -> "OrchestrationTask":
        """Cross-field validation for commonly supplied parameters."""
        params = self.params or {}

        start_year = params.get("start_year")
        end_year = params.get("end_year")
        if isinstance(start_year, int) and isinstance(end_year, int):
            if start_year > end_year:
                raise ValueError("start_year must be less than or equal to end_year")

        top_n = params.get("top_n")
        if top_n is not None:
            if not isinstance(top_n, int):
                raise TypeError("top_n must be an integer")
            if not 1 <= top_n <= 50:
                raise ValueError("top_n must be between 1 and 50")

        months = params.get("months")
        if months is not None:
            if months not in {12, 24, 36}:
                raise ValueError("months must be one of {12, 24, 36}")

        return self


class ReportSection(BaseModel):
    """
    A structured section of the final report.

    Attributes:
        title: Section title
        body_md: Section content in Markdown format
    """

    title: str
    body_md: str


class Citation(BaseModel):
    """
    Citation with query provenance.

    Attributes:
        query_id: Deterministic query identifier
        dataset_id: Source dataset identifier
        locator: File path or API endpoint
        fields: List of field names in the result
        timestamp: When the data was accessed
    """

    query_id: str
    dataset_id: str
    locator: str
    fields: List[str]
    timestamp: Optional[str] = None


class Freshness(BaseModel):
    """
    Data freshness metadata per source.

    Attributes:
        source: Source identifier
        last_updated: ISO timestamp of last update
        age_days: Age in days
    """

    source: str
    last_updated: str
    age_days: Optional[float] = None


class Reproducibility(BaseModel):
    """
    Reproducibility metadata.

    Attributes:
        method: Agent method executed
        params: Parameters used (PII-safe)
        timestamp: Execution timestamp
    """

    method: str
    params: Dict[str, Any]
    timestamp: str


class OrchestrationResult(BaseModel):
    """
    Final output from the orchestration workflow.

    Attributes:
        ok: Whether the workflow completed successfully
        intent: The executed intent
        sections: Structured report sections
        citations: List of data citations
        freshness: Per-source freshness metadata
        reproducibility: Execution metadata for reproducibility
        warnings: Any warnings generated during execution
        request_id: Request tracking identifier
        timestamp: When the result was generated
    """

    ok: bool
    intent: Intent
    sections: List[ReportSection]
    citations: List[Citation]
    freshness: Dict[str, Freshness]
    reproducibility: Reproducibility
    warnings: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkflowState(BaseModel):
    """
    Internal state for LangGraph workflow.

    This state is passed between nodes and accumulates information
    as the workflow progresses.

    Attributes:
        task: The input task
        route: Resolved intent route
        agent_output: Output from agent execution
        error: Error message if any
        logs: Execution logs
        metadata: Additional metadata collected during execution
    """

    task: Optional[OrchestrationTask] = None
    route: Optional[str] = None
    agent_output: Optional[Any] = None  # AgentReport from agents.base
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
