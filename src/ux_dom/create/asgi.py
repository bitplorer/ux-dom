"""Removed from the product path.

Product composition: ``uxcompose create-app`` / ``ux_compose.build``.
This class remains importable so leftover callers fail closed with a
teaching error instead of standing up a second FastAPI factory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_TEACH = (
    "CreateAsgi is not the product path. "
    "Use: uxcompose create-app / ux_compose.build(host=) "
    "(see ux-compose docs/FLOW.md). "
    "Leftover: FastAPI() + document.mount(app) + leftover DirectoryRouter."
)


class ProductAsgiMoved(RuntimeError):
    """Raised when a caller builds product ASGI from ux-dom CreateAsgi."""

    def __init__(self, message: str = _TEACH):
        super().__init__(message)


@dataclass
class CreateAsgi:
    """Historical helper. ``build()`` fails closed and teaches uxcompose."""

    title: str = "ux-dom"
    document: Any = None
    debug: bool = False
    app: Any = None
    _route_packages: list[tuple[Path, str, str]] = field(default_factory=list)
    _static_mounts: list[tuple[str, Path]] = field(default_factory=list)
    _styles: list[Any] = field(default_factory=list)
    _hmr: list[Any] = field(default_factory=list)
    _extra: list[Any] = field(default_factory=list)

    def directory_routes(
        self,
        package_dir: Path | str,
        base_directory: str = "routes",
        prefix: str = "",
    ) -> "CreateAsgi":
        raise ProductAsgiMoved()

    def static(self, url_path: str, directory: Path | str) -> "CreateAsgi":
        raise ProductAsgiMoved()

    def use(self, *items: Any) -> "CreateAsgi":
        raise ProductAsgiMoved()

    def build(self) -> Any:
        raise ProductAsgiMoved()
