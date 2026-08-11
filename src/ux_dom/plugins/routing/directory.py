"""DirectoryRouting contribution for App composition / scaffolds."""
from __future__ import annotations

from typing import Any, Optional, Type


class DirectoryRouting:
    """Plugin wrapper around ``DirectoryRouter`` (Next.js-like file routes).

    Sacred DX: ``app/**/*.py`` with ``routes = [...]`` on Components, or ``route.py``.
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
    ):
        self.base_directory = base_directory
        self.route_file_name = route_file_name
        self.prefix = prefix
        self.route_class = route_class
        self.package_dir = package_dir
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
        )
        if hasattr(app, "include_router"):
            app.include_router(self._router)
        return self._router
