"""Demo-local CSS compile. Not a library API.

    python -m app.tailwindcss

Product compile is ``uxcompose build``. This leftover showcase tree shells
``tailwindcss`` on PATH when present.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from app import settings


def main() -> int:
    tw = shutil.which("tailwindcss")
    if not tw:
        print(
            "tailwindcss not on PATH — product compile is: uxcompose build",
            file=sys.stderr,
        )
        return 2
    inp = Path(settings.webassets.dir) / settings.INPUT_CSS
    if not inp.is_file():
        alt = Path(settings.webassets.dir) / "css" / settings.INPUT_CSS
        inp = alt if alt.is_file() else inp
    out = Path(settings.webassets.static.css) / settings.OUTPUT_CSS
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [tw, "-i", str(inp), "-o", str(out)]
    if not settings.DEBUG:
        cmd.append("--minify")
    return subprocess.call(cmd, cwd=str(settings.webassets.dir))


if __name__ == "__main__":
    raise SystemExit(main())
