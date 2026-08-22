"""FastAPI adapter — materialize DirectoryRoutes into an APIRouter.

The pure discovery model lives in ``ux_dom.routing.core``. This module only
binds callables onto FastAPI/Starlette routes. Page units and path law never
import FastAPI.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from ux_dom.routing.core import DirectoryRoutes, RouterHooks


def _page_get_endpoint(
    page_cls: type,
    *,
    path: str,
    name: str,
    resolve_unit: Optional[Callable[..., Any]] = None,
):
    """Synthetic page GET: resolve_unit → instance, else cls()."""

    def endpoint(*args: Any, **kwargs: Any):
        inst = None
        if resolve_unit is not None:
            try:
                inst = resolve_unit(page_cls, path, name)
            except Exception:
                inst = None
        if inst is None:
            inst = page_cls()
        render = getattr(inst, "render", None) or getattr(inst, "__render__", None)
        if callable(render):
            return render()
        return inst

    endpoint.__name__ = f"{name}_get"
    endpoint.__doc__ = getattr(page_cls, "__doc__", None)
    return endpoint


def materialize(
    core: DirectoryRoutes,
    *,
    router: Any = None,
    route_class: Any = None,
) -> Any:
    """Build / extend a FastAPI APIRouter from pure ``DirectoryRoutes`` records."""
    try:
        from fastapi import APIRouter
    except ImportError as e:
        raise ImportError(
            "FastAPI adapter requires fastapi. pip install fastapi"
        ) from e

    if router is None:
        router = APIRouter()
    if route_class is not None:
        router.route_class = route_class

    if not core.records:
        core.discover()

    hooks = core.hooks or RouterHooks()
    resolve = hooks.resolve_unit

    for rec in core.records:
        path = rec.path
        methods = [rec.method.upper()]
        name = rec.name
        if rec.kind == "explicit" and rec.handler is not None:
            endpoint = rec.handler
        elif rec.page_cls is not None:
            endpoint = _page_get_endpoint(
                rec.page_cls,
                path=path,
                name=name,
                resolve_unit=resolve,
            )
        else:
            continue
        router.add_api_route(
            path,
            endpoint,
            name=name,
            methods=methods,
            description=getattr(endpoint, "__doc__", None),
        )
    return router


def mount(
    core: DirectoryRoutes,
    asgi_app: Any,
    *,
    prefix: str = "",
    route_class: Any = None,
) -> Any:
    """Discover (if needed) and ``include_router`` on a FastAPI/Starlette app."""
    router = materialize(core, route_class=route_class)
    if not hasattr(asgi_app, "include_router"):
        raise TypeError("asgi_app must support include_router (FastAPI/Starlette)")
    asgi_app.include_router(router, prefix=prefix)
    return router


__all__ = ["materialize", "mount"]
