"""
Configuration loader for orchestration system.

Loads and validates YAML configuration files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load orchestration configuration from YAML file.

    Args:
        config_path: Path to config file (default: src/qnwis/config/orchestration.yml)

    Returns:
        Configuration dictionary

    Raises:
        ConfigurationError: If config is invalid
        FileNotFoundError: If config file not found
    """
    if config_path is None:
        # Default path
        config_path = Path(__file__).parent / "orchestration.yml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    logger.info("Loading configuration from: %s", config_path)

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary")

        # Validate required sections
        _validate_config(config)

        logger.info("Configuration loaded successfully")
        return config

    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML: {exc}") from exc


def _validate_config(config: dict[str, Any]) -> None:
    """
    Validate configuration structure.

    Args:
        config: Configuration dictionary

    Raises:
        ConfigurationError: If validation fails
    """
    required_sections = ["timeouts", "retries", "validation", "enabled_intents"]

    for section in required_sections:
        if section not in config:
            raise ConfigurationError(f"Missing required section: {section}")

    # Validate timeouts
    timeouts = config["timeouts"]
    if not isinstance(timeouts, dict):
        raise ConfigurationError("timeouts must be a dictionary")

    if "agent_call_ms" not in timeouts:
        raise ConfigurationError("timeouts.agent_call_ms is required")

    if not isinstance(timeouts["agent_call_ms"], int) or timeouts["agent_call_ms"] <= 0:
        raise ConfigurationError("timeouts.agent_call_ms must be a positive integer")

    # Validate retries
    retries = config["retries"]
    if not isinstance(retries, dict):
        raise ConfigurationError("retries must be a dictionary")

    if "agent_call" not in retries:
        raise ConfigurationError("retries.agent_call is required")
    agent_call = retries["agent_call"]
    if not isinstance(agent_call, int) or agent_call < 0:
        raise ConfigurationError("retries.agent_call must be a non-negative integer")

    transient = retries.get("transient", [])
    if transient is not None and (
        not isinstance(transient, list) or not all(isinstance(item, str) for item in transient)
    ):
        raise ConfigurationError("retries.transient must be a list of exception names")

    # Validate enabled_intents
    enabled_intents = config["enabled_intents"]
    if not isinstance(enabled_intents, list):
        raise ConfigurationError("enabled_intents must be a list")

    valid_intents = [
        "pattern.anomalies",
        "pattern.correlation",
        "pattern.root_causes",
        "pattern.best_practices",
        "strategy.gcc_benchmark",
        "strategy.talent_competition",
        "strategy.vision2030",
    ]

    for intent in enabled_intents:
        if intent not in valid_intents:
            raise ConfigurationError(f"Invalid intent: {intent}")

    logger.debug("Configuration validated successfully")


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Merge two configuration dictionaries.

    Args:
        base: Base configuration
        override: Override configuration

    Returns:
        Merged configuration
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result
