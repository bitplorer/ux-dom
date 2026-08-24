# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Removed from the product path.

Dev HMR is ``uxcompose serve --hmr`` (``ux_compose.hmr``).
Leftover demosite that cannot import compose still uses
``ux_dom.reloader.HotReloadWebSocketRoute`` directly.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence


_TEACH = (
    "HotReload is not a Document.use / ux-dom product API. "
    "Dev HMR is uxcompose serve --hmr (ux_compose.hmr). "
    "Leftover demosite: ux_dom.reloader.HotReloadWebSocketRoute."
)


class ProductHmrMoved(RuntimeError):
    """Raised when a caller constructs product HMR from ux-dom plugins."""

    def __init__(self, message: str = _TEACH):
        super().__init__(message)


class HotReload:
    """Fail-closed. Product HMR is ``ux_compose.hmr``."""

    plugin_kind = "hmr"
    name = "hotreload"

    def __init__(
        self,
        *,
        watch_paths: Optional[Sequence[Any]] = None,
        url_path: str = "/hot-reload",
        url_name: str = "hot-reload",
        reconnect_interval: float = 0.5,
    ):
        raise ProductHmrMoved()

    def client_script(self) -> str:
        raise ProductHmrMoved()

    def asgi_route(self) -> Optional[tuple[str, Any]]:
        raise ProductHmrMoved()

    async def startup(self) -> None:
        raise ProductHmrMoved()

    async def shutdown(self) -> None:
        raise ProductHmrMoved()


__all__ = ["HotReload", "ProductHmrMoved"]
