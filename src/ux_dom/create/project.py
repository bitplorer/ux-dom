# Copyright (c) 2026 ux-dom
"""CreateProject — filesystem scaffold (``uxdom create-app``)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class CreateProject:
    """
    Generate a project tree. Does not start a server.

    ::

        CreateProject("shop").with_channel().with_tailwind().write("./shop")
    """

    def __init__(self, name: str = "app", dest: Optional[Path | str] = None):
        self.name = name
        self.dest = Path(dest) if dest else Path.cwd() / name
        self._tailwind = True
        self._channel = False
        self._hmr = True
        self._template = "minimal"
        self._force = False

    def with_tailwind(self, on: bool = True) -> "CreateProject":
        self._tailwind = on
        return self

    def with_channel(self, on: bool = True) -> "CreateProject":
        self._channel = on
        return self

    def with_hmr(self, on: bool = True) -> "CreateProject":
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
        from ux_dom.cli.scaffold import ScaffoldOptions, create_app as _create_app_fs

        root = Path(dest) if dest is not None else self.dest
        opts = ScaffoldOptions(
            app_name=self.name,
            dest=root,
            force=self._force,
            with_tailwind=self._tailwind,
            with_channel=self._channel,
            with_hmr=self._hmr,
            template=self._template,
        )
        return _create_app_fs(opts)
