"""
Request ID middleware for request tracing.

Adds X-Request-ID header to responses if not already present in the request,
enabling end-to-end request tracing across the system.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestIDMiddleware:
    """ASGI middleware that ensures X-Request-ID header presence."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        """
        Initialize middleware.

        Args:
            app: ASGI application to wrap
            header_name: Header used to propagate the request ID
        """
        self.app = app
        self.header_name = header_name
        self._header_bytes = header_name.lower().encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Process request and ensure X-Request-ID is present on request and response.

        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers = scope.get("headers") or []
        headers = list(
            cast(Sequence[tuple[bytes, bytes]], raw_headers)  # ensure tuple sequence
        )
        request_id: str | None = None
        for name, value in headers:
            if name.lower() == self._header_bytes:
                candidate = value.decode("latin-1").strip()
                if candidate:
                    request_id = candidate
                    break

        if not request_id:
            request_id = uuid4().hex
            headers.append((self._header_bytes, request_id.encode("latin-1")))
            scope["headers"] = headers

        state_obj = scope.get("state")
        if not isinstance(state_obj, dict):
            state_obj = {}
            scope["state"] = state_obj
        state_obj["request_id"] = request_id

        async def send_wrapper(message: Message) -> None:
            if message.get("type") == "http.response.start":
                mutable_headers = MutableHeaders(scope=message)
                mutable_headers[self.header_name] = request_id
            await send(message)

        await self.app(scope, receive, send_wrapper)
