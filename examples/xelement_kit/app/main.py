"""
XElement kit — HTMX / Alpine / Web Components.

    PYTHONPATH=examples/xelement_kit:./ uvicorn app.main:app --app-dir examples/xelement_kit --port 8080

XElement JS: single copy from installed ux_dom → GET /ux-dom/static/x_element.js
"""
from __future__ import annotations

from pathlib import Path

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from ux_dom.plugins import App, XElementRuntime
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.plugins.runtime import XELEMENT_JS_URL

from app import settings

PACKAGE = Path(__file__).resolve().parent

app = (
    App(debug=settings.DEBUG)
    .use(XElementRuntime())  # package mount — no dual assets/js copy
    .use(FastAPIHost(title=settings.APP_TITLE, debug=settings.DEBUG))
    .use(DirectoryRouting(package_dir=PACKAGE, base_directory="routes", prefix=""))
    .use(HtmxControl(middleware=True, version="2.0.4"))
    .build()
)

if settings.ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(settings.ASSETS_DIR)), name="assets")


@app.get("/")
def root():
    return RedirectResponse("/index/Index")


@app.get("/health", response_class=JSONResponse)
def health():
    return {
        "ok": True,
        "app": "xelement_kit",
        "runtime": "x_element.js",
        "python": "XElement",
        "runtime_url": XELEMENT_JS_URL,
    }
