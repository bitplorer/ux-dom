"""DirectoryRouting contribution for App composition / scaffolds."""
from __future__ import annotations

from typing import Any, Callable, Optional, Type


class DirectoryRouting:
    """Leftover plugin wrapper around ``DirectoryRouter``.

    Product page routing is ``ux_compose.routing.DirectoryRoutes``.
    This wrapper stays for leftover standalone FastAPI trees that cannot
    import compose.

    Path law (DirectoryRouter leftover):
    * URL = filesystem only (folder + file stem). No ClassName segment.
    * Renderable unit always registers GET.
    * ``routes=`` only for extra verbs / subpaths.

    Extension: ``on_unit(klass, prefix, file)``.
    """

    plugin_kind = "routing"
    name = "directory"

    def __init__(
        self,
        *,
        base_directory: str = "app",
        route_file_name: str = "route",
        prefix: str = "",
        route_class: Optional[Type[Any]] = None,
        package_dir: Any = None,
        on_unit: Optional[Callable[..., Any]] = None,
    ):
        self.base_directory = base_directory
        self.route_file_name = route_file_name
        self.prefix = prefix
        self.route_class = route_class
        self.package_dir = package_dir
        self.on_unit = on_unit
        self._router = None

    def include(self, app: Any, **kwargs: Any) -> Any:
        from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute

        route_class: Any = self.route_class or StreamingRoute
        self._router = DirectoryRouter(  # type: ignore[assignment]
            base_directory=self.base_directory,
            route_file_name=self.route_file_name,
            prefix=self.prefix,
            route_class=route_class,
            package_dir=self.package_dir,
            on_unit=self.on_unit,
        )
        if hasattr(app, "include_router"):
            app.include_router(self._router)
        return self._router

    @property
    def route_table(self):
        r = self._router
        if r is None:
            return []
        return getattr(r, "route_table", [])
