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

Complexity = Literal["simple", "medium", "complex", "crisis"]


class Entities(BaseModel):
    """
    Extracted entities from query text.

    Attributes:
        sectors: List of identified sector names
        metrics: List of identified metrics (retention, salary, etc.)
        time_horizon: Parsed time horizon (start/end dates or relative periods).
            Defaults to last 36 months when absent.
    """

    sectors: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    time_horizon: Optional[Dict[str, Any]] = None


class Classification(BaseModel):
    """
    Query classification result.

    Attributes:
        intents: List of matching intent identifiers
        complexity: Query complexity level
        entities: Extracted entities from the query
        confidence: Confidence score [0,1]
        reasons: Human-readable explanation of classification decisions
        intent_scores: Deterministic mapping of intents to their scores
        elapsed_ms: Classification latency in milliseconds
        tie_within_threshold: Whether top intents were within tie delta
    """

    intents: List[str]
    complexity: Complexity
    entities: Entities
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    intent_scores: Dict[str, float] = Field(default_factory=dict)
    elapsed_ms: float = Field(default=0.0, ge=0.0)
    tie_within_threshold: bool = False

    @model_validator(mode="after")
    def _validate_intent_scores(self) -> "Classification":
        """Validate that scores exist for all intents and tie metadata is consistent."""
        missing = [intent for intent in self.intents if intent not in self.intent_scores]
        if missing:
            raise ValueError(f"Missing intent scores for: {', '.join(missing)}")

        if self.tie_within_threshold and len(self.intents) < 2:
            raise ValueError("tie_within_threshold requires at least two intents")

        return self


class RoutingDecision(BaseModel):
    """
    Routing decision with execution mode and prefetch needs.

    Attributes:
        agents: List of agent method names to execute
        mode: Execution mode (single, parallel, sequential)
        prefetch: List of data prefetch specifications (declarative)
        notes: Additional routing notes or warnings
        execution_hints: Execution hints for coordination (complexity, priority, etc.)
    """

    agents: List[str]
    mode: Literal["single", "parallel", "sequential"]
    prefetch: List[Dict[str, Any]] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    execution_hints: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_mode_agents(self) -> "RoutingDecision":
        """Ensure routing mode is consistent with number of agents."""
        if not self.agents:
            raise ValueError("RoutingDecision.agents must not be empty")

        agent_count = len(self.agents)
        if self.mode == "single" and agent_count != 1:
            raise ValueError("Single mode requires exactly one agent")
        if self.mode in {"parallel", "sequential"} and agent_count < 2:
            raise ValueError(f"{self.mode} mode requires at least two agents")

        return self


class OrchestrationTask(BaseModel):
    """
    Input task for the orchestration workflow.

    Attributes:
        intent: The analytical intent to execute (optional if query_text provided)
        query_text: Natural language query (optional if intent provided)
        params: Parameters specific to the intent
        user_id: Optional user identifier (for audit trails)
        request_id: Optional request tracking identifier
        classification: Classification result (populated by router if query_text used)
    """

    intent: Optional[Intent] = None
    query_text: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    classification: Optional[Classification] = None

    @model_validator(mode="after")
    def _validate_intent_or_query(self) -> "OrchestrationTask":
        """Ensure either intent or query_text is provided."""
        if self.intent is None and self.query_text is None:
            raise ValueError("Either intent or query_text must be provided")
        return self

    @model_validator(mode="after")
    def _validate_params_after_intent(self) -> "OrchestrationTask":
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
        last_updated: ISO timestamp of latest update observed
        age_days: Age in days for the latest update (if available)
        min_timestamp: Oldest timestamp observed across partial results
        max_timestamp: Latest timestamp observed across partial results
    """

    source: str
    last_updated: str
    age_days: Optional[float] = None
    min_timestamp: Optional[str] = None
    max_timestamp: Optional[str] = None


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
        intent: The executed intent (string for coordination flexibility)
        sections: Structured report sections
        citations: List of data citations
        freshness: Per-source freshness metadata
        reproducibility: Execution metadata for reproducibility
        warnings: Any warnings generated during execution
        request_id: Request tracking identifier
        timestamp: When the result was generated
        agent_traces: Execution traces from coordinated agents
    """

    ok: bool
    intent: str  # Changed from Intent Literal to str for coordination flexibility
    sections: List[ReportSection]
    citations: List[Citation]
    freshness: Dict[str, Freshness]
    reproducibility: Reproducibility
    warnings: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_traces: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """
    Internal state for LangGraph workflow.

    This state is passed between nodes and accumulates information
    as the workflow progresses.

    Attributes:
        task: The input task
        route: Resolved intent route
        routing_decision: Routing decision with mode and prefetch info
        agent_output: Output from agent execution
        error: Error message if any
        logs: Execution logs
        metadata: Additional metadata collected during execution
        prefetch_cache: Cache of prefetched QueryResult objects
    """

    task: Optional[OrchestrationTask] = None
    route: Optional[str] = None
    routing_decision: Optional[RoutingDecision] = None
    agent_output: Optional[Any] = None  # AgentReport from agents.base
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    prefetch_cache: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
