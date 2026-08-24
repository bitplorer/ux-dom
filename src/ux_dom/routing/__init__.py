# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Routing — leftover ``DirectoryRouter`` batteries only.

Product page routing is ``ux_compose.routing.DirectoryRoutes``.

Leftover standalone FastAPI trees (demosite, examples that must not
import compose)::

    from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute

``DirectoryRoutes`` / thin adapters / facade on this package fail closed.
"""
