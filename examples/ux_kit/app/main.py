from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.response.starlette import HTMLResponse

from app import settings
from app.routes.index import Index

PACKAGE = Path(__file__).resolve().parent

_builder = (
    App(debug=settings.DEBUG)
    .use(HtmxControl(middleware=True, version="2.0.4"))
)
app = _builder.build(asgi=FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG))



@app.get("/")
def gallery():
    return HTMLResponse(Index.page_view())
