#!/usr/bin/env python3
"""Maintainer alias for ``uxdom profile`` that works from a plain checkout.

    python scripts/profile_p95.py [--out DIR] [--rounds N] [--json] ...

Options are those of ``uxdom profile``. Without ``--out`` the report goes to
``reports/p95/`` in the repository (not the current directory).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # ux_dom without an install

from ux_dom.cli.cli import app  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--out" not in args:
        args += ["--out", str(ROOT / "reports" / "p95")]
    app(["profile", *args], prog_name="profile_p95.py")


if __name__ == "__main__":
    main()
