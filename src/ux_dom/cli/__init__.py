# Copyright (c) 2023–2026 UX-DOM
"""uxdom CLI entry — pure Document/render tooling.

Product lifecycle: ``uxcompose create-app | build | serve | deploy``.
Tailwind *compiler* resolution: ``ux_compose.tailwind``.
This package keeps CSS *path* helpers (``ux_dom.cli.tailwind.discover_css_io``).
"""

from .cli import app as app
from .cli import ux_dom as ux_dom

__all__ = ["app", "ux_dom"]
