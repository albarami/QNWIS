"""
Agent registry with security controls.

Maps intents to agent methods while preventing arbitrary attribute access.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Tuple

logger = logging.getLogger(__name__)


class UnknownIntentError(LookupError):
    """Raised when attempting to resolve an unregistered intent."""

    def __init__(self, intent: str, available: list[str]) -> None:
        self.intent = intent
        self.available = available
        super().__init__(
            f"Unknown intent: {intent}. Available intents: {', '.join(sorted(available))}"
        )


class AgentRegistry:
    """
    Secure registry mapping intents to agent methods.

    This registry enforces explicit registration and prevents reflective
    access to arbitrary methods. Only whitelisted intent->method mappings
    are permitted.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._mappings: Dict[str, Tuple[Any, str]] = {}

    def register(self, intent: str, agent: Any, method: str) -> None:
        """
        Register an intent with its corresponding agent and method.

        Args:
            intent: Intent identifier (e.g., "pattern.anomalies")
            agent: Agent instance
            method: Method name on the agent (must exist)

        Raises:
            AttributeError: If the method does not exist on the agent
            ValueError: If the intent is already registered
        """
        if intent in self._mappings:
            raise ValueError(f"Intent already registered: {intent}")

        # Verify the method exists on the agent
        if not hasattr(agent, method):
            raise AttributeError(
                f"Agent {type(agent).__name__} does not have method: {method}"
            )

        # Verify it's callable
        method_obj = getattr(agent, method)
        if not callable(method_obj):
            raise TypeError(
                f"Attribute {method} on {type(agent).__name__} is not callable"
            )

        self._mappings[intent] = (agent, method)
        logger.info(
            "Registered intent=%s -> %s.%s",
            intent,
            type(agent).__name__,
            method,
        )

    def resolve(self, intent: str) -> Tuple[Any, str]:
        """
        Resolve an intent to its agent and method name.

        Args:
            intent: Intent identifier

        Returns:
            Tuple of (agent_instance, method_name)

        Raises:
            UnknownIntentError: If the intent is not registered
        """
        if intent not in self._mappings:
            raise UnknownIntentError(intent, self.intents())

        return self._mappings[intent]

    def get_method(self, intent: str) -> Callable[..., Any]:
        """
        Get the callable method for an intent.

        Args:
            intent: Intent identifier

        Returns:
            Callable method

        Raises:
            UnknownIntentError: If the intent is not registered
        """
        agent, method_name = self.resolve(intent)
        return getattr(agent, method_name)

    def intents(self) -> list[str]:
        """
        List all registered intents.

        Returns:
            Sorted list of intent identifiers
        """
        return sorted(self._mappings.keys())

    def is_registered(self, intent: str) -> bool:
        """
        Check if an intent is registered.

        Args:
            intent: Intent identifier

        Returns:
            True if registered, False otherwise
        """
        return intent in self._mappings

    def clear(self) -> None:
        """Clear all registrations (primarily for testing)."""
        self._mappings.clear()
        logger.info("Registry cleared")


def create_default_registry(
    client: Any,
    verifier: Any = None,
) -> AgentRegistry:
    """
    Create a registry with all standard QNWIS agents.

    Args:
        client: DataClient instance
        verifier: Optional AgentResponseVerifier instance

    Returns:
        Populated AgentRegistry
    """
    from ..agents.labour_economist import LabourEconomistAgent
    from ..agents.national_strategy import NationalStrategyAgent
    from ..agents.nationalization import NationalizationAgent
    from ..agents.pattern_detective import PatternDetectiveAgent
    from ..agents.skills import SkillsAgent

    registry = AgentRegistry()

    # Instantiate agents
    pattern_agent = PatternDetectiveAgent(client, verifier)
    strategy_agent = NationalStrategyAgent(client, verifier)
    labour_agent = LabourEconomistAgent(client)  # noqa: F841 - Reserved for future use
    nationalization_agent = NationalizationAgent(client)  # noqa: F841 - Reserved for future use
    skills_agent = SkillsAgent(client)  # noqa: F841 - Reserved for future use

    # Pattern Detective intents
    registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")
    registry.register("pattern.correlation", pattern_agent, "find_correlations")
    registry.register("pattern.root_causes", pattern_agent, "identify_root_causes")
    registry.register("pattern.best_practices", pattern_agent, "best_practices")

    # National Strategy intents
    registry.register("strategy.gcc_benchmark", strategy_agent, "gcc_benchmark")
    registry.register(
        "strategy.talent_competition", strategy_agent, "talent_competition_assessment"
    )
    registry.register("strategy.vision2030", strategy_agent, "vision2030_alignment")

    logger.info("Default registry created with %d intents", len(registry.intents()))
    return registry
