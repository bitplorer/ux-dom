# Copyright (c) 2023–2026 UX-DOM
"""uxdom CLI entry.

Brand lines
-----------
| Layer | Name |
|-------|------|
| **PyPI / pip** | ``ux-dom`` |
| **Import** | ``ux_dom`` |
| **CLI** | ``uxdom`` (console script → ``ux_dom.cli:app``) |

Public surface
--------------
* ``app`` — Typer application (``uxdom`` console script)
* ``ux_dom`` — alias of ``app`` (programmatic use)
"""

from .cli import app as app
from .cli import ux_dom as ux_dom

__all__ = ["app", "ux_dom"]
