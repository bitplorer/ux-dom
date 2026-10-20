"""
XElement kit — HTMX / Alpine / Web Components.

    PYTHONPATH=examples/xelement_kit:./ uvicorn app.main:app --app-dir examples/xelement_kit --port 8080

XElement JS: single copy from installed ux_dom → GET /ux-dom/static/x_element.js
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ux_dom.plugins import App, XElementRuntime
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.runtime import XELEMENT_JS_URL
from ux_dom.response.starlette import HTMLResponse

from app import settings
from app.routes import alpine, htmx, index, jinja, lightdom, shadowdom, slots, wc

PACKAGE = Path(__file__).resolve().parent

app = (
    App(debug=settings.DEBUG)
    .use(XElementRuntime())  # package mount — no dual assets/js copy
    .use(HtmxControl(middleware=True, version="2.0.4"))
    .build(asgi=FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG))
)

# Explicit page table (ux-dom has no file router; product routing is ux-compose).
PAGES = {
    "/": index.Index,
    "/wc": wc.WC,
    "/slots": slots.Slots,
    "/shadowdom": shadowdom.ShadowDom,
    "/lightdom": lightdom.LightDom,
    "/alpine": alpine.Alpine,
    "/jinja": jinja.Jinja,
    "/htmx": htmx.Htmx,
}


def _page_endpoint(cls):
    def endpoint():
        return HTMLResponse(cls.page_view())

    endpoint.__name__ = f"page_{cls.__name__}"
    return endpoint


for _path, _cls in PAGES.items():
    app.add_api_route(_path, _page_endpoint(_cls), methods=["GET"])


@app.get("/htmx/partial")
def htmx_partial():
    return HTMLResponse(htmx.Htmx.partial())


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
