"""App settings — paths and feature flags."""
from __future__ import annotations

import os
from pathlib import Path

from ux_dom import WebAssets

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DEBUG", "1") not in ("0", "false", "False")

ASSETS_DIR = BASE_DIR / "assets"
CSS_DIR = ASSETS_DIR / "css"
INPUT_CSS = "input.css"
OUTPUT_CSS = "output.css"

# WebAssets: base_dir is the static root served at /css, /js, …
webassets = WebAssets(base_dir=ASSETS_DIR, dry_run=False)

APP_TITLE = "UxDom Showcase"
WITH_TAILWIND = True
WITH_CHANNEL = False
WITH_HMR = True
