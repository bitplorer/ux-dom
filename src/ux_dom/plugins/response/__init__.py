# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Response-related plugin contributions. Prefer ux_dom.response for apps."""
from __future__ import annotations

from typing import Any, Callable


class StreamingResponsePlugin:
    plugin_kind = "response"
    name = "streaming"

    def wrap(self, endpoint: Callable[..., Any]) -> Callable[..., Any]:
        from ux_dom.response.starlette import streaming_response

        return streaming_response(endpoint)


class HTMLResponsePlugin:
    plugin_kind = "response"
    name = "html"

    def wrap(self, endpoint: Callable[..., Any]) -> Callable[..., Any]:
        from ux_dom.response.starlette import html_response

        return html_response(endpoint)


__all__ = ["StreamingResponsePlugin", "HTMLResponsePlugin"]
