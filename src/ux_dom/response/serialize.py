"""Pure HTML prepare/serialize — no FastAPI/Starlette imports.

Domain boundary: tree / Component / str → body content (or async stream).
HTTP container classes live in ``response.starlette`` (adapter) and call these.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from ux_dom.dom.src import dom_tag

__all__ = [
    "is_html_renderable",
    "is_stream_renderable",
    "prepare_html_body",
    "to_html_bytes",
    "prepare_html_stream",
]


def is_html_renderable(content: Any) -> bool:
    """dom_tag trees or any object exposing ``__render__`` (e.g. Compose Component)."""
    return isinstance(content, dom_tag.dom_tag) or hasattr(content, "__render__")


def is_stream_renderable(content: Any) -> bool:
    """dom_tag trees or any object exposing ``__async_render__``."""
    return isinstance(content, dom_tag.dom_tag) or hasattr(content, "__async_render__")


def prepare_html_body(content: Any) -> Any:
    """Stamp CSP + expand ``__render__`` / str nonces. No framework types.

    Return value is what an HTTP adapter encodes to bytes. Starlette
    ``HTMLResponse.render`` should call this then ``super().render(...)``.
    """
    if content is None:
        return content
    try:
        from ux_dom.plugins.csp import resolve_nonce, stamp_tree

        n = resolve_nonce()
        if n:
            stamp_tree(content, n)
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
    return content


def to_html_bytes(content: Any, *, encoding: str = "utf-8") -> bytes:
    """Tree/Component/str → UTF-8 HTML bytes (framework-agnostic)."""
    body = prepare_html_body(content)
    if body is None:
        return b""
    if isinstance(body, (bytes, bytearray, memoryview)):
        return bytes(body)
    if hasattr(body, "__render__"):
        body = body.__render__()
    if isinstance(body, dom_tag.dom_tag):
        body = str(body)
    return str(body).encode(encoding)


async def _async_bytes_chunks(data: bytes) -> AsyncIterator[bytes]:
    yield data


async def _async_str_chunks(data: str) -> AsyncIterator[str]:
    yield data


def prepare_html_stream(html_content: Any) -> Any:
    """Normalize constructor input to an async iterable body. No Starlette."""
    if html_content is None:
        return _async_str_chunks("")

    if isinstance(html_content, dom_tag.dom_tag) or hasattr(
        html_content, "__async_render__"
    ):
        try:
            from ux_dom.plugins.csp import resolve_nonce, stamp_tree

            n = resolve_nonce()
            if n:
                stamp_tree(html_content, n)
        except Exception:
            pass
        return html_content.__async_render__(pretty=False)

    if isinstance(html_content, (bytes, bytearray, memoryview)):
        return _async_bytes_chunks(bytes(html_content))

    if isinstance(html_content, str):
        return _async_str_chunks(html_content)

    if hasattr(html_content, "__aiter__"):
        return html_content

    raise TypeError(
        "prepare_html_stream expects a dom_tag, object with __async_render__, "
        f"str, bytes, or async iterator; got {type(html_content)!r}"
    )
