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

Coordination Layer (Step 15):
- Coordinator: Multi-agent execution planner and executor
- Prefetcher: Declarative data prefetch
- CoordinationPolicy: Execution policies
- merge_results: Deterministic result merger
"""

from .coordination import Coordinator
from .council import CouncilConfig, build_council_graph, run_council
from .graph import QNWISGraph, create_graph
from .merge import merge_results
from .metrics import MetricsObserver, NullMetricsObserver
from .policies import DEFAULT_POLICY, CoordinationPolicy, get_policy_for_complexity
from .prefetch import Prefetcher, generate_cache_key
from .registry import AgentRegistry, create_default_registry
from .schemas import OrchestrationResult, OrchestrationTask
from .synthesis import CouncilReport, synthesize
from .types import AgentCallSpec, ExecutionTrace, PrefetchSpec
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
    # Coordination Layer
    "Coordinator",
    "Prefetcher",
    "generate_cache_key",
    "CoordinationPolicy",
    "get_policy_for_complexity",
    "DEFAULT_POLICY",
    "merge_results",
    "PrefetchSpec",
    "AgentCallSpec",
    "ExecutionTrace",
]
