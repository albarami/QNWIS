"""
Multi-agent orchestration for QNWIS.

Provides both legacy council-based orchestration and new LangGraph workflow.

Legacy:
- CouncilConfig, run_council: Council-based multi-agent orchestration
- synthesize: Report synthesis

LangGraph Workflow (Step 14):
- QNWISGraph: State machine orchestrator
- AgentRegistry: Intent-to-method mapping
- OrchestrationTask/Result: Typed inputs/outputs
"""

from .council import CouncilConfig, build_council_graph, run_council
from .graph import QNWISGraph, create_graph
from .metrics import MetricsObserver, NullMetricsObserver
from .registry import AgentRegistry, create_default_registry
from .schemas import OrchestrationResult, OrchestrationTask
from .synthesis import CouncilReport, synthesize
from .verification import VerificationIssue, VerificationResult, verify_insight, verify_report

__all__ = [
    # Legacy Council
    "CouncilConfig",
    "build_council_graph",
    "run_council",
    "CouncilReport",
    "synthesize",
    "VerificationIssue",
    "VerificationResult",
    "verify_insight",
    "verify_report",
    # LangGraph Workflow
    "QNWISGraph",
    "create_graph",
    "AgentRegistry",
    "create_default_registry",
    "OrchestrationTask",
    "OrchestrationResult",
    "MetricsObserver",
    "NullMetricsObserver",
]
