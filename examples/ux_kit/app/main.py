from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.routing import DirectoryRouting

from app import settings

PACKAGE = Path(__file__).resolve().parent

_builder = (
    App(debug=settings.DEBUG)
    .use(DirectoryRouting(package_dir=PACKAGE, base_directory="routes", prefix=""))
    .use(HtmxControl(middleware=True, version="2.0.4"))
)
app = _builder.build(asgi=FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG))


@app.get("/")
def _root():
    return RedirectResponse("/index/Index")
