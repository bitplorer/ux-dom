"""Host adapters for DirectoryRoutes core.

* ``fastapi`` — materialize/mount onto APIRouter-compatible apps
* ``asgi`` — pure :class:`DirectoryASGI` (no framework)
"""
from __future__ import annotations

from ux_dom.routing.adapters.asgi import DirectoryASGI, match_record
from ux_dom.routing.adapters.fastapi import materialize, mount

__all__ = ["materialize", "mount", "DirectoryASGI", "match_record"]
