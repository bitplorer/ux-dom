"""ASGI entry point.

uvicorn examples.xelement_kit.main:app --reload        # from the repo root
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from ux_dom.response.fastapi import HTMLRoute
from ux_dom.runtime import XELEMENT_JS_URL

from .document import TITLE, document
from .pages import alpine, htmx, index, jinja, lightdom, shadowdom, slots, wc

pages = APIRouter(route_class=HTMLRoute)
pages.add_api_route("/", index.get)
pages.add_api_route("/lightdom", lightdom.get)
pages.add_api_route("/shadowdom", shadowdom.get)
pages.add_api_route("/wc", wc.get)
pages.add_api_route("/alpine", alpine.get)
pages.add_api_route("/htmx", htmx.get)
pages.add_api_route("/htmx/partial", htmx.partial)
pages.add_api_route("/jinja", jinja.get)
pages.add_api_route("/slots", slots.get)


def health():
    return {
        "ok": True,
        "app": "xelement_kit",
        "runtime": "x_element.js",
        "runtime_url": XELEMENT_JS_URL,
    }


app = FastAPI(title=TITLE)
app.include_router(pages)
app.add_api_route("/health", health)
document.mount(app)  # serves x_element.js from the package
