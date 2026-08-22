"""Host adapters for DirectoryRoutes core.

FastAPI is the current production adapter. Starlette / Litestar can land
later without changing page units or path law.
"""
from __future__ import annotations

from ux_dom.routing.adapters.fastapi import materialize, mount

__all__ = ["materialize", "mount"]
