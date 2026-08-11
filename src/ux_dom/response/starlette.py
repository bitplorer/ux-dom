"""Starlette/FastAPI response adapters for ux-dom trees.

HTMLResponse buffers; StreamingResponse uses compact token walk (pretty=False).
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

__all__ = ["HTMLResponse", "html_response", "StreamingResponse", "streaming_response"]

CallableType = T.TypeVar("CallableType", bound=T.Callable[..., T.Any])


class HTMLResponse(StarletteHTMLResponse):
    media_type = "text/html"

    def __init__(
        self,
        html_content: dom_tag.dom_tag,
        status_code: int = 200,
        headers: T.Optional[dict] = None,
        media_type: T.Optional[str] = None,
        background: T.Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(html_content, status_code, headers, media_type, background)

    def render(self, content: T.Any) -> bytes:
        # CSP: if middleware set a request nonce, stamp script/style in the tree
        try:
            from ux_dom.plugins.csp import get_nonce, resolve_nonce, stamp_tree

            n = resolve_nonce()
            if n and content is not None:
                stamp_tree(content, n)  # bake nonce — serialize is read-agnostic
        except Exception:
            pass
        if hasattr(content, "__render__"):
            content = content.__render__()
        elif isinstance(content, str):
            try:
                from ux_dom.plugins.csp import get_nonce, stamp_nonce

                if get_nonce():
                    content = stamp_nonce([content])[0]
            except Exception:
                pass
        return super().render(content=content)  # type: ignore[return-value]


def html_response(
    endpoint: T.Optional[CallableType] = None,
) -> T.Callable[..., HTMLResponse]:
    def decorate_sync_async(endpoint):
        if inspect.iscoroutinefunction(endpoint):

            @wraps(endpoint)
            async def decorated(*args, **kwargs) -> HTMLResponse:
                content = await endpoint(*args, **kwargs)
                if isinstance(content, dom_tag.dom_tag):
                    return HTMLResponse(content)
                return content

        else:

            @wraps(endpoint)
            def decorated(*args, **kwargs) -> HTMLResponse:
                content = endpoint(*args, **kwargs)
                if isinstance(content, dom_tag.dom_tag):
                    return HTMLResponse(content)
                return content

        decorated.__doc__ = endpoint.__doc__
        return decorated

    return decorate_sync_async(endpoint)


class StreamingResponse(StarletteStreamingResponse):
    """Stream HTML (or raw bytes) to the client.

    Accepts:
    * ``dom_tag`` — ``__async_render__(pretty=False)`` token stream (preferred)
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


async def _async_bytes_chunks(data: bytes):
    yield data


async def _async_str_chunks(data: str):
    yield data


def _coerce_streaming_body(html_content):
    """Normalize constructor input to an async iterable body."""
    if html_content is None:
        return _async_str_chunks("")

    # Prefer dom_tag async stream
    if isinstance(html_content, dom_tag.dom_tag) or hasattr(
        html_content, "__async_render__"
    ):
        try:
            from ux_dom.plugins.csp import resolve_nonce, stamp_tree

            n = resolve_nonce()
            if n:
                # Bake on request Task BEFORE any pretty/worker stream.
                # After this, tree attributes carry the nonce (read-agnostic).
                stamp_tree(html_content, n)
        except Exception:
            pass
        return html_content.__async_render__(pretty=False)

    if isinstance(html_content, (bytes, bytearray, memoryview)):
        return _async_bytes_chunks(bytes(html_content))

    if isinstance(html_content, str):
        return _async_str_chunks(html_content)

    # Already an async iterator / generator?
    if hasattr(html_content, "__aiter__"):
        return html_content

    raise TypeError(
        "StreamingResponse expects a dom_tag, str, bytes, or async iterator; "
        f"got {type(html_content)!r}"
    )


def streaming_response(
    endpoint: T.Optional[CallableType] = None,
) -> T.Callable[..., StreamingResponse]:
    def decorate_sync_async(endpoint):
        if inspect.iscoroutinefunction(endpoint):

            @wraps(endpoint)
            async def decorated(*args, **kwargs) -> StreamingResponse:
                content = await endpoint(*args, **kwargs)
                if isinstance(content, dom_tag.dom_tag):
                    return StreamingResponse(content)
                return content

        else:

            @wraps(endpoint)
            def decorated(*args, **kwargs) -> StreamingResponse:
                content = endpoint(*args, **kwargs)
                if isinstance(content, dom_tag.dom_tag):
                    return StreamingResponse(content)
                return content

        decorated.__doc__ = endpoint.__doc__
        return decorated

    return decorate_sync_async(endpoint)
