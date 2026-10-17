# Copyright (c) 2023–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""FastAPI route classes that serialize ux-dom trees.

Set one as ``route_class`` and every endpoint on that router may return a
Component / tag (or an async generator of them)::

    router = APIRouter(route_class=StreamingRoute)

    @router.get("/")
    def index():
        return page(Index())

``HTMLRoute`` wraps endpoints with ``html_response`` (one body);
``StreamingRoute`` wraps them with ``streaming_response`` (chunked).
Requires the optional ``fastapi`` extra.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi.routing import APIRoute

from ux_dom.response.starlette import html_response, streaming_response

__all__ = ["HTMLRoute", "StreamingRoute"]


class HTMLRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        super().__init__(path, html_response(endpoint), **kwargs)


class StreamingRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        super().__init__(path, streaming_response(endpoint), **kwargs)
