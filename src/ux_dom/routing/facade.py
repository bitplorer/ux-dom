"""Composition-facing mount — one door for host selection.

::

    from ux_dom.routing.facade import mount
    from ux_dom.routing.core import DirectoryRoutes, RouterHooks

    core = DirectoryRoutes(PACKAGE, hooks=hooks)
    app = mount(core, host="asgi")           # pure DirectoryASGI
    mount(core, fastapi_app, host="fastapi") # include_router
    mount(core, app, host="auto")            # detect
"""
from __future__ import annotations

from typing import Any

from ux_dom.routing.core import DirectoryRoutes

__all__ = ["mount", "detect_host"]


def detect_host(app: Any) -> str:
    if app is None:
        return "asgi"
    mod = type(app).__module__ or ""
    name = type(app).__name__
    if "fastapi" in mod or name == "FastAPI":
        return "fastapi"
    if "starlette" in mod or name in ("Starlette", "Application"):
        return "starlette"
    if "litestar" in mod:
        return "litestar"
    if hasattr(app, "include_router"):
        return "fastapi"
    return "asgi"


def mount(
    core: DirectoryRoutes,
    app: Any = None,
    *,
    host: str = "auto",
    prefix: str = "",
) -> Any:
    """Discover (if needed) and bind routes to a host.

    * ``host="asgi"`` or ``app is None`` → DirectoryASGI
    * ``host="fastapi"`` / ``starlette`` → adapters.fastapi.mount
    * ``host="auto"`` → detect_host
    """
    if not core.records:
        core.discover()

    h = host.lower() if host else "auto"
    if h == "auto":
        h = detect_host(app)

    if h == "asgi" or app is None:
        from ux_dom.routing.adapters.asgi import DirectoryASGI

        asgi_app = DirectoryASGI(core)
        if app is not None and hasattr(app, "mount") and prefix:
            app.mount(prefix or "/", asgi_app)
            return asgi_app
        return asgi_app

    if h in ("fastapi", "starlette"):
        from ux_dom.routing.adapters.fastapi import mount as fastapi_mount

        if app is None:
            raise TypeError("host=%r requires an ASGI app with include_router" % h)
        return fastapi_mount(core, app, prefix=prefix)

    raise ValueError("unknown host %r — use auto|asgi|fastapi|starlette" % host)
