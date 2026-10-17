"""Toolchain gate for the Playwright harnesses in tests/browser/.

Setup (once): ``npm ci --prefix tests/browser`` then
``npx --prefix tests/browser playwright install --with-deps chromium``.

Without the toolchain these tests skip locally with that hint. CI sets
``UX_DOM_REQUIRE_BROWSER=1`` so a missing toolchain fails instead of skipping:
a browser gate that can silently skip is not a gate.
"""

from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROWSER_DIR = ROOT / "tests" / "browser"
NODE = os.environ.get("NODE_BIN", "node")
HINT = (
    "npm ci --prefix tests/browser && "
    "npx --prefix tests/browser playwright install --with-deps chromium"
)


def _missing() -> str | None:
    if shutil.which(NODE) is None:
        return f"node not found ({NODE!r})"
    if not (BROWSER_DIR / "node_modules" / "playwright" / "package.json").is_file():
        return "playwright not installed in tests/browser"
    return None


def require_browser() -> None:
    reason = _missing()
    if reason is None:
        return
    if os.environ.get("UX_DOM_REQUIRE_BROWSER") == "1":
        raise AssertionError(f"UX_DOM_REQUIRE_BROWSER=1 but {reason}; run: {HINT}")
    raise unittest.SkipTest(f"{reason}; run: {HINT}")
