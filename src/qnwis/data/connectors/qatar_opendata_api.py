"""Qatar Open Data Portal API v2.1 connector for deterministic queries."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import httpx

from ..deterministic.models import Freshness, Provenance, QueryResult, QuerySpec, Row

logger = logging.getLogger(__name__)

BASE_URL = "https://www.data.gov.qa/api/explore/v2.1"
QATAR_OPEN_DATA_LICENSE = "Qatar Open Data Portal License (CC BY 4.0)"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5


def _build_api_url(dataset_id: str) -> str:
    """Construct the API endpoint URL for a dataset."""
    return f"{BASE_URL}/catalog/datasets/{dataset_id}/records"


def _parse_params(spec: QuerySpec) -> dict[str, Any]:
    """Extract and validate parameters from QuerySpec."""
    params = spec.params or {}
    
    dataset_id = params.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("Qatar API query requires a non-empty 'dataset_id' parameter.")
    
    # Build query parameters for the API
    query_params: dict[str, Any] = {}
    
    # Limit (max records to fetch)
    limit = params.get("limit", 100)
    if isinstance(limit, int) and limit > 0:
        query_params["limit"] = min(limit, 10000)  # API max is 10000
    
    # Offset (for pagination)
    offset = params.get("offset")
    if isinstance(offset, int) and offset >= 0:
        query_params["offset"] = offset
    
    # Where clause (OData-style filtering)
    where = params.get("where")
    if isinstance(where, str) and where.strip():
        query_params["where"] = where.strip()
    
    # Select fields
    select = params.get("select")
    if isinstance(select, list) and select:
        query_params["select"] = ",".join(str(f) for f in select)
    
    return {
        "dataset_id": dataset_id.strip(),
        "query_params": query_params,
    }


def _fetch_with_retry(
    url: str,
    params: dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    Fetch data from API with exponential backoff retry logic.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON response
        
    Raises:
        httpx.HTTPError: If request fails after retries
        ValueError: If response is not valid JSON
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            last_exception = exc
            if exc.response.status_code >= 500:
                # Server error - retry with backoff
                wait_time = RETRY_BACKOFF ** attempt
                logger.warning(
                    f"API request failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                    f"HTTP {exc.response.status_code}. Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
            else:
                # Client error (4xx) - don't retry
                logger.error(f"Client error from Qatar API: HTTP {exc.response.status_code}")
                raise
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            last_exception = exc
            wait_time = RETRY_BACKOFF ** attempt
            logger.warning(
                f"Network error (attempt {attempt + 1}/{MAX_RETRIES}): {exc}. "
                f"Retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
    
    # All retries exhausted
    raise ValueError(
        f"Failed to fetch data from Qatar API after {MAX_RETRIES} attempts"
    ) from last_exception


def run_qatar_api_query(spec: QuerySpec) -> QueryResult:
    """
    Execute a query against Qatar Open Data API v2.1.
    
    Supported params:
        dataset_id (str): Dataset identifier from data.gov.qa (required)
        where (str, optional): OData-style filter clause (e.g., "year='2020'")
        limit (int, optional): Max records to fetch (default: 100, max: 10000)
        offset (int, optional): Pagination offset (default: 0)
        select (list[str], optional): Fields to return (default: all fields)
    
    Args:
        spec: QuerySpec containing dataset_id and optional filters
        
    Returns:
        QueryResult with rows from API response
        
    Raises:
        ValueError: If dataset_id is missing or API request fails
    """
    parsed = _parse_params(spec)
    dataset_id = parsed["dataset_id"]
    query_params = parsed["query_params"]
    
    url = _build_api_url(dataset_id)
    
    logger.info(f"Querying Qatar API: {dataset_id} with params {query_params}")
    
    try:
        api_response = _fetch_with_retry(url, query_params)
    except Exception as exc:
        raise ValueError(f"Qatar API query failed for dataset '{dataset_id}': {exc}") from exc
    
    # Extract results from API response
    if not isinstance(api_response, dict):
        raise ValueError(f"Invalid API response format: expected dict, got {type(api_response)}")
    
    results = api_response.get("results", [])
    total_count = api_response.get("total_count", len(results))
    
    if not isinstance(results, list):
        raise ValueError(f"Invalid 'results' field in API response: expected list, got {type(results)}")
    
    # Convert API results to Row objects
    rows: list[Row] = []
    for item in results:
        if isinstance(item, dict):
            rows.append(Row(data=item))
        else:
            logger.warning(f"Skipping non-dict result: {type(item)}")
    
    if not rows:
        logger.warning(f"Qatar API returned 0 rows for dataset '{dataset_id}'")
    
    # Determine fields from first row or query params
    fields: list[str] = []
    if rows:
        fields = list(rows[0].data.keys())
    elif "select" in query_params:
        fields = query_params["select"].split(",")
    
    # Determine most recent year for asof_date
    max_year = None
    for row in rows:
        year_value = row.data.get("year")
        if year_value is not None:
            try:
                year = int(year_value)
                max_year = year if (max_year is None or year > max_year) else max_year
            except (TypeError, ValueError):
                pass
    
    asof_date = f"{max_year}-12-31" if max_year else datetime.now().strftime("%Y-%m-%d")
    
    return QueryResult(
        query_id=spec.id,
        rows=rows,
        unit=spec.expected_unit,
        provenance=Provenance(
            source="qatar_api",
            dataset_id=dataset_id,
            locator=url,
            fields=fields,
            license=QATAR_OPEN_DATA_LICENSE,
        ),
        freshness=Freshness(
            asof_date=asof_date,
            updated_at=datetime.now().isoformat(),
        ),
        metadata={
            "total_count": total_count,
            "row_count": len(rows),
            "dataset_id": dataset_id,
        },
        warnings=[f"Fetched {len(rows)} of {total_count} total records"] if len(rows) < total_count else [],
    )


__all__ = ["run_qatar_api_query"]
