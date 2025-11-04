"""Shared HTTP utilities for API clients."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class RequestMetadata:
    """Metadata about an HTTP request after retry logic."""

    retries: int
    rate_limited: bool


_DEFAULT_BACKOFF = 0.25
_MAX_RETRIES = 2


def send_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_retries: int = _MAX_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    expected_statuses: set[int] | None = None,
    **kwargs: Any,
) -> tuple[httpx.Response, RequestMetadata]:
    """Send an HTTP request with simple retry and rate limit handling.

    Retries on:
        - httpx transport/timeouts
        - HTTP 5xx responses
        - HTTP 429 (one second sleep before retry)
    """
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")

    rate_limited = False
    last_response: httpx.Response | None = None
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = client.request(method, url, **kwargs)
            last_response = response
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exception = exc
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise

        status_code = response.status_code
        if status_code == 429:
            rate_limited = True
            if attempt < max_retries:
                time.sleep(1.0)
                continue

        if 500 <= status_code < 600 and attempt < max_retries:
            time.sleep(backoff * (attempt + 1))
            continue

        if expected_statuses and status_code in expected_statuses:
            return response, RequestMetadata(
                retries=attempt,
                rate_limited=rate_limited,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if (
                attempt < max_retries
                and exc.response is not None
                and 500 <= exc.response.status_code < 600
            ):
                time.sleep(backoff * (attempt + 1))
                continue
            raise

        return response, RequestMetadata(retries=attempt, rate_limited=rate_limited)

    if last_response is not None:
        if expected_statuses and last_response.status_code in expected_statuses:
            return last_response, RequestMetadata(
                retries=max_retries,
                rate_limited=rate_limited,
            )
        last_response.raise_for_status()
        return last_response, RequestMetadata(
            retries=max_retries,
            rate_limited=rate_limited,
        )

    if last_exception is not None:
        raise last_exception

    raise RuntimeError("Request failed without response or exception.")
