"""Fail-closed adapters — product bind is ``ux_compose.routing.adapters``."""
from __future__ import annotations

from ux_dom.routing.adapters.asgi import DirectoryASGI, match_record
from ux_dom.routing.adapters.fastapi import materialize, mount

__all__ = ["materialize", "mount", "DirectoryASGI", "match_record"]
