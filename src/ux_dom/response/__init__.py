# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Starlette/FastAPI response adapters for ux-dom trees.

Public API
----------
* ``HTMLResponse`` / ``html_response`` — render a DOM tree as HTML
* ``StreamingResponse`` / ``streaming_response`` — stream a DOM tree

::

    from ux_dom.response import HTMLResponse, StreamingResponse
    from ux_dom.dom import div

    return HTMLResponse(div("hello"))
"""

from ux_dom.response.starlette import (
    HTMLResponse,
    StreamingResponse,
    html_response,
    streaming_response,
)

__all__ = [
    "HTMLResponse",
    "html_response",
    "StreamingResponse",
    "streaming_response",
]
