"""
Alert rule registry for loading and validating rule sets.

Supports YAML and JSON rule definitions with deterministic ordering.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

import yaml

from .rules import AlertRule

logger = logging.getLogger(__name__)


class AlertRegistry:
    """
    Registry for alert rule definitions.

    Loads rules from YAML/JSON files and maintains validated rule sets
    with deterministic ordering.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._rules: dict[str, AlertRule] = {}
        self._load_order: list[str] = []

    def load_file(self, path: str | Path) -> int:
        """
        Load alert rules from a file.

        Supports both YAML and JSON formats. Rules are loaded in deterministic
        order based on file content.

        Args:
            path: Path to rule definition file

        Returns:
            Number of rules successfully loaded

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Rule file not found: {path}")

        suffix = file_path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            return self._load_yaml(file_path)
        elif suffix == ".json":
            return self._load_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _load_yaml(self, path: Path) -> int:
        """Load rules from YAML file."""
        try:
            loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)  # type: ignore[attr-defined]
            with open(path, encoding="utf-8") as f:
                data = yaml.load(f, Loader=loader)  # type: ignore[attr-defined]
            return self._load_rules_from_data(data, str(path))
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {path}: {e}")
            raise ValueError(f"Invalid YAML: {e}") from e

    def _load_json(self, path: Path) -> int:
        """Load rules from JSON file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self._load_rules_from_data(data, str(path))
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in {path}: {e}")
            raise ValueError(f"Invalid JSON: {e}") from e

    def _load_rules_from_data(self, data: Any, source: str) -> int:
        """
        Parse and validate rules from loaded data.

        Args:
            data: Parsed YAML/JSON data
            source: Source file path for error reporting

        Returns:
            Number of rules loaded
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict at root, got {type(data).__name__}")

        rules_list = data.get("rules", [])
        if not isinstance(rules_list, list):
            raise ValueError("'rules' key must contain a list")

        loaded_count = 0
        for idx, rule_data in enumerate(rules_list):
            try:
                rule = AlertRule.model_validate(rule_data)
                self.add_rule(rule)
                loaded_count += 1
            except ValidationError as e:
                logger.warning(f"Validation error for rule {idx} in {source}: {e}")
                # Continue loading other rules

        logger.info(f"Loaded {loaded_count}/{len(rules_list)} rules from {source}")
        return loaded_count

    def add_rule(self, rule: AlertRule) -> None:
        """
        Add a validated rule to the registry.

        Args:
            rule: Validated AlertRule instance
        """
        if rule.rule_id in self._rules:
            logger.warning(f"Overwriting existing rule: {rule.rule_id}")
            # Remove from load order if present
            if rule.rule_id in self._load_order:
                self._load_order.remove(rule.rule_id)

        self._rules[rule.rule_id] = rule
        self._load_order.append(rule.rule_id)

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """
        Retrieve a rule by ID.

        Args:
            rule_id: Rule identifier

        Returns:
            AlertRule if found, None otherwise
        """
        return self._rules.get(rule_id)

    def get_all_rules(self, enabled_only: bool = False) -> list[AlertRule]:
        """
        Get all rules in deterministic load order.

        Args:
            enabled_only: If True, return only enabled rules

        Returns:
            List of AlertRule instances
        """
        rules = [self._rules[rule_id] for rule_id in self._load_order]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def get_rules_by_metric(self, metric: str) -> list[AlertRule]:
        """
        Get all rules for a specific metric.

        Args:
            metric: Metric name

        Returns:
            List of AlertRule instances
        """
        return [r for r in self.get_all_rules() if r.metric == metric]

    def get_rules_by_severity(self, severity: str) -> list[AlertRule]:
        """
        Get all rules with a specific severity.

        Args:
            severity: Severity level (low, medium, high, critical)

        Returns:
            List of AlertRule instances
        """
        return [r for r in self.get_all_rules() if r.severity.value == severity]

    def validate_all(self) -> tuple[bool, list[str]]:
        """
        Validate all loaded rules.

        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []
        for rule_id, rule in self._rules.items():
            try:
                # Re-validate using Pydantic
                AlertRule.model_validate(rule.model_dump())
            except ValidationError as e:
                errors.append(f"{rule_id}: {e}")

        return len(errors) == 0, errors

    def clear(self) -> None:
        """Clear all loaded rules."""
        self._rules.clear()
        self._load_order.clear()

    def __len__(self) -> int:
        """Return number of loaded rules."""
        return len(self._rules)

    def __contains__(self, rule_id: str) -> bool:
        """Check if rule ID exists in registry."""
        return rule_id in self._rules
