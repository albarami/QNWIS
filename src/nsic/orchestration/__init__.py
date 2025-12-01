"""NSIC Orchestration - Dual-engine orchestration components."""

from .deepseek_client import (
    DeepSeekClient,
    DeepSeekConfig,
    DeepSeekResponse,
    ThinkingBlock,
    InferenceMode,
    create_deepseek_client,
)

from .engine_b_deepseek import (
    EngineBDeepSeek,
    ScenarioResult,
    TurnResult,
    create_engine_b,
)

from .timing_logger import (
    TimingLogger,
    Stage,
    TimingEntry,
    ScenarioTimingReport,
    get_timing_logger,
    reset_timing_logger,
)

from .dual_engine_orchestrator import (
    DualEngineOrchestrator,
    DualEngineResult,
    create_dual_engine_orchestrator,
)

from .error_handler import (
    NSICErrorHandler,
    AnalysisState,
    FailureType,
    DegradationStrategy,
    create_error_handler,
)

from .semantic_cache import (
    SemanticCache,
    CacheEntry,
    CacheStats,
    create_semantic_cache,
)

from .compute_enhanced_orchestrator import (
    ComputeEnhancedOrchestrator,
    ComputeEnhancedResult,
    create_compute_enhanced_orchestrator,
)

__all__ = [
    # DeepSeek Client
    "DeepSeekClient",
    "DeepSeekConfig",
    "DeepSeekResponse",
    "ThinkingBlock",
    "InferenceMode",
    "create_deepseek_client",
    # Engine B
    "EngineBDeepSeek",
    "ScenarioResult",
    "TurnResult",
    "create_engine_b",
    # Timing Logger
    "TimingLogger",
    "Stage",
    "TimingEntry",
    "ScenarioTimingReport",
    "get_timing_logger",
    "reset_timing_logger",
    # Dual-Engine Orchestrator
    "DualEngineOrchestrator",
    "DualEngineResult",
    "create_dual_engine_orchestrator",
    # Error Handler
    "NSICErrorHandler",
    "AnalysisState",
    "FailureType",
    "DegradationStrategy",
    "create_error_handler",
    # Semantic Cache
    "SemanticCache",
    "CacheEntry",
    "CacheStats",
    "create_semantic_cache",
    # Compute-Enhanced Orchestrator (Engine B v5.0)
    "ComputeEnhancedOrchestrator",
    "ComputeEnhancedResult",
    "create_compute_enhanced_orchestrator",
]
