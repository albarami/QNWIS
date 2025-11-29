"""
QNWIS Deterministic Calculation Engines.

This package provides domain-agnostic calculation engines that perform
all financial and analytical computations using deterministic Python math.

CRITICAL PRINCIPLE: LLMs are BANNED from doing math.
All calculations happen here, in pure Python.
"""

from .financial_engine import (
    CashFlowInput,
    FinancialModelInput,
    FinancialModelOutput,
    SensitivityScenario,
    FinancialEngine,
    calculate_simple_npv,
    calculate_simple_irr,
)

__all__ = [
    "CashFlowInput",
    "FinancialModelInput",
    "FinancialModelOutput",
    "SensitivityScenario",
    "FinancialEngine",
    "calculate_simple_npv",
    "calculate_simple_irr",
]

