"""Removed from the product path.

Product page routing is ``ux_compose.routing.DirectoryRoutes``.
This module remains importable so leftover callers fail closed with a
teaching error instead of discovering a second scanner.

Leftover standalone FastAPI trees that cannot import compose still use
``ux_dom.routing.fastapi.DirectoryRouter``.
"""
from __future__ import annotations

_TEACH = (
    "DirectoryRoutes is not a ux-dom render API. "
    "Product page routing lives on ux-compose:\n"
    "  from ux_compose.routing import DirectoryRoutes, RouterHooks\n"
    "  # or: app.mount(...) / ux_compose.build() / uxcompose serve\n"
    "Leftover standalone FastAPI trees: ux_dom.routing.fastapi.DirectoryRouter."
)


class ProductRoutingMoved(RuntimeError):
    """Raised when a caller constructs product DirectoryRoutes from ux-dom."""

    def __init__(self, message: str = _TEACH):
        super().__init__(message)


class DirectoryRouterError(RuntimeError):
    """Historical name — constructing this is not the product path."""

    def __init__(self, *args, **kwargs):
        raise ProductRoutingMoved()


class RouterHooks:
    def __init__(self, *args, **kwargs):
        raise ProductRoutingMoved()


class DirectoryRoutes:
    """Fail-closed. Product discovery is ``ux_compose.routing.DirectoryRoutes``."""

    def __init__(self, *args, **kwargs):
        raise ProductRoutingMoved()

    def discover(self):
        raise ProductRoutingMoved()

    def route_table(self):
        raise ProductRoutingMoved()


class RouteRecord:
    def __init__(self, *args, **kwargs):
        raise ProductRoutingMoved()


def pick_page_type(*args, **kwargs):
    raise ProductRoutingMoved()


def module_exports(*args, **kwargs):
    raise ProductRoutingMoved()


ResolveUnit = AcceptSymbol = OnRoute = None

__all__ = [
    "ProductRoutingMoved",
    "DirectoryRouterError",
    "DirectoryRoutes",
    "RouterHooks",
    "RouteRecord",
    "pick_page_type",
    "module_exports",
]
