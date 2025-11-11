"""
Service Level Objectives (SLO) core primitives.

Deterministic, type-safe SLI/SLO models, loaders, and error-budget math.
"""

from .models import ErrorBudgetSnapshot, SLIKind, SLOTarget

__all__ = [
    "SLIKind",
    "SLOTarget",
    "ErrorBudgetSnapshot",
]
