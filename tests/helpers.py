"""Shared test helpers (optional). Prefer local fixtures when one-off.

Keep this module small: helpers here must be used by 2+ packages.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from contextlib import contextmanager

from ux_dom.cli.scaffold import ScaffoldOptions, create_app


@contextmanager
def scaffolded_app(
    name: str = "app",
    *,
    template: str = "minimal",
    with_tailwind: bool = False,
    with_channel: bool = False,
) -> Iterator[Path]:
    """Yield a temporary create-app project root (force=True)."""
    with TemporaryDirectory() as td:
        root = create_app(
            ScaffoldOptions(
                name,
                dest=Path(td) / name,
                force=True,
                template=template,
                with_tailwind=with_tailwind,
                with_channel=with_channel,
            )
        )
        yield root
