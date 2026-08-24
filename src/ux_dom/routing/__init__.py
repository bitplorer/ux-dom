# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Routing — **DirectoryRoutes** + thin adapters (live path).

Preferred::

    from ux_dom.routing.core import DirectoryRoutes, RouterHooks
    from ux_dom.routing.adapters.fastapi import mount
    from ux_dom.routing.adapters.asgi import DirectoryASGI

``DirectoryRouter`` (FastAPI APIRouter batteries) remains for leftover
standalone FastAPI trees. Product apps use ux-compose ``App.mount``.

See docs/guides/ROUTING.md for path law and page-unit convention.
"""
