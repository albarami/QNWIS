"""
NSIC Scenario Loader

Loads deterministic scenario definitions from YAML files.

Each scenario contains:
- Unique ID and metadata
- Input parameters
- Expected structure
- Validation rules
- Retry configuration
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ScenarioInput:
    """Input parameters for a scenario."""
    variable: str
    base_value: float
    shock_value: float
    shock_type: str  # "absolute", "percentage"
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "base_value": self.base_value,
            "shock_value": self.shock_value,
            "shock_type": self.shock_type,
            "unit": self.unit,
        }


@dataclass
class ValidationRule:
    """Validation rule for scenario output."""
    field: str
    rule_type: str  # "required", "range", "format", "contains"
    params: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "rule_type": self.rule_type,
            "params": self.params,
            "message": self.message,
        }


@dataclass
class RetryConfig:
    """Retry configuration for scenario execution."""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    retry_on_errors: List[str] = field(default_factory=lambda: ["timeout", "rate_limit"])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "exponential_backoff": self.exponential_backoff,
            "retry_on_errors": self.retry_on_errors,
        }


@dataclass
class ScenarioDefinition:
    """Complete scenario definition."""
    id: str
    name: str
    domain: str  # "economic", "policy", "competitive", "timing", "social"
    description: str
    inputs: List[ScenarioInput]
    expected_structure: Dict[str, Any]
    validation_rules: List[ValidationRule]
    retry_config: RetryConfig
    
    # Optional metadata
    version: str = "1.0"
    author: str = "NSIC"
    tags: List[str] = field(default_factory=list)
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    # Engine assignment
    assigned_engine: str = "auto"  # "engine_a", "engine_b", "auto"
    target_turns: int = 50  # Target number of reasoning turns
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "priority": self.priority,
            "assigned_engine": self.assigned_engine,
            "target_turns": self.target_turns,
            "inputs": [i.to_dict() for i in self.inputs],
            "expected_structure": self.expected_structure,
            "validation_rules": [r.to_dict() for r in self.validation_rules],
            "retry_config": self.retry_config.to_dict(),
        }


class ScenarioLoader:
    """
    Loads and manages scenario definitions from YAML files.
    
    Directory structure:
    scenarios/
      economic/
        scenario_001_oil_50.yaml
        scenario_002_inflation.yaml
      policy/
        scenario_010_trade.yaml
      competitive/
        ...
    """
    
    VALID_DOMAINS = {"economic", "policy", "competitive", "timing", "social"}
    
    def __init__(self, scenarios_dir: str = "scenarios"):
        """
        Initialize scenario loader.
        
        Args:
            scenarios_dir: Root directory containing scenario YAML files
        """
        self.scenarios_dir = Path(scenarios_dir)
        self._scenarios: Dict[str, ScenarioDefinition] = {}
        self._loaded = False
    
    def _parse_input(self, data: Dict[str, Any]) -> ScenarioInput:
        """Parse input definition from YAML data."""
        return ScenarioInput(
            variable=data.get("variable", ""),
            base_value=float(data.get("base_value", 0)),
            shock_value=float(data.get("shock_value", 0)),
            shock_type=data.get("shock_type", "absolute"),
            unit=data.get("unit", ""),
        )
    
    def _parse_rule(self, data: Dict[str, Any]) -> ValidationRule:
        """Parse validation rule from YAML data."""
        return ValidationRule(
            field=data.get("field", ""),
            rule_type=data.get("rule_type", "required"),
            params=data.get("params", {}),
            message=data.get("message", ""),
        )
    
    def _parse_retry(self, data: Optional[Dict[str, Any]]) -> RetryConfig:
        """Parse retry configuration from YAML data."""
        if data is None:
            return RetryConfig()
        
        return RetryConfig(
            max_retries=data.get("max_retries", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
            exponential_backoff=data.get("exponential_backoff", True),
            retry_on_errors=data.get("retry_on_errors", ["timeout", "rate_limit"]),
        )
    
    def _load_yaml_file(self, filepath: Path) -> Optional[ScenarioDefinition]:
        """Load a single scenario from YAML file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty YAML file: {filepath}")
                return None
            
            # Parse components
            inputs = [self._parse_input(i) for i in data.get("inputs", [])]
            rules = [self._parse_rule(r) for r in data.get("validation_rules", [])]
            retry = self._parse_retry(data.get("retry_config"))
            
            scenario = ScenarioDefinition(
                id=data.get("id", filepath.stem),
                name=data.get("name", filepath.stem),
                domain=data.get("domain", "economic"),
                description=data.get("description", ""),
                version=data.get("version", "1.0"),
                author=data.get("author", "NSIC"),
                tags=data.get("tags", []),
                priority=data.get("priority", 1),
                assigned_engine=data.get("assigned_engine", "auto"),
                target_turns=data.get("target_turns", 50),
                inputs=inputs,
                expected_structure=data.get("expected_structure", {}),
                validation_rules=rules,
                retry_config=retry,
            )
            
            return scenario
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading scenario {filepath}: {e}")
            return None
    
    def load_all(self) -> int:
        """
        Load all scenarios from the scenarios directory.
        
        Returns:
            Number of scenarios loaded
        """
        if not self.scenarios_dir.exists():
            logger.warning(f"Scenarios directory not found: {self.scenarios_dir}")
            return 0
        
        self._scenarios.clear()
        count = 0
        
        # Load from each domain subdirectory
        for domain in self.VALID_DOMAINS:
            domain_dir = self.scenarios_dir / domain
            if domain_dir.exists():
                for yaml_file in domain_dir.glob("*.yaml"):
                    scenario = self._load_yaml_file(yaml_file)
                    if scenario:
                        self._scenarios[scenario.id] = scenario
                        count += 1
        
        # Also load from root (for backward compatibility)
        for yaml_file in self.scenarios_dir.glob("*.yaml"):
            scenario = self._load_yaml_file(yaml_file)
            if scenario and scenario.id not in self._scenarios:
                self._scenarios[scenario.id] = scenario
                count += 1
        
        self._loaded = True
        logger.info(f"Loaded {count} scenarios from {self.scenarios_dir}")
        
        return count
    
    def get(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """Get a scenario by ID."""
        if not self._loaded:
            self.load_all()
        return self._scenarios.get(scenario_id)
    
    def get_all(self) -> List[ScenarioDefinition]:
        """Get all loaded scenarios."""
        if not self._loaded:
            self.load_all()
        return list(self._scenarios.values())
    
    def get_by_domain(self, domain: str) -> List[ScenarioDefinition]:
        """Get scenarios filtered by domain."""
        if not self._loaded:
            self.load_all()
        return [s for s in self._scenarios.values() if s.domain == domain]
    
    def get_by_engine(self, engine: str) -> List[ScenarioDefinition]:
        """Get scenarios assigned to a specific engine."""
        if not self._loaded:
            self.load_all()
        return [
            s for s in self._scenarios.values()
            if s.assigned_engine == engine or s.assigned_engine == "auto"
        ]
    
    def get_by_priority(self, priority: int) -> List[ScenarioDefinition]:
        """Get scenarios with specified priority."""
        if not self._loaded:
            self.load_all()
        return [s for s in self._scenarios.values() if s.priority == priority]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded scenarios."""
        if not self._loaded:
            self.load_all()
        
        domain_counts = {}
        engine_counts = {"engine_a": 0, "engine_b": 0, "auto": 0}
        priority_counts = {1: 0, 2: 0, 3: 0}
        
        for scenario in self._scenarios.values():
            domain_counts[scenario.domain] = domain_counts.get(scenario.domain, 0) + 1
            if scenario.assigned_engine in engine_counts:
                engine_counts[scenario.assigned_engine] += 1
            if scenario.priority in priority_counts:
                priority_counts[scenario.priority] += 1
        
        return {
            "total_scenarios": len(self._scenarios),
            "by_domain": domain_counts,
            "by_engine": engine_counts,
            "by_priority": priority_counts,
            "scenarios_dir": str(self.scenarios_dir),
        }


def create_scenario_loader(scenarios_dir: str = "scenarios") -> ScenarioLoader:
    """Factory function to create a ScenarioLoader."""
    return ScenarioLoader(scenarios_dir=scenarios_dir)

