"""Removed from the product path.

Thin FastAPI adapter lives on ``ux_compose.routing.adapters.fastapi``.
"""
from __future__ import annotations

from ux_dom.routing.core import ProductRoutingMoved

_TEACH = (
    "ux_dom.routing.adapters.fastapi is not the product path. "
    "Use: from ux_compose.routing.adapters.fastapi import mount"
)


def materialize(*args, **kwargs):
    raise ProductRoutingMoved(_TEACH)


def mount(*args, **kwargs):
    raise ProductRoutingMoved(_TEACH)


__all__ = ["materialize", "mount"]
