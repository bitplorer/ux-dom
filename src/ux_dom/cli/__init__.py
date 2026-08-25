# Copyright (c) 2023–2026 UX-DOM
"""uxdom CLI entry — pure Document/render tooling.

Product lifecycle: ``uxcompose create-app | build | serve | deploy``.
Tailwind compiler: ``ux_compose.tailwind`` (``uxcompose build``).
This package does not find, download, or invoke the Tailwind CLI.
"""

from .cli import app as app
from .cli import ux_dom as ux_dom

__all__ = ["app", "ux_dom"]
