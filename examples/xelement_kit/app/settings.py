from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DEBUG", "1") not in ("0", "false", "False")
APP_TITLE = "UxDom XElement Kit"
ASSETS_DIR = BASE_DIR / "assets"
