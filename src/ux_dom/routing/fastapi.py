# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""FastAPI **adapter** for DirectoryRouter.

Core path-law / page-unit discovery lives in ``ux_dom.routing.core``
(no FastAPI imports). This module materializes an ``APIRouter`` from that
model. Swap hosts later via additional adapters without changing page units.

Public re-export. Full FastAPI implementation: ``_directory_router_impl``.
Pure core: ``ux_dom.routing.core``.
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
]
