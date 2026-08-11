# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""HTMX request details + pure ASGI middleware.

Breaking (0.5): no longer subclasses Starlette ``BaseHTTPMiddleware`` (which
breaks streaming responses and contextvars under load). Usage is unchanged::

    app.add_middleware(HtmxMiddleware)
    # request.state.htmx → HtmxDetails
"""

from __future__ import annotations

import json
from functools import cached_property
from typing import Any, Mapping, Optional
from urllib.parse import unquote

__all__ = ["HtmxDetails", "HtmxMiddleware"]


def _headers_from_scope(scope: dict) -> dict[str, str]:
    return {
        k.decode("latin-1").lower(): v.decode("latin-1")
        for k, v in scope.get("headers", [])
    }


class HtmxDetails:
    """HTMX request headers.

    Accepts a Starlette/FastAPI ``Request``, a header mapping, or an ASGI scope.
    """

    def __init__(self, request_or_scope: Any) -> None:
        headers: Any
        if isinstance(request_or_scope, dict) and "type" in request_or_scope:
            headers = _headers_from_scope(request_or_scope)
        elif hasattr(request_or_scope, "headers"):
            headers = request_or_scope.headers
        elif isinstance(request_or_scope, Mapping):
            headers = request_or_scope
        else:
            headers = {}
        self._headers = headers

    def _get_header_value(self, name: str) -> Optional[str]:
        headers = self._headers
        value = headers.get(name)
        if value is None and hasattr(headers, "get"):
            value = headers.get(name.lower())
        if not value:
            return None
        auto = headers.get(f"{name}-URI-AutoEncoded")
        if auto is None:
            auto = headers.get(f"{name.lower()}-uri-autoencoded")
        if auto == "true":
            value = unquote(value)
        return value

    def __bool__(self) -> bool:
        return self._get_header_value("HX-Request") == "true"

    @cached_property
    def boosted(self) -> bool:
        return self._get_header_value("HX-Boosted") == "true"

    @cached_property
    def current_url(self) -> Optional[str]:
        return self._get_header_value("HX-Current-URL")

    @cached_property
    def history_restore_request(self) -> bool:
        return self._get_header_value("HX-History-Restore-Request") == "true"

    @cached_property
    def prompt(self) -> Optional[str]:
        return self._get_header_value("HX-Prompt")

    @cached_property
    def target(self) -> Optional[str]:
        return self._get_header_value("HX-Target")

    @cached_property
    def trigger(self) -> Optional[str]:
        return self._get_header_value("HX-Trigger")

    @cached_property
    def trigger_name(self) -> Optional[str]:
        return self._get_header_value("HX-Trigger-Name")

    @cached_property
    def triggering_event(self) -> Any:
        value = self._get_header_value("Triggering-Event") or self._get_header_value(
            "HX-Triggering-Event"
        )
        if value is not None:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = None
        return value


class HtmxMiddleware:
    """Pure ASGI middleware — safe with StreamingResponse and contextvars.

    Compatible with ``app.add_middleware(HtmxMiddleware)`` on Starlette/FastAPI.
    Sets ``scope["state"]["htmx"]`` so ``request.state.htmx`` works.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive, send) -> None:
        if scope["type"] == "http":
            state = scope.setdefault("state", {})
            details = HtmxDetails(scope)
            # Starlette State is a dict-backed object when built from scope["state"]
            if isinstance(state, dict):
                state["htmx"] = details
            else:
                try:
                    state.htmx = details  # type: ignore[attr-defined]
                except Exception:
                    pass
        await self.app(scope, receive, send)
