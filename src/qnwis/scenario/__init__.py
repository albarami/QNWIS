"""
Scenario Planner - Deterministic forecast adjustments and what-if analysis.

This module provides typed scenario specifications, deterministic transforms,
and QA metrics for LMIS labour market forecasting scenarios.
"""

from .apply import apply_scenario
from .dsl import ScenarioSpec, parse_scenario
from .qa import backtest_forecast, stability_check

__all__ = [
    "ScenarioSpec",
    "parse_scenario",
    "apply_scenario",
    "backtest_forecast",
    "stability_check",
]
