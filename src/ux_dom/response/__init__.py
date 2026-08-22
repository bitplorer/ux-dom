# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Response boundary.

Domain (no framework)::

    from ux_dom.response import prepare_html_body, to_html_bytes, prepare_html_stream

Starlette/FastAPI adapter (optional extra)::

    from ux_dom.response import HTMLResponse, StreamingResponse
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
