"""FastAPI host plugin — leftover batteries, **not** the product path.

Product host strategy lives on **ux-compose** (`build(host=)`).
This module remains for tests and pure-dom experiments.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional, Sequence


class FastAPIHost:
    """Mount a FastAPI app with StreamingRoute, static mounts, HMR lifespan.

    Usage::

        from ux_dom.plugins import App
        from ux_dom.plugins.host import FastAPIHost

        app = App().use(FastAPIHost(title="My App")).build()

    When ``debug`` is false, OpenAPI UI routes (``/docs``, ``/redoc``,
    ``/openapi.json``) are disabled so production builds do not expose the
    schema by default.
    """

    plugin_kind = "host"
    name = "fastapi"

    def __init__(
        self,
        title: str = "ux-dom",
        debug: Optional[bool] = None,
        default_response_class: Any = None,
        route_class: Any = None,
        static_mounts: Optional[Sequence[tuple[str, Any]]] = None,
        lifespan_hooks: Optional[Sequence[Any]] = None,
    ):
        self.title = title
        self.debug = debug
        self.default_response_class = default_response_class
        self.route_class = route_class
        self.static_mounts = list(static_mounts) if static_mounts else []
        self.lifespan_hooks = list(lifespan_hooks) if lifespan_hooks else []
        self.app = None

    def mount(self, app: Any = None, settings: Any = None, **kwargs: Any) -> Any:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        from fastapi.staticfiles import StaticFiles
        from ux_dom.routing.fastapi import StreamingRoute

        hub = kwargs.get("hub")
        if self.debug is not None:
            debug = self.debug
        else:
            debug = bool(kwargs.get("debug", getattr(settings, "DEBUG", False)))

        hmr_plugins = list(hub.hmr.values()) if hub is not None else []
        style_plugins = list(hub.styles.values()) if hub is not None else []
        host = self

        @asynccontextmanager
        async def lifespan(application: FastAPI):
            for style in style_plugins:
                try:
                    await style.build(watch=debug)
                except Exception:
                    pass
            for hmr in hmr_plugins:
                startup = getattr(hmr, "startup", None)
                if startup is not None:
                    await startup()
            for hook in host.lifespan_hooks:
                start = getattr(hook, "startup", None) or (
                    hook[0] if isinstance(hook, tuple) else None
                )
                if start is not None:
                    await start()
            yield
            for hmr in hmr_plugins:
                shutdown = getattr(hmr, "shutdown", None)
                if shutdown is not None:
                    await shutdown()
            for style in style_plugins:
                stop = getattr(style, "stop", None)
                if stop is not None:
                    await stop()
            for hook in host.lifespan_hooks:
                stop = getattr(hook, "shutdown", None) or (
                    hook[1] if isinstance(hook, tuple) else None
                )
                if stop is not None:
                    await stop()

        if app is None:
            app = FastAPI(
                title=self.title,
                debug=debug,
                default_response_class=self.default_response_class or HTMLResponse,
                lifespan=lifespan,
                docs_url="/docs" if debug else None,
                redoc_url="/redoc" if debug else None,
                openapi_url="/openapi.json" if debug else None,
            )

        route_class = self.route_class or StreamingRoute
        if hasattr(app, "router") and route_class is not None:
            app.router.route_class = route_class

        if hub is not None:
            for hmr in hub.hmr.values():
                route = hmr.asgi_route()
                if route is not None:
                    path, endpoint = route
                    name = getattr(hmr, "url_name", hmr.name)
                    if hasattr(app, "add_websocket_route"):
                        app.add_websocket_route(path, endpoint, name=name)

        for mount_path, directory in self.static_mounts:
            directory = Path(directory)
            app.mount(
                mount_path,
                StaticFiles(directory=str(directory), check_dir=False),
                name=mount_path.strip("/").replace("/", "_") or "static",
            )

        self.app = app
        return app


__all__ = ["FastAPIHost"]
