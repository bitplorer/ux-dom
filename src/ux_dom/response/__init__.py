# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Response boundary (optional adapters around domain serialize).

**Serialize SSoT is the tree dunders** — not this package::

    html = tree.__render__()
    async for token in tree.__async_render__(pretty=False):
        ...

Pure helpers (framework-free) that *call* those dunders may live here for
CSP stamp + bytes convenience. They are not a second body owner.

Starlette/FastAPI response classes are **optional adapters**. Product HTTP
delivery and host strategy belong in **ux-compose**. Pure-dom scripts may still
import adapters when needed.

See ``docs/internals/SYSTEM.md``.
"""

from ux_dom.response.serialize import (
    is_html_renderable,
    is_stream_renderable,
    prepare_html_body,
    prepare_html_stream,
    to_html_bytes,
)

try:
    from ux_dom.response.starlette import (
        HTMLResponse,
        StreamingResponse,
        html_response,
        streaming_response,
    )
except ImportError:  # pragma: no cover
    HTMLResponse = StreamingResponse = html_response = streaming_response = None  # type: ignore

__all__ = [
    "prepare_html_body",
    "to_html_bytes",
    "prepare_html_stream",
    "is_html_renderable",
    "is_stream_renderable",
    "HTMLResponse",
    "html_response",
    "StreamingResponse",
    "streaming_response",
]
