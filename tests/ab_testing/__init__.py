"""
Comprehensive A/B Testing Framework for QNWIS.

This module provides thorough testing of all data sources, APIs,
databases, and extraction accuracy for the ministerial-grade system.
"""

from .ground_truth_data import (
    QATAR_GROUND_TRUTH,
    GCC_BENCHMARK_DATA,
    TEST_QUERIES,
    GroundTruthValue,
    TestQuery,
    get_ground_truth,
    get_all_domains,
    get_indicators_for_domain,
)

__all__ = [
    "QATAR_GROUND_TRUTH",
    "GCC_BENCHMARK_DATA", 
    "TEST_QUERIES",
    "GroundTruthValue",
    "TestQuery",
    "get_ground_truth",
    "get_all_domains",
    "get_indicators_for_domain",
]

