"""
Pagination utilities for QNWIS UI rendering.

Provides helpers to paginate large result sets and avoid rendering
performance issues with massive tables.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypeVar

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 1000
MAX_PAGE_SIZE = 5000


def paginate(
    items: List[T],
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        page_size: Items per page (default: 1000, max: 5000)
        
    Returns:
        Dictionary with paginated results and metadata
        
    Example:
        >>> items = list(range(100))
        >>> result = paginate(items, page=1, page_size=25)
        >>> len(result["items"])
        25
        >>> result["total_items"]
        100
        >>> result["total_pages"]
        4
    """
    # Clamp page_size
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    
    # Clamp page number
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    page = max(1, min(page, total_pages))
    
    # Calculate slice
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return {
        "items": items[start_idx:end_idx],
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def should_paginate(item_count: int, threshold: int = 1000) -> bool:
    """
    Determine if a result set should be paginated.
    
    Args:
        item_count: Number of items in result set
        threshold: Threshold for pagination (default: 1000)
        
    Returns:
        True if pagination is recommended
        
    Example:
        >>> should_paginate(500)
        False
        >>> should_paginate(1500)
        True
    """
    return item_count > threshold


def render_pagination_info(page_info: Dict[str, Any]) -> str:
    """
    Render pagination info as markdown.
    
    Args:
        page_info: Pagination metadata from paginate()
        
    Returns:
        Markdown string with pagination info
        
    Example:
        >>> info = {"page": 2, "total_pages": 5, "total_items": 1234}
        >>> render_pagination_info(info)
        'Page 2 of 5 (1,234 total items)'
    """
    return (
        f"Page {page_info['page']} of {page_info['total_pages']} "
        f"({page_info['total_items']:,} total items)"
    )


def chunk_for_rendering(
    items: List[T],
    chunk_size: int = 100,
) -> List[List[T]]:
    """
    Split items into chunks for progressive rendering.
    
    Useful for streaming large result sets to UI without blocking.
    
    Args:
        items: List of items to chunk
        chunk_size: Items per chunk (default: 100)
        
    Returns:
        List of chunks
        
    Example:
        >>> items = list(range(250))
        >>> chunks = chunk_for_rendering(items, chunk_size=100)
        >>> len(chunks)
        3
        >>> len(chunks[0])
        100
        >>> len(chunks[-1])
        50
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
