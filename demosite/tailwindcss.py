# Copyright (c) 2022–2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Demo-local CSS compile. Not a library API.

Product compile is ``uxcompose build`` (``ux_compose.tailwind``).
This script shells ``tailwindcss`` on PATH for the in-tree demosite only.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from demosite import settings

_INPUT = Path(settings.webassets.dir) / "tailwind.css"
_OUTPUT = Path(settings.webassets.static.css) / "styles.css"


def _argv(*, watch: bool) -> list[str] | None:
    tw = shutil.which("tailwindcss")
    if not tw:
        return None
    argv = [tw, "-i", str(_INPUT), "-o", str(_OUTPUT)]
    argv.append("--watch" if watch else "--minify")
    return argv


def run() -> int:
    argv = _argv(watch=False)
    if argv is None:
        print(
            "tailwindcss not on PATH — product compile is: uxcompose build",
            file=sys.stderr,
        )
        return 2
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.call(argv, cwd=str(settings.webassets.dir))


async def async_run():
    """Used by demosite DEBUG reloader. Missing CLI is a no-op."""
    argv = _argv(watch=bool(settings.DEBUG))
    if argv is None:
        return None
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        *argv, cwd=str(settings.webassets.dir)
    )
    if settings.DEBUG:
        return proc
    return await proc.wait()


if __name__ == "__main__":
    raise SystemExit(run())
