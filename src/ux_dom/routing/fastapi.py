# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""Leftover FastAPI DirectoryRouter batteries.

Product page routing is ``ux_compose.routing.DirectoryRoutes``.
This module stays so leftover demosite / examples that cannot import
compose keep a working FastAPI file router.

Do not use this from product ``app.py`` trees.
"""
from __future__ import annotations

from ux_dom.routing._directory_router_impl import (  # noqa: F401
    AcceptSymbol,
    DirectoryRouter,
    DirectoryRouterError,
    HTMLRoute,
    OnRoute,
    ResolveUnit,
    RouterHooks,
    StreamingRoute,
    _clean_url_prefix,
    _set_endpoint_name,
    _to_fastapi_path_params,
)

__all__ = [
    "HTMLRoute",
    "StreamingRoute",
    "DirectoryRouter",
    "DirectoryRouterError",
    "RouterHooks",
    "ResolveUnit",
    "AcceptSymbol",
    "OnRoute",
]
