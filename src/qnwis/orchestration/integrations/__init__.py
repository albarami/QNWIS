"""Integrations package - split from monolithic prefetch_apis.py."""
from .common import classify_query_for_extraction
from .orchestrator import CompletePrefetchLayer, get_complete_prefetch

__all__ = [
    "CompletePrefetchLayer",
    "get_complete_prefetch",
    "classify_query_for_extraction",
]
