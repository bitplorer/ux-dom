# Copyright (c) 2026 ux-dom
"""CreateProject — **not** the product scaffold.

Product applications: ``uxcompose create-app`` (ux-compose).

This class remains importable so older tests and scripts fail closed with a
teaching error instead of writing a second product tree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


_TEACH = (
    "CreateProject.write() is not the product path. "
    "Use: uxcompose create-app <dest>  "
    "(see ux-compose docs/FLOW.md and ux-dom docs/internals/SYSTEM.md)."
)


class ProductScaffoldMoved(RuntimeError):
    """Raised when a caller tries to scaffold a product app from ux-dom."""


class CreateProject:
    """
    Historical builder. ``write()`` fails closed and teaches uxcompose.

    ::

        # will raise ProductScaffoldMoved
        CreateProject("shop").write("./shop")
    """

    def __init__(self, name: str = "app", dest: Optional[Path | str] = None):
        self.name = name
        self.dest = Path(dest) if dest else Path.cwd() / name
        self._tailwind = True
        self._channel = False
        self._hmr = False
        self._template = "minimal"
        self._force = False

    def with_tailwind(self, on: bool = True) -> "CreateProject":
        self._tailwind = on
        return self

    def with_channel(self, on: bool = True) -> "CreateProject":
        self._channel = on
        return self

    def with_hmr(self, on: bool = True) -> "CreateProject":
        # HMR process is ux-compose delivery, not a Document.use / create API.
        self._hmr = on
        return self

    def with_tutorial(self, on: bool = True) -> "CreateProject":
        if on:
            self._template = "tutorial"
        return self

    def template(self, name: str) -> "CreateProject":
        self._template = name
        return self

    def force(self, on: bool = True) -> "CreateProject":
        self._force = on
        return self

    def write(self, dest: Optional[Path | str] = None) -> Path:
        raise ProductScaffoldMoved(_TEACH)
