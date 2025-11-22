"""
Async SSE client for QNWIS UI streaming.

Provides a robust, retry-capable client for consuming Server-Sent Events
from the LLM council workflow API with request correlation and heartbeat handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class SSEValidationError(ValueError):
    """Raised when an SSE payload does not satisfy the contract."""


@dataclass(frozen=True)
class WorkflowEvent:
    """
    Parsed event from the workflow SSE stream.

    Attributes:
        stage: Stage name (classify, prefetch, agent:*, verify, synthesize, done)
        status: Status (running, streaming, complete, error, warning)
        payload: Stage-specific data (tokens, results, errors)
        latency_ms: Stage completion latency in milliseconds
        timestamp: ISO-8601 timestamp when event was generated
        request_id: Correlation ID for tracing across logs
    """

    stage: str
    status: str
    payload: dict[str, Any]
    latency_ms: Optional[float]
    timestamp: str
    request_id: str


class SSEClient:
    """
    Minimal, robust SSE client around httpx for QNWIS streaming.

    Features:
    - Sends X-Request-ID and propagates to events for correlation
    - Handles keepalive/heartbeat lines gracefully
    - Yields parsed WorkflowEvent objects
    - Retries with exponential backoff on transient network faults
    - Non-blocking async iteration

    Example:
        ```python
        client = SSEClient("http://localhost:8001")
        async for event in client.stream(question="Test", provider="anthropic"):
            if event.status == "streaming":
                print(event.payload.get("token"), end="", flush=True)
        ```
    """

    _ALLOWED_PROVIDERS = {"anthropic", "openai"}
    _MIN_QUESTION_LEN = 3
    _MAX_QUESTION_LEN = 5000

    def __init__(self, base_url: str, timeout: float = 120.0, api_key: str | None = None):
        """
        Initialize SSE client.

        Args:
            base_url: Base URL of the API (e.g., http://localhost:8001)
            timeout: Request timeout in seconds (default: 120s for long workflows)
            api_key: Optional API key for authentication
        """
        self.base_url = self._validate_base_url(base_url)
        self.timeout = timeout
        self.api_key = api_key
        self.log = logging.getLogger(__name__)

    async def stream(
        self,
        question: str,
        provider: str = "anthropic",
        model: Optional[str] = None,
        request_id: str | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """
        Stream workflow events from the LLM council API.

        Args:
            question: User question to analyze
            provider: LLM provider (anthropic, openai)
            model: Optional model override
            request_id: Optional correlation ID to propagate (auto-generated if omitted)

        Yields:
            WorkflowEvent objects as they arrive from the API

        Raises:
            httpx.HTTPStatusError: On HTTP errors (4xx, 5xx)
            httpx.ConnectError: If all retry attempts fail
            httpx.ReadTimeout: If request times out after retries
        """
        question = question.strip()
        self._validate_question(question)

        normalized_provider = self._normalize_provider(provider)
        url = f"{self.base_url}/api/v1/council/stream"
        request_id = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": request_id}
        
        # Add API key if provided
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {"question": question, "provider": normalized_provider}
        if model:
            cleaned_model = model.strip()
            if cleaned_model:
                payload["model"] = cleaned_model

        # Exponential backoff: 0.5s, 1s, 2s
        delay = 0.5
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as http_client:
                    async with http_client.stream(
                        "POST", url, json=payload, headers=headers
                    ) as resp:
                        resp.raise_for_status()

                        async for event in self._iterate_sse(resp, request_id):
                            yield event

                # Successful stream completion
                return

            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as e:
                self._log_with_request_id(
                    request_id,
                    "warning",
                    f"SSE attempt {attempt + 1}/{max_attempts} failed: {e}",
                )

                if attempt == max_attempts - 1:
                    # Last attempt failed, re-raise
                    raise

                # Wait before retry with exponential backoff
                await asyncio.sleep(delay)
                delay *= 2

            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx/5xx errors
                self._log_with_request_id(
                    request_id,
                    "error",
                    f"SSE HTTP error: {e.response.status_code} "
                    f"{e.response.text[:200]}",
                )
                raise

    async def _iterate_sse(
        self, response: httpx.Response, request_id: str
    ) -> AsyncIterator[WorkflowEvent]:
        """
        Iterate over SSE lines, assembling payloads and yielding WorkflowEvents.
        """
        buffer: list[str] = []
        current_event_type: Optional[str] = None

        async for raw_line in response.aiter_lines():
            if raw_line is None:
                continue

            line = raw_line.strip()

            if not line:
                if current_event_type == "heartbeat":
                    buffer.clear()
                    current_event_type = None
                    continue

                if buffer:
                    data = "\n".join(buffer)
                    buffer.clear()
                    event = self._build_event(data, request_id)
                    if event:
                        yield event
                current_event_type = None
                continue

            if line.startswith("event:"):
                current_event_type = line.split(":", 1)[1].strip()
                if current_event_type == "heartbeat":
                    self._log_with_request_id(request_id, "debug", "heartbeat")
                continue

            if line.startswith("data:"):
                if current_event_type == "heartbeat":
                    # Ignore heartbeat payloads
                    continue
                buffer.append(line[6:])
                continue

            # Unknown line - log for observability but continue streaming
            self._log_with_request_id(
                request_id,
                "debug",
                f"Ignoring SSE line: {line[:80]}",
            )

        # Flush any remaining buffered data when stream closes
        if buffer:
            data = "\n".join(buffer)
            event = self._build_event(data, request_id)
            if event:
                yield event

    def _build_event(self, data: str, request_id: str) -> WorkflowEvent:
        """Parse JSON data into a WorkflowEvent with schema validation."""
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            self._log_with_request_id(
                request_id,
                "warning",
                f"Malformed SSE JSON: {exc}",
            )
            return self._warning_event(
                request_id, "Received malformed JSON from streaming API."
            )

        try:
            event_dict = self._validate_event_schema(parsed)
        except SSEValidationError as exc:
            self._log_with_request_id(
                request_id,
                "warning",
                f"Invalid SSE payload: {exc}",
            )
            return self._warning_event(request_id, str(exc))

        workflow_event = WorkflowEvent(
            stage=event_dict["stage"],
            status=event_dict["status"],
            payload=event_dict["payload"],
            latency_ms=event_dict["latency_ms"],
            timestamp=event_dict["timestamp"],
            request_id=request_id,
        )
        self._log_with_request_id(
            request_id,
            "debug",
            f"stage={workflow_event.stage} status={workflow_event.status}",
        )
        return workflow_event

    def _warning_event(self, request_id: str, message: str) -> WorkflowEvent:
        """Create a warning WorkflowEvent surfaced to the UI."""
        return WorkflowEvent(
            stage="client",
            status="warning",
            payload={"warning": message},
            latency_ms=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        )

    @classmethod
    def _validate_event_schema(cls, data: Any) -> dict[str, Any]:
        """Validate SSE JSON payload and return normalized values."""
        if not isinstance(data, dict):
            raise SSEValidationError("Event payload must be a JSON object.")

        stage = str(data.get("stage", "")).strip()
        status = str(data.get("status", "")).strip()
        if not stage:
            raise SSEValidationError("Event missing 'stage'.")
        if not status:
            raise SSEValidationError("Event missing 'status'.")

        payload = data.get("payload") or {}
        if not isinstance(payload, dict):
            raise SSEValidationError("Event payload field must be an object.")

        if status == "streaming" and "token" in payload:
            token = payload["token"]
            if token is not None and not isinstance(token, str):
                raise SSEValidationError("Streaming token must be a string.")

        latency_ms = data.get("latency_ms")
        if latency_ms is not None:
            try:
                latency_ms = float(latency_ms)
            except (TypeError, ValueError):
                raise SSEValidationError("latency_ms must be numeric.") from None

        timestamp = str(data.get("timestamp") or "").strip()
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "stage": stage,
            "status": status,
            "payload": payload,
            "latency_ms": latency_ms,
            "timestamp": timestamp,
        }

    @classmethod
    def _validate_base_url(cls, base_url: str) -> str:
        """Ensure the base URL includes scheme and host."""
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid base URL for SSE client: {base_url!r}")
        return base_url.rstrip("/")

    @classmethod
    def _normalize_provider(cls, provider: str) -> str:
        """Validate provider against allowed set."""
        value = (provider or "").strip().lower()
        if value not in cls._ALLOWED_PROVIDERS:
            allowed = ", ".join(sorted(cls._ALLOWED_PROVIDERS))
            raise ValueError(
                f"Provider '{provider}' is not supported. Allowed: {allowed}."
            )
        return value

    @classmethod
    def _validate_question(cls, question: str) -> None:
        """Validate question length boundaries."""
        length = len(question)
        if length < cls._MIN_QUESTION_LEN or length > cls._MAX_QUESTION_LEN:
            raise ValueError(
                "Question must be between "
                f"{cls._MIN_QUESTION_LEN} and {cls._MAX_QUESTION_LEN} characters."
            )

    def _log_with_request_id(self, request_id: str, level: str, message: str) -> None:
        """Log helper that prefixes entries with rid/stage/status."""
        log_line = f"rid={request_id} {message}"
        getattr(self.log, level, self.log.info)(log_line)
