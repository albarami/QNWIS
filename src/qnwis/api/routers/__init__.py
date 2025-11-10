"""API router registry for server autoload."""

from . import (
    agents_pattern,
    agents_predictor,
    agents_scenario,
    agents_strategy,
    agents_time,
    notifications,
)

ROUTERS = [
    agents_time.router,
    agents_pattern.router,
    agents_predictor.router,
    agents_scenario.router,
    agents_strategy.router,
    notifications.router,
]

__all__ = ["ROUTERS"]
