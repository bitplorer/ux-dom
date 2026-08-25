"""App settings — paths and feature flags."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DEBUG", "1") not in ("0", "false", "False")

ASSETS_DIR = BASE_DIR / "assets"
CSS_DIR = ASSETS_DIR / "css"
INPUT_CSS = "input.css"
OUTPUT_CSS = "output.css"

# Demo-local folders — product layout is ux_compose.WebAssets.
_css = ASSETS_DIR / "static" / "file" / "css"
_js = ASSETS_DIR / "static" / "file" / "js"
_css.mkdir(parents=True, exist_ok=True)
_js.mkdir(parents=True, exist_ok=True)
webassets = SimpleNamespace(dir=ASSETS_DIR, static=SimpleNamespace(css=_css, js=_js))

APP_TITLE = "UxDom Showcase"
WITH_TAILWIND = True
WITH_CHANNEL = False
WITH_HMR = True
