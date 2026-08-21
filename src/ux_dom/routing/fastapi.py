# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""FastAPI DirectoryRouter and streaming HTML route classes.

Public re-export. Full implementation: ``ux_dom.routing._directory_router_impl``.
"""
from __future__ import annotations

from ux_dom.routing._directory_router_impl import (  # noqa: F401
    DirectoryRouter,
    DirectoryRouterError,
    HTMLRoute,
    RouterHooks,
    StreamingRoute,
)

__all__ = [
    "HTMLRoute",
    "StreamingRoute",
    "DirectoryRouter",
    "DirectoryRouterError",
    "RouterHooks",
]
