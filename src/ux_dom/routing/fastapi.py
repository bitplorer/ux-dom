# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""FastAPI **adapter** for DirectoryRouter.

Core path-law / page-unit discovery lives in ``ux_dom.routing.core``
(no FastAPI imports). This module materializes an ``APIRouter`` from that
model. Swap hosts later via additional adapters without changing page units.

* Full-featured adapter: ``DirectoryRouter`` (StreamingRoute, [id] paths, …)
* Thin materialize path: ``ux_dom.routing.adapters.fastapi.mount(core, app)``
"""
from __future__ import annotations

from ux_dom.routing.core import (  # noqa: F401
    AcceptSymbol,
    DirectoryRouterError,
    DirectoryRoutes,
    OnRoute,
    ResolveUnit,
    RouteRecord,
    RouterHooks,
)
from ux_dom.routing._directory_router_impl import (  # noqa: F401
    DirectoryRouter,
    HTMLRoute,
    StreamingRoute,
)

try:
    from ux_dom.routing.adapters.fastapi import materialize, mount  # noqa: F401
except ImportError:  # pragma: no cover
    materialize = mount = None  # type: ignore

__all__ = [
    "HTMLRoute",
    "StreamingRoute",
    "DirectoryRouter",
    "DirectoryRouterError",
    "DirectoryRoutes",
    "RouteRecord",
    "RouterHooks",
    "ResolveUnit",
    "AcceptSymbol",
    "OnRoute",
    "materialize",
    "mount",
]
