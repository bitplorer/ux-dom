"""Starlette/FastAPI response **adapter** for ux-dom trees.

Domain prepare lives in ``ux_dom.response.serialize`` (no framework imports).
This module only wraps Starlette response classes.
"""
import inspect

# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


import typing as T
from functools import wraps

from starlette.background import BackgroundTask
from starlette.responses import HTMLResponse as StarletteHTMLResponse
from starlette.responses import StreamingResponse as StarletteStreamingResponse

from ux_dom.response.serialize import (
    is_html_renderable,
    is_stream_renderable,
    prepare_html_body,
    prepare_html_stream,
)

__all__ = ["HTMLResponse", "html_response", "StreamingResponse", "streaming_response"]



def _response_decorator(
    endpoint: T.Optional[T.Callable[..., T.Any]],
    is_renderable: T.Callable[[T.Any], bool],
    response_cls: T.Callable[[T.Any], T.Any],
) -> T.Callable[..., T.Any]:
    """Wrap ``endpoint`` so renderable results become ``response_cls``.

    Called with ``endpoint=None`` (``@deco()``), return the bare decorator.
    Other results (e.g. a ready ``Response``) pass through unchanged.
    """
    if endpoint is None:
        return lambda fn: _response_decorator(fn, is_renderable, response_cls)

    if inspect.iscoroutinefunction(endpoint):

        @wraps(endpoint)
        async def decorated(*args, **kwargs):
            content = await endpoint(*args, **kwargs)
            return response_cls(content) if is_renderable(content) else content

    else:

        @wraps(endpoint)
        def decorated(*args, **kwargs):
            content = endpoint(*args, **kwargs)
            return response_cls(content) if is_renderable(content) else content

    return decorated


class HTMLResponse(StarletteHTMLResponse):
    media_type = "text/html"

    def __init__(
        self,
        html_content: T.Any,
        status_code: int = 200,
        headers: T.Optional[dict] = None,
        media_type: T.Optional[str] = None,
        background: T.Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(html_content, status_code, headers, media_type, background)

    def render(self, content: T.Any) -> bytes:
        # Domain prepare (CSP + __render__) — no framework logic here
        content = prepare_html_body(content)
        return super().render(content=content)  # type: ignore[return-value]


def html_response(
    endpoint: T.Optional[T.Callable[..., T.Any]] = None,
) -> T.Callable[..., T.Any]:
    """Decorator: renderable endpoint results become :class:`HTMLResponse`.

    Use as ``@html_response`` or ``@html_response()``; sync and async endpoints.
    """
    return _response_decorator(endpoint, is_html_renderable, HTMLResponse)


class StreamingResponse(StarletteStreamingResponse):
    """Stream HTML (or raw bytes) to the client.

    Accepts:
    * ``dom_tag`` — ``__async_render__(pretty=False)`` token stream (preferred)
    * object with ``__async_render__`` (e.g. Compose Component)
    * ``str`` / ``bytes`` / ``bytearray`` — single-chunk body
    * async iterator / async generator — passed through
    """

    media_type = "text/html"

    def __init__(
        self,
        html_content,
        status_code: int = 200,
        headers: T.Optional[dict] = None,
        media_type: T.Optional[str] = None,
        background: T.Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(
            prepare_html_stream(html_content),
            status_code,
            headers,
            media_type,
            background,
        )


def streaming_response(
    endpoint: T.Optional[T.Callable[..., T.Any]] = None,
) -> T.Callable[..., T.Any]:
    """Decorator: stream-renderable endpoint results become :class:`StreamingResponse`.

    Use as ``@streaming_response`` or ``@streaming_response()``; sync and async endpoints.
    """
    return _response_decorator(endpoint, is_stream_renderable, StreamingResponse)
