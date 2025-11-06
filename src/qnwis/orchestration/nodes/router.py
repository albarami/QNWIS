"""
Router node: Validates task intent and resolves routing.

This node performs security checks and ensures the intent is registered
before allowing workflow progression.

Supports both explicit intent routing and natural language query classification.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..classifier import QueryClassifier
from ..registry import AgentRegistry, UnknownIntentError
from ..schemas import RoutingDecision, WorkflowState

logger = logging.getLogger(__name__)

# Global classifier instance (lazy initialization)
_classifier: Optional[QueryClassifier] = None


def _build_clarifying_question(query_text: str) -> str:
    """
    Build a deterministic clarifying question for low-confidence queries.

    Args:
        query_text: Original query text

    Returns:
        Clarifying question string
    """
    snippet = " ".join(query_text.strip().split()) if query_text else ""
    if len(snippet) > 80:
        snippet = f"{snippet[:77]}..."
    return (
        f"Could you clarify the primary labour market metric or sector for \"{snippet}\"?"
    )


def _get_classifier() -> QueryClassifier:
    """
    Get or create the global QueryClassifier instance.

    Returns:
        Initialized QueryClassifier

    Raises:
        FileNotFoundError: If required lexicon files are missing
    """
    global _classifier

    if _classifier is None:
        # Determine paths relative to this module
        orchestration_dir = Path(__file__).parent.parent
        catalog_path = orchestration_dir / "intent_catalog.yml"
        sector_lex = orchestration_dir / "keywords" / "sectors.txt"
        metric_lex = orchestration_dir / "keywords" / "metrics.txt"

        _classifier = QueryClassifier(
            catalog_path=str(catalog_path),
            sector_lex=str(sector_lex),
            metric_lex=str(metric_lex),
            min_confidence=0.55,
        )
        logger.info("QueryClassifier initialized in router")

    return _classifier


def route_intent(state: Dict[str, Any], registry: AgentRegistry) -> Dict[str, Any]:
    """
    Validate and route the task intent.

    Supports two modes:
    1. Explicit intent: task.intent is provided -> validate and pass through
    2. Natural language: task.query_text is provided -> classify -> map to intents

    Args:
        state: Current workflow state
        registry: Agent registry for intent validation

    Returns:
        Updated state with route, routing_decision, and potentially updated task
    """
    workflow_state = WorkflowState(**state)

    if workflow_state.task is None:
        error_msg = "No task provided to router"
        logger.error(error_msg)
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    task = workflow_state.task
    logs = workflow_state.logs.copy()
    metadata = dict(workflow_state.metadata or {})

    try:
        # Mode 1: Explicit intent provided
        if task.intent is not None:
            intent = task.intent
            logger.info("Explicit intent routing: %s request_id=%s", intent, task.request_id)

            # Validate intent is registered
            if not registry.is_registered(intent):
                available = registry.intents()
                logger.error(
                    "Unknown intent requested: %s. Available intents: %s",
                    intent,
                    available,
                )
                raise UnknownIntentError(intent, available)

            # Create simple routing decision for backward compatibility
            routing_decision = RoutingDecision(
                agents=[intent],
                mode="single",
                prefetch=[],
                notes=["Explicit intent routing"],
            )

            log_entry = f"Routed to intent: {intent}"
            logger.info(log_entry)
            logs.append(log_entry)

            return {
                **state,
                "route": intent,
                "routing_decision": routing_decision.model_dump(),
                "logs": logs,
                "metadata": metadata,
            }

        # Mode 2: Natural language query classification
        elif task.query_text is not None:
            query_text = task.query_text
            logger.info(
                "Query classification routing: query=%s... request_id=%s",
                query_text[:50],
                task.request_id,
            )

            # Get classifier
            classifier = _get_classifier()

            # Classify query
            classification = classifier.classify_text(query_text)
            logs.append(
                f"Classification: {len(classification.intents)} intents, "
                f"complexity={classification.complexity}, "
                f"confidence={classification.confidence:.2f}"
            )
            logger.info(
                "Classification metrics: request_id=%s intent_scores=%s complexity=%s "
                "confidence=%.2f elapsed_ms=%.2f",
                task.request_id,
                classification.intent_scores,
                classification.complexity,
                classification.confidence,
                classification.elapsed_ms,
            )
            metadata.update(
                {
                    "classification_confidence": classification.confidence,
                    "classification_elapsed_ms": classification.elapsed_ms,
                    "classification_intent_scores": classification.intent_scores,
                    "classification_complexity": classification.complexity,
                }
            )

            # Check confidence threshold
            if classification.confidence < classifier.min_confidence:
                clarifying_question = _build_clarifying_question(query_text)
                metadata["clarifying_question"] = clarifying_question
                error_msg = (
                    f"Clarification required (confidence {classification.confidence:.2f} "
                    f"< {classifier.min_confidence:.2f}). {clarifying_question}"
                )
                logger.warning(error_msg)
                return {
                    **state,
                    "error": error_msg,
                    "logs": logs + [f"WARNING: {error_msg}"],
                    "metadata": metadata,
                }

            # Filter to registered intents only
            valid_intents = [
                intent for intent in classification.intents
                if registry.is_registered(intent)
            ]

            if not valid_intents:
                available = registry.intents()
                error_msg = (
                    f"No valid intents found. Classified as: {classification.intents}. "
                    f"Registered intents: {available}"
                )
                logger.error(error_msg)
                return {
                    **state,
                    "error": error_msg,
                    "logs": logs + [f"ERROR: {error_msg}"],
                    "metadata": metadata,
                }

            # Take primary intent (highest score)
            primary_intent = valid_intents[0]
            logger.info("Primary intent selected: %s", primary_intent)
            metadata["tie_within_threshold"] = classification.tie_within_threshold

            # Determine execution mode based on complexity and intent count
            if classification.tie_within_threshold and len(valid_intents) >= 2:
                valid_intents = valid_intents[:2]
                mode = "parallel"
                logs.append("Tie within threshold; executing top intents in parallel")
            elif classification.complexity == "simple" or len(valid_intents) == 1:
                mode = "single"
            elif classification.complexity in ["medium", "complex"]:
                mode = "parallel" if len(valid_intents) <= 3 else "sequential"
            else:  # crisis
                mode = "parallel"  # High priority parallel execution

            # Determine data prefetch needs
            prefetch = classifier.determine_data_needs(classification)
            metadata["routed_agents"] = valid_intents

            # Build routing decision
            routing_decision = RoutingDecision(
                agents=valid_intents,
                mode=mode,
                prefetch=prefetch,
                notes=classification.reasons,
            )

            # Update task with classification
            task.classification = classification
            task.intent = primary_intent  # Set primary for execution

            log_entry = f"Classified to intent: {primary_intent} (mode={mode})"
            logger.info(log_entry)
            logs.append(log_entry)

            return {
                **state,
                "task": task.model_dump(),
                "route": primary_intent,
                "routing_decision": routing_decision.model_dump(),
                "logs": logs,
                "metadata": metadata,
            }

        else:
            error_msg = "Neither intent nor query_text provided in task"
            logger.error(error_msg)
            return {
                **state,
                "error": error_msg,
                "logs": logs + [f"ERROR: {error_msg}"],
                "metadata": metadata,
            }

    except UnknownIntentError as exc:
        logger.error("Unknown intent: %s", exc)
        return {
            **state,
            "error": str(exc),
            "logs": logs + [f"ERROR: {exc}"],
            "metadata": metadata,
        }
    except Exception as exc:
        logger.exception("Unexpected routing error")
        error_msg = f"Routing failed: {type(exc).__name__}: {exc}"
        return {
            **state,
            "error": error_msg,
            "logs": logs + [f"ERROR: {error_msg}"],
            "metadata": metadata,
        }
