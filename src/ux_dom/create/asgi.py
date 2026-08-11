# Copyright (c) 2026 ux-dom
"""CreateAsgi — *optional* sugar for FastAPI + ``document.mount``.

Prefer the explicit pattern (what ``uxdom create-app`` emits)::

    app = FastAPI(...)
    document.mount(app)
    DirectoryRouting(...).include(app)

``CreateAsgi`` is only a short helper; it is not required and not a second framework.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CreateAsgi:
    """Optional helper — same as writing FastAPI + ``document.mount`` yourself.

    Prefer explicit ``main.py`` (scaffold default). This class exists for
    compact tests / scripts only.
    """

    title: str = "ux-dom"
    document: Any = None
    debug: bool = False
    app: Any = None
    _route_packages: list[tuple[Path, str, str]] = field(default_factory=list)
    _static_mounts: list[tuple[str, Path]] = field(default_factory=list)
    _styles: list[Any] = field(default_factory=list)
    _hmr: list[Any] = field(default_factory=list)
    _extra: list[Any] = field(default_factory=list)

    def directory_routes(
        self,
        package_dir: Path | str,
        base_directory: str = "routes",
        prefix: str = "",
    ) -> "CreateAsgi":
        self._route_packages.append((Path(package_dir), base_directory, prefix))
        return self

    def static(self, url_path: str, directory: Path | str) -> "CreateAsgi":
        self._static_mounts.append((url_path, Path(directory)))
        return self

    def use(self, *items: Any) -> "CreateAsgi":
        for item in items:
            if item is None:
                continue
            kind = getattr(item, "plugin_kind", None)
            if (
                kind == "style"
                or hasattr(item, "stylesheet_href")
                and hasattr(item, "build")
            ):
                self._styles.append(item)
            elif kind == "hmr" or hasattr(item, "asgi_route"):
                self._hmr.append(item)
            else:
                self._extra.append(item)
        return self

    def build(self) -> Any:
        from fastapi import FastAPI
        from fastapi.staticfiles import StaticFiles

        styles = list(self._styles)
        hmr_list = list(self._hmr)
        debug = self.debug

        @asynccontextmanager
        async def lifespan(application: FastAPI):
            for style in styles:
                try:
                    await style.build(watch=debug)
                except Exception:
                    pass
            for hmr in hmr_list:
                startup = getattr(hmr, "startup", None)
                if startup is not None:
                    await startup()
            yield
            for hmr in hmr_list:
                shutdown = getattr(hmr, "shutdown", None)
                if shutdown is not None:
                    await shutdown()
            for style in styles:
                stop = getattr(style, "stop", None)
                if stop is not None:
                    await stop()

        app = self.app
        if app is None:
            app = FastAPI(title=self.title, debug=debug, lifespan=lifespan)

        # StreamingRoute when available
        try:
            from ux_dom.routing.fastapi import StreamingRoute

            if hasattr(app, "router"):
                app.router.route_class = StreamingRoute
        except ImportError:
            pass

        doc = self.document
        if doc is not None and hasattr(doc, "mount"):
            doc.mount(app)

        for package_dir, base_directory, prefix in self._route_packages:
            from ux_dom.plugins.routing import DirectoryRouting

            DirectoryRouting(
                package_dir=package_dir,
                base_directory=base_directory,
                prefix=prefix,
            ).include(app)

        for url_path, directory in self._static_mounts:
            if directory.exists():
                app.mount(
                    url_path,
                    StaticFiles(directory=str(directory), check_dir=False),
                    name=url_path.strip("/").replace("/", "_") or "static",
                )

        for hmr in hmr_list:
            route = hmr.asgi_route() if hasattr(hmr, "asgi_route") else None
            if route is not None:
                path, endpoint = route
                name = getattr(hmr, "url_name", getattr(hmr, "name", "hmr"))
                if hasattr(app, "add_api_websocket_route"):
                    app.add_api_websocket_route(path, endpoint, name=name)
                elif hasattr(app, "add_websocket_route"):
                    app.add_websocket_route(path, endpoint, name=name)

        for item in self._extra:
            mount = getattr(item, "mount", None)
            if callable(mount):
                try:
                    mount(app)
                except TypeError:
                    mount(app, hub=None)

        return app
