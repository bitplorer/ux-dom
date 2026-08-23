# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""HMR contribution wiring (dev) — pairs with ``reloader``.

**Not a Document.use product API.** File watch + WebSocket is **dev delivery**.
Product applications should take HMR from **ux-compose** (owns package_dir +
ASGI bind). This module remains for pure-dom / legacy scaffolds only.

See ``docs/internals/SYSTEM.md`` and ux-compose ``docs/FLOW.md``.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence


class HotReload:
    """HmrPlugin around ``HotReloadWebSocketRoute`` (non-product / advanced)."""

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
        self.watch_paths = list(watch_paths or ["."])
        self.url_path = url_path
        self.url_name = url_name
        self.reconnect_interval = reconnect_interval
        self._route = None

    def _ensure(self):
        if self._route is not None:
            return self._route
        from fastapi import WebSocket

        from ux_dom.reloader import HotReloadWebSocketRoute, WatchPath

        paths = []
        for item in self.watch_paths:
            if isinstance(item, WatchPath):
                paths.append(item)
            elif isinstance(item, tuple) and len(item) == 2:
                paths.append(WatchPath(path=str(item[0]), on_reload=item[1] or ()))
            else:
                paths.append(WatchPath(path=str(item), on_reload=()))
        self._route = HotReloadWebSocketRoute(
            websocket_type=WebSocket,
            watch_paths=paths,
            url_path=self.url_path,
            url_name=self.url_name,
            reconnect_interval=self.reconnect_interval,
        )
        return self._route

    def client_script(self) -> str:
        return self._ensure().script()

    def asgi_route(self) -> Optional[tuple[str, Any]]:
        route = self._ensure()
        return (route.url_path, route)

    async def startup(self) -> None:
        await self._ensure().startup()

    async def shutdown(self) -> None:
        await self._ensure().shutdown()


__all__ = ["HotReload"]
