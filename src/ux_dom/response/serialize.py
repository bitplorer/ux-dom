"""Pure HTML prepare/serialize — no FastAPI/Starlette imports.

Domain boundary: tree / Component / str → body content (or async stream).
HTTP container classes live in ``response.starlette`` (adapter) and call these.

``extract_by_id`` is the owned post-serialize strip (compose#80 C2).
``Fragment`` builds trees; it is not extract. Compose
``_fragment_for_target`` KEEP until callers USE this API. Channel
``_guess_target_from_html`` is selector leftover, not extract — do not
absorb. No ``fragment.py``. Soft 1/4 prefer-owner: no channel package import.
"""
from __future__ import annotations

import re
from typing import Any, AsyncIterator

from ux_dom.dom.src import dom_tag

__all__ = [
    "is_html_renderable",
    "is_stream_renderable",
    "prepare_html_body",
    "to_html_bytes",
    "prepare_html_stream",
    "extract_by_id",
]

# Void tags + quote-aware scan — same contract as compose
# ``_fragment_for_target``. Exact outer-HTML slice; do not parse-then-re-render.
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_TAG_NAME = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9:_-]*)", re.I)
_ID_ATTR_NAME = re.compile(r"(?<![A-Za-z0-9:_-])id\s*=\s*", re.I)


def _skip_quoted(html: str, start: int) -> int:
    """Advance from ``start`` (a ``>`` search) past the next unquoted ``>``."""
    i = start
    in_quote: str | None = None
    while i < len(html):
        c = html[i]
        if in_quote:
            if c == in_quote:
                in_quote = None
        elif c in "\"'":
            in_quote = c
        elif c == ">":
            return i
        i += 1
    return -1


def _element_end(html: str, start: int) -> int | None:
    """Exclusive index of the element that opens at ``html[start]`` (``<``)."""
    m = _TAG_NAME.match(html, start)
    if not m or m.group(1):
        return None
    name = m.group(2).lower()
    gt = _skip_quoted(html, m.end())
    if gt < 0:
        return None
    self_close = gt > start and html[gt - 1] == "/"
    after_open = gt + 1
    if self_close or name in _VOID_TAGS:
        return after_open
    depth = 1
    i = after_open
    while i < len(html):
        if html.startswith("<!--", i):
            end = html.find("-->", i + 4)
            if end < 0:
                return None
            i = end + 3
            continue
        if html[i] != "<":
            i += 1
            continue
        tm = _TAG_NAME.match(html, i)
        if not tm:
            i += 1
            continue
        gt = _skip_quoted(html, tm.end())
        if gt < 0:
            return None
        tname = tm.group(2).lower()
        closing = bool(tm.group(1))
        self_close = gt > i and html[gt - 1] == "/"
        nxt = gt + 1
        if tname == name:
            if closing:
                depth -= 1
                if depth == 0:
                    return nxt
            elif not self_close and name not in _VOID_TAGS:
                depth += 1
        i = nxt
    return None


def _open_tag_id(open_tag: str) -> str | None:
    """Return the ``id`` attribute of one start tag, ignoring quoted values."""
    i = 0
    in_quote: str | None = None
    while i < len(open_tag):
        c = open_tag[i]
        if in_quote:
            if c == in_quote:
                in_quote = None
            i += 1
            continue
        if c in "\"'":
            in_quote = c
            i += 1
            continue
        m = _ID_ATTR_NAME.match(open_tag, i)
        if not m:
            i += 1
            continue
        j = m.end()
        if j < len(open_tag) and open_tag[j] in "\"'":
            q = open_tag[j]
            k = open_tag.find(q, j + 1)
            return open_tag[j + 1 : k] if k >= 0 else open_tag[j + 1 :].rstrip(">/ \t\n\r")
        k = j
        while k < len(open_tag) and open_tag[k] not in " \t\n\r>/":
            k += 1
        return open_tag[j:k]
    return None


def extract_by_id(html: str, target_id: str) -> str:
    """Return the outer-HTML slice for ``#target_id``.

    Morph payload law: subtree for the id, not a document shell.
    ``target_id`` may be ``hello`` or ``#hello``. Missing / empty
    id leaves ``html`` unchanged. Already-fragment HTML is unchanged.

    Callers USE this instead of a homemade walker (compose C2).
    ``Fragment`` is a tree builder — not this function.
    """
    blob = html or ""
    tid = str(target_id or "").lstrip("#")
    if not blob or not tid:
        return html
    i = 0
    while i < len(blob):
        if blob.startswith("<!--", i):
            end = blob.find("-->", i + 4)
            i = len(blob) if end < 0 else end + 3
            continue
        if blob[i] != "<" or blob.startswith(("</", "<!", "<?"), i):
            i += 1
            continue
        gt = _skip_quoted(blob, i + 1)
        if gt < 0:
            break
        if _open_tag_id(blob[i : gt + 1]) == tid:
            end = _element_end(blob, i)
            if end is not None:
                return blob[i:end]
        i = gt + 1
    return html


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
