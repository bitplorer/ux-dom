"""Removed from the product path.

Pure ASGI adapter lives on ``ux_compose.routing.adapters.asgi``.
"""
from __future__ import annotations

from ux_dom.routing.core import ProductRoutingMoved

_TEACH = (
    "ux_dom.routing.adapters.asgi is not the product path. "
    "Use: from ux_compose.routing.adapters.asgi import DirectoryASGI"
)


def match_record(*args, **kwargs):
    raise ProductRoutingMoved(_TEACH)


class DirectoryASGI:
    """Fail-closed. Product ASGI bind is ``ux_compose.routing.DirectoryASGI``."""

    def __init__(self, *args, **kwargs):
        raise ProductRoutingMoved(_TEACH)


__all__ = ["DirectoryASGI", "match_record"]
