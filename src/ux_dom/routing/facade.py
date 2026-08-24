"""Removed from the product path.

Host selection for page units lives on ux-compose
(``App.use_host`` / ``build(host=)`` / ``ux_compose.routing``).
"""
from __future__ import annotations

from ux_dom.routing.core import ProductRoutingMoved

_TEACH = (
    "ux_dom.routing.facade.mount is not the product path. "
    "Use ux_compose.build(host=) / App.mount / ux_compose.routing."
)


def detect_host(*args, **kwargs):
    raise ProductRoutingMoved(_TEACH)


def mount(*args, **kwargs):
    raise ProductRoutingMoved(_TEACH)


__all__ = ["mount", "detect_host"]
