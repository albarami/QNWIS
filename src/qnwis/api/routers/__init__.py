"""API router registry for server autoload."""

from . import (
    agents_pattern,
    agents_predictor,
    agents_scenario,
    agents_strategy,
    agents_time,
    backups,
    briefing,
    continuity,
    council,
    export,
    notifications,
    queries,
    slo,
    ui,
    ui_dashboard,
)

ROUTERS = [
    agents_time.router,
    agents_pattern.router,
    agents_predictor.router,
    agents_scenario.router,
    agents_strategy.router,
    queries.router,
    export.router,
    ui.router,
    ui_dashboard.router,
    council.router,
    continuity.router,
    backups.router,
    briefing.router,
    slo.router,
    notifications.router,
]

__all__ = ["ROUTERS"]
