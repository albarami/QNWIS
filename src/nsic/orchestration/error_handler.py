"""
NSIC Error Handler - Graceful Degradation for Production Systems

Production systems fail. This module ensures the system produces SOMETHING useful
rather than crashing entirely. Each failure mode has a documented recovery strategy.

Integration:
- Used by DualEngineOrchestrator during query processing
- Tracks all degradations in audit trail
- Adjusts confidence scores based on limitations
- Generates degradation summaries for ministerial briefs
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can occur during analysis."""
    ENGINE_A_TIMEOUT = "engine_a_timeout"
    ENGINE_A_MID_DEBATE = "engine_a_mid_debate"
    ENGINE_B_TIMEOUT = "engine_b_timeout"
    ENGINE_B_INSTANCE_CRASH = "engine_b_instance_crash"
    BOTH_ENGINES_FAIL = "both_engines_fail"
    EMBEDDINGS_SERVER_DOWN = "embeddings_server_down"
    VERIFICATION_SERVER_DOWN = "verification_server_down"
    KG_SERVER_DOWN = "kg_server_down"
    EXTERNAL_API_FAILURE = "external_api_failure"
    RAG_FAILURE = "rag_failure"
    DATABASE_FAILURE = "database_failure"


@dataclass
class DegradationStrategy:
    """Strategy for handling a specific failure type."""
    action: str
    confidence_reduction: float
    message_template: str
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class AnalysisState:
    """
    Tracks the current state of analysis including any degradations.

    Passed through the orchestration pipeline and updated as failures occur.
    """
    # Confidence tracking
    base_confidence: float = 0.80
    confidence_reduction: float = 0.0

    # Component availability
    engine_a_available: bool = True
    engine_b_available: bool = True
    embeddings_available: bool = True
    verification_available: bool = True
    kg_available: bool = True

    # Partial completion tracking
    engine_a_completed_turns: int = 0
    engine_a_partial: bool = False
    engine_b_completed_scenarios: int = 0
    deepseek_single_instance: bool = False

    # Data source tracking
    successful_apis: List[str] = field(default_factory=list)
    failed_apis: List[str] = field(default_factory=list)

    # Audit and messaging
    degradation_notes: List[str] = field(default_factory=list)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)

    def get_final_confidence(self) -> float:
        """Calculate final confidence after all degradations."""
        return max(0.20, self.base_confidence - self.confidence_reduction)

    def is_degraded(self) -> bool:
        """Check if any degradation has occurred."""
        return self.confidence_reduction > 0 or len(self.degradation_notes) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for logging/storage."""
        return {
            "base_confidence": self.base_confidence,
            "confidence_reduction": self.confidence_reduction,
            "final_confidence": self.get_final_confidence(),
            "engine_a_available": self.engine_a_available,
            "engine_b_available": self.engine_b_available,
            "embeddings_available": self.embeddings_available,
            "verification_available": self.verification_available,
            "kg_available": self.kg_available,
            "engine_a_partial": self.engine_a_partial,
            "engine_a_completed_turns": self.engine_a_completed_turns,
            "deepseek_single_instance": self.deepseek_single_instance,
            "successful_apis_count": len(self.successful_apis),
            "failed_apis_count": len(self.failed_apis),
            "degradation_notes_count": len(self.degradation_notes),
            "is_degraded": self.is_degraded(),
        }


class NSICErrorHandler:
    """
    Graceful degradation when components fail.

    System should produce SOMETHING useful, not crash entirely.
    Each failure type has a documented recovery strategy.
    """

    # Degradation strategies for each failure type
    STRATEGIES: Dict[FailureType, DegradationStrategy] = {
        FailureType.ENGINE_A_TIMEOUT: DegradationStrategy(
            action="proceed_with_engine_b_only",
            confidence_reduction=0.25,
            message_template="Deep analysis unavailable. Proceeding with broad exploration only.",
            severity="high"
        ),
        FailureType.ENGINE_A_MID_DEBATE: DegradationStrategy(
            action="save_partial_continue_or_summarize",
            confidence_reduction=0.15,
            message_template="Deep analysis interrupted at turn {turn}. Synthesizing from {completed_turns} completed turns.",
            severity="medium"
        ),
        FailureType.ENGINE_B_TIMEOUT: DegradationStrategy(
            action="proceed_with_engine_a_only",
            confidence_reduction=0.20,
            message_template="Broad exploration unavailable. Proceeding with deep analysis only.",
            severity="high"
        ),
        FailureType.ENGINE_B_INSTANCE_CRASH: DegradationStrategy(
            action="route_to_surviving_instance",
            confidence_reduction=0.10,
            message_template="One DeepSeek instance unavailable. Routing all scenarios to remaining instance.",
            severity="medium"
        ),
        FailureType.BOTH_ENGINES_FAIL: DegradationStrategy(
            action="return_data_summary_only",
            confidence_reduction=0.60,
            message_template="Analysis engines unavailable. Returning extracted facts and basic summary.",
            severity="critical"
        ),
        FailureType.EMBEDDINGS_SERVER_DOWN: DegradationStrategy(
            action="use_keyword_search_fallback",
            confidence_reduction=0.15,
            message_template="Semantic search unavailable. Using keyword matching fallback.",
            severity="medium"
        ),
        FailureType.VERIFICATION_SERVER_DOWN: DegradationStrategy(
            action="skip_verification_flag_output",
            confidence_reduction=0.20,
            message_template="Verification unavailable. Claims not independently verified.",
            severity="high"
        ),
        FailureType.KG_SERVER_DOWN: DegradationStrategy(
            action="skip_causal_chains",
            confidence_reduction=0.10,
            message_template="Knowledge graph unavailable. Causal chain analysis skipped.",
            severity="medium"
        ),
        FailureType.EXTERNAL_API_FAILURE: DegradationStrategy(
            action="proceed_with_available_sources",
            confidence_reduction=0.05,
            message_template="Data source '{api_name}' unavailable. Analysis based on {available}/{total} sources.",
            severity="low"
        ),
        FailureType.RAG_FAILURE: DegradationStrategy(
            action="proceed_without_rag_context",
            confidence_reduction=0.10,
            message_template="R&D research context unavailable. Analysis based on extracted data only.",
            severity="medium"
        ),
        FailureType.DATABASE_FAILURE: DegradationStrategy(
            action="proceed_without_historical",
            confidence_reduction=0.10,
            message_template="Historical database unavailable. Analysis based on current data only.",
            severity="medium"
        ),
    }

    def __init__(self):
        """Initialize the error handler."""
        self._stats = {
            "total_failures_handled": 0,
            "failures_by_type": {},
            "successful_recoveries": 0,
        }
        logger.info("NSICErrorHandler initialized")

    def create_state(self) -> AnalysisState:
        """Create a fresh analysis state for a new query."""
        return AnalysisState()

    async def handle_engine_a_failure(
        self,
        state: AnalysisState,
        error: Exception,
        turn: Optional[int] = None
    ) -> AnalysisState:
        """
        Handle Azure GPT-5 (Engine A) failure during debate.

        Args:
            state: Current analysis state
            error: The exception that occurred
            turn: Current turn number if failed mid-debate

        Returns:
            Updated state with degradation applied
        """
        if turn and turn > 50:
            # More than half complete - summarize what we have
            failure_type = FailureType.ENGINE_A_MID_DEBATE
            state.engine_a_partial = True
            state.engine_a_completed_turns = turn
        else:
            # Early failure or no turn info - proceed without Engine A
            failure_type = FailureType.ENGINE_A_TIMEOUT
            state.engine_a_available = False

        strategy = self.STRATEGIES[failure_type]
        state.confidence_reduction += strategy.confidence_reduction

        message = strategy.message_template.format(
            turn=turn or 0,
            completed_turns=turn or 0
        )
        state.degradation_notes.append(message)

        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event": "engine_failure",
            "engine": "A",
            "failure_type": failure_type.value,
            "turn": turn,
            "strategy": strategy.action,
            "confidence_reduction": strategy.confidence_reduction,
            "error": str(error),
            "error_type": type(error).__name__,
        })

        self._update_stats(failure_type)
        logger.warning(f"Engine A failure handled: {message}")

        return state

    async def handle_engine_b_failure(
        self,
        state: AnalysisState,
        error: Exception,
        instance: Optional[int] = None,
        completed_scenarios: int = 0
    ) -> AnalysisState:
        """
        Handle DeepSeek (Engine B) failure.

        Args:
            state: Current analysis state
            error: The exception that occurred
            instance: Which DeepSeek instance failed (1 or 2)
            completed_scenarios: Number of scenarios completed before failure

        Returns:
            Updated state with degradation applied
        """
        state.engine_b_completed_scenarios = completed_scenarios

        if instance and self._check_other_instance_health(instance):
            # Route to surviving instance
            failure_type = FailureType.ENGINE_B_INSTANCE_CRASH
            state.deepseek_single_instance = True
        else:
            # Both instances down or single instance mode
            failure_type = FailureType.ENGINE_B_TIMEOUT
            state.engine_b_available = False

        strategy = self.STRATEGIES[failure_type]
        state.confidence_reduction += strategy.confidence_reduction
        state.degradation_notes.append(strategy.message_template)

        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event": "engine_failure",
            "engine": "B",
            "failure_type": failure_type.value,
            "instance": instance,
            "completed_scenarios": completed_scenarios,
            "strategy": strategy.action,
            "confidence_reduction": strategy.confidence_reduction,
            "error": str(error),
            "error_type": type(error).__name__,
        })

        self._update_stats(failure_type)
        logger.warning(f"Engine B failure handled: {strategy.message_template}")

        return state

    async def handle_both_engines_failure(
        self,
        state: AnalysisState,
        error_a: Optional[Exception] = None,
        error_b: Optional[Exception] = None
    ) -> AnalysisState:
        """
        Handle case where both engines have failed.

        Args:
            state: Current analysis state
            error_a: Engine A error if applicable
            error_b: Engine B error if applicable

        Returns:
            Updated state - will trigger basic summary mode
        """
        failure_type = FailureType.BOTH_ENGINES_FAIL
        strategy = self.STRATEGIES[failure_type]

        state.engine_a_available = False
        state.engine_b_available = False
        state.confidence_reduction += strategy.confidence_reduction
        state.degradation_notes.append(strategy.message_template)

        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event": "critical_failure",
            "failure_type": failure_type.value,
            "strategy": strategy.action,
            "confidence_reduction": strategy.confidence_reduction,
            "error_a": str(error_a) if error_a else None,
            "error_b": str(error_b) if error_b else None,
        })

        self._update_stats(failure_type)
        logger.error(f"CRITICAL: Both engines failed - {strategy.message_template}")

        return state

    async def handle_service_failure(
        self,
        state: AnalysisState,
        service: str,
        error: Exception
    ) -> AnalysisState:
        """
        Handle failure of a supporting service (embeddings, verification, KG).

        Args:
            state: Current analysis state
            service: Name of the failed service
            error: The exception that occurred

        Returns:
            Updated state with appropriate degradation
        """
        # Map service name to failure type
        service_mapping = {
            "embeddings": FailureType.EMBEDDINGS_SERVER_DOWN,
            "verification": FailureType.VERIFICATION_SERVER_DOWN,
            "knowledge_graph": FailureType.KG_SERVER_DOWN,
            "kg": FailureType.KG_SERVER_DOWN,
            "rag": FailureType.RAG_FAILURE,
            "database": FailureType.DATABASE_FAILURE,
        }

        failure_type = service_mapping.get(service.lower(), FailureType.EXTERNAL_API_FAILURE)
        strategy = self.STRATEGIES[failure_type]

        # Update availability flags
        if service.lower() == "embeddings":
            state.embeddings_available = False
        elif service.lower() == "verification":
            state.verification_available = False
        elif service.lower() in ["knowledge_graph", "kg"]:
            state.kg_available = False

        state.confidence_reduction += strategy.confidence_reduction
        state.degradation_notes.append(strategy.message_template)

        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event": "service_failure",
            "service": service,
            "failure_type": failure_type.value,
            "strategy": strategy.action,
            "confidence_reduction": strategy.confidence_reduction,
            "error": str(error),
            "error_type": type(error).__name__,
        })

        self._update_stats(failure_type)
        logger.warning(f"Service failure ({service}): {strategy.message_template}")

        return state

    async def handle_api_failure(
        self,
        state: AnalysisState,
        api_name: str,
        error: Exception
    ) -> AnalysisState:
        """
        Handle external API failure during data extraction.

        Args:
            state: Current analysis state
            api_name: Name of the failed API
            error: The exception that occurred

        Returns:
            Updated state with degradation applied
        """
        state.failed_apis.append(api_name)

        available = len(state.successful_apis)
        total = available + len(state.failed_apis)

        strategy = self.STRATEGIES[FailureType.EXTERNAL_API_FAILURE]

        message = strategy.message_template.format(
            api_name=api_name,
            available=available,
            total=total
        )
        state.degradation_notes.append(message)

        # Small reduction per failed API
        state.confidence_reduction += strategy.confidence_reduction

        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event": "api_failure",
            "api_name": api_name,
            "available_apis": available,
            "total_apis": total,
            "confidence_reduction": strategy.confidence_reduction,
            "error": str(error),
        })

        self._update_stats(FailureType.EXTERNAL_API_FAILURE)
        logger.warning(f"API failure ({api_name}): {message}")

        return state

    def record_api_success(self, state: AnalysisState, api_name: str) -> AnalysisState:
        """Record a successful API call."""
        state.successful_apis.append(api_name)
        return state

    def _check_other_instance_health(self, failed_instance: int) -> bool:
        """
        Check if the other DeepSeek instance is healthy.

        Args:
            failed_instance: The instance that failed (1 or 2)

        Returns:
            True if the other instance is available
        """
        # In production, this would actually check the health endpoint
        # For now, we assume if one fails, the other might be available
        try:
            import requests
            other_port = 8002 if failed_instance == 1 else 8001
            response = requests.get(f"http://localhost:{other_port}/v1/models", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def _update_stats(self, failure_type: FailureType):
        """Update internal statistics."""
        self._stats["total_failures_handled"] += 1

        type_name = failure_type.value
        if type_name not in self._stats["failures_by_type"]:
            self._stats["failures_by_type"][type_name] = 0
        self._stats["failures_by_type"][type_name] += 1

    def generate_degradation_summary(self, state: AnalysisState) -> str:
        """
        Generate summary of any degradations for the ministerial brief.

        Args:
            state: The analysis state with degradation info

        Returns:
            Formatted string for inclusion in output, or empty if no degradations
        """
        notes = state.degradation_notes
        if not notes:
            return ""

        # Deduplicate notes
        unique_notes = list(dict.fromkeys(notes))

        severity = "HIGH" if state.confidence_reduction > 0.30 else (
            "MEDIUM" if state.confidence_reduction > 0.15 else "LOW"
        )

        return f"""
ANALYSIS LIMITATIONS ({severity})
{'='*40}
{chr(10).join(f'* {note}' for note in unique_notes)}

Note: Confidence score adjusted from {state.base_confidence*100:.0f}% to {state.get_final_confidence()*100:.0f}%
to reflect these limitations.
"""

    def get_stats(self) -> Dict[str, Any]:
        """Get error handler statistics."""
        return {
            **self._stats,
            "strategies_available": len(self.STRATEGIES),
        }


# Factory function
def create_error_handler() -> NSICErrorHandler:
    """Create an error handler instance."""
    return NSICErrorHandler()
