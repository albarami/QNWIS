"""
Streaming response utilities for QNWIS API.

Provides helpers for streaming large result sets to clients without
blocking or consuming excessive memory.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator, Dict, List

from fastapi.responses import StreamingResponse


async def stream_json_array(
    items: List[Dict[str, Any]],
    chunk_size: int = 100,
) -> AsyncGenerator[str, None]:
    """
    Stream a JSON array in chunks.
    
    Yields JSON array opening, items in chunks, and closing bracket.
    Each chunk is a valid JSON fragment that can be parsed incrementally.
    
    Args:
        items: List of dictionaries to stream
        chunk_size: Items per chunk (default: 100)
        
    Yields:
        JSON string fragments
        
    Example:
        >>> async for chunk in stream_json_array([{"id": 1}, {"id": 2}]):
        ...     print(chunk)
    """
    # Yield array opening
    yield "["
    
    total_items = len(items)
    for i in range(0, total_items, chunk_size):
        chunk = items[i:i + chunk_size]
        
        # Serialize chunk
        for j, item in enumerate(chunk):
            item_json = json.dumps(item, separators=(",", ":"))
            
            # Add comma separator except for last item
            if i + j < total_items - 1:
                item_json += ","
            
            yield item_json
    
    # Yield array closing
    yield "]"


async def stream_ndjson(
    items: List[Dict[str, Any]],
    chunk_size: int = 100,
) -> AsyncGenerator[bytes, None]:
    """
    Stream newline-delimited JSON (NDJSON).
    
    Each item is serialized as a single line of JSON.
    Useful for log-style streaming or large datasets.
    
    Args:
        items: List of dictionaries to stream
        chunk_size: Items per chunk (default: 100)
        
    Yields:
        Bytes of NDJSON data
        
    Example:
        >>> async for chunk in stream_ndjson([{"id": 1}, {"id": 2}]):
        ...     print(chunk.decode())
    """
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        
        # Serialize chunk as NDJSON
        lines = [json.dumps(item, separators=(",", ":")) for item in chunk]
        ndjson = "\n".join(lines) + "\n"
        
        yield ndjson.encode("utf-8")


def create_streaming_response(
    items: List[Dict[str, Any]],
    format: str = "json",
    chunk_size: int = 100,
) -> StreamingResponse:
    """
    Create a FastAPI StreamingResponse for large result sets.
    
    Args:
        items: List of dictionaries to stream
        format: Response format ("json" or "ndjson")
        chunk_size: Items per chunk (default: 100)
        
    Returns:
        FastAPI StreamingResponse
        
    Example:
        >>> @app.get("/data")
        ... def get_data():
        ...     items = [{"id": i} for i in range(10000)]
        ...     return create_streaming_response(items, format="json")
    """
    if format == "ndjson":
        return StreamingResponse(
            stream_ndjson(items, chunk_size),
            media_type="application/x-ndjson",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache",
            },
        )
    else:
        return StreamingResponse(
            stream_json_array(items, chunk_size),
            media_type="application/json",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache",
            },
        )


async def stream_with_progress(
    items: List[Dict[str, Any]],
    chunk_size: int = 100,
) -> AsyncGenerator[str, None]:
    """
    Stream JSON with progress metadata.
    
    Wraps items in an envelope with progress information.
    Format: {"progress": {"current": N, "total": M}, "data": [...]}
    
    Args:
        items: List of dictionaries to stream
        chunk_size: Items per chunk (default: 100)
        
    Yields:
        JSON string fragments with progress metadata
    """
    total_items = len(items)
    
    for i in range(0, total_items, chunk_size):
        chunk = items[i:i + chunk_size]
        current = min(i + chunk_size, total_items)
        
        envelope = {
            "progress": {
                "current": current,
                "total": total_items,
                "percent": round(current / total_items * 100, 1) if total_items > 0 else 100,
            },
            "data": chunk,
        }
        
        yield json.dumps(envelope, separators=(",", ":")) + "\n"


def add_timing_header(response: StreamingResponse, duration_ms: float) -> StreamingResponse:
    """
    Add execution time header to streaming response.
    
    Args:
        response: FastAPI StreamingResponse
        duration_ms: Execution time in milliseconds
        
    Returns:
        Response with X-Exec-Time header
    """
    response.headers["X-Exec-Time"] = f"{duration_ms:.2f}ms"
    return response


def should_stream(item_count: int, threshold: int = 1000) -> bool:
    """
    Determine if response should be streamed.
    
    Args:
        item_count: Number of items in response
        threshold: Threshold for streaming (default: 1000)
        
    Returns:
        True if streaming is recommended
        
    Example:
        >>> should_stream(500)
        False
        >>> should_stream(5000)
        True
    """
    return item_count > threshold
