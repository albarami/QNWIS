"""
UI builders and helpers for QNWIS frontend components.

Provides deterministic card and chart data builders using the DataAPI.
All functions work entirely on synthetic CSV data without network/SQL/LLM calls.
"""

from __future__ import annotations

__all__ = ["cards", "charts"]
