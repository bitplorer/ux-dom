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

from ux_dom.dom.src import dom_tag
from ux_dom.response.serialize import (
    is_html_renderable,
    is_stream_renderable,
    prepare_html_body,
    prepare_html_stream,
)

__all__ = ["HTMLResponse", "html_response", "StreamingResponse", "streaming_response"]

CallableType = T.TypeVar("CallableType", bound=T.Callable[..., T.Any])


def _is_html_renderable(content: T.Any) -> bool:
    return is_html_renderable(content)


def _is_stream_renderable(content: T.Any) -> bool:
    return is_stream_renderable(content)


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
    endpoint: T.Optional[CallableType] = None,
) -> T.Callable[..., HTMLResponse]:
    def decorate_sync_async(endpoint):
        if inspect.iscoroutinefunction(endpoint):

            @wraps(endpoint)
            async def decorated(*args, **kwargs) -> HTMLResponse:
                content = await endpoint(*args, **kwargs)
                if _is_html_renderable(content):
                    return HTMLResponse(content)
                return content

        else:

            @wraps(endpoint)
            def decorated(*args, **kwargs) -> HTMLResponse:
                content = endpoint(*args, **kwargs)
                if _is_html_renderable(content):
                    return HTMLResponse(content)
                return content

        decorated.__doc__ = endpoint.__doc__
        return decorated

    return decorate_sync_async(endpoint)


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
        body = _coerce_streaming_body(html_content)
        super().__init__(
            body,
            status_code,
            headers,
            media_type,
            background,
        )


def _coerce_streaming_body(html_content):
    """Adapter thin wrap — domain prepare lives in serialize.prepare_html_stream."""
    return prepare_html_stream(html_content)


def streaming_response(
    endpoint: T.Optional[CallableType] = None,
) -> T.Callable[..., StreamingResponse]:
    def decorate_sync_async(endpoint):
        if inspect.iscoroutinefunction(endpoint):

            @wraps(endpoint)
            async def decorated(*args, **kwargs) -> StreamingResponse:
                content = await endpoint(*args, **kwargs)
                if _is_stream_renderable(content):
                    return StreamingResponse(content)
                return content

        else:

            @wraps(endpoint)
            def decorated(*args, **kwargs) -> StreamingResponse:
                content = endpoint(*args, **kwargs)
                if _is_stream_renderable(content):
                    return StreamingResponse(content)
                return content

        decorated.__doc__ = endpoint.__doc__
        return decorated

    return decorate_sync_async(endpoint)
