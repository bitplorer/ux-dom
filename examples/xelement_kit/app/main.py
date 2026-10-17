"""
XElement kit — HTMX / Alpine / Web Components.

    PYTHONPATH=examples/xelement_kit:./ uvicorn app.main:app --app-dir examples/xelement_kit --port 8080

XElement JS: single copy from installed ux_dom → GET /ux-dom/static/x_element.js
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ux_dom.plugins import App, XElementRuntime
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.runtime import XELEMENT_JS_URL
from ux_dom.response.fastapi import StreamingRoute

from app import settings
from app.pages import alpine, htmx, index, jinja, lightdom, shadowdom, slots, wc

pages = APIRouter(route_class=StreamingRoute)
for path, endpoint in (
    ("/", index.get),
    ("/alpine", alpine.get),
    ("/htmx", htmx.get),
    ("/htmx/partial", htmx.partial),
    ("/jinja", jinja.get),
    ("/lightdom", lightdom.get),
    ("/shadowdom", shadowdom.get),
    ("/slots", slots.get),
    ("/wc", wc.get),
):
    pages.get(path)(endpoint)

asgi = FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG)
asgi.include_router(pages)
app = (
    App(debug=settings.DEBUG)
    .use(XElementRuntime())  # package mount — no dual assets/js copy
    .use(HtmxControl(middleware=True, version="2.0.4"))
    .build(asgi=asgi)
)

if settings.ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(settings.ASSETS_DIR)), name="assets")



@app.get("/health", response_class=JSONResponse)
def health():
    return {
        "ok": True,
        "app": "xelement_kit",
        "runtime": "x_element.js",
        "python": "XElement",
        "runtime_url": XELEMENT_JS_URL,
    }
