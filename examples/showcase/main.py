"""ASGI entry point.

    uvicorn examples.showcase.main:app --reload        # from the repo root

Routes are explicit: one table per response style. ``HTMLRoute`` and
``StreamingRoute`` let endpoints return ux-dom trees directly.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from ux_dom.response.fastapi import HTMLRoute, StreamingRoute

from .document import TITLE, document
from .pages import cart, guestbook, home, live, shop

pages = APIRouter(route_class=HTMLRoute)
pages.add_api_route("/", home.get)
pages.add_api_route("/shop", shop.get)
pages.add_api_route("/cart", cart.get)
pages.add_api_route("/cart", cart.post, methods=["POST"])
pages.add_api_route("/guestbook", guestbook.get)
pages.add_api_route("/guestbook", guestbook.post, methods=["POST"])
pages.add_api_route("/sse", live.sse_page)

streamed = APIRouter(route_class=StreamingRoute)
streamed.add_api_route("/stream", live.stream_page)

api = APIRouter()
api.add_api_route("/api/sse", live.sse_feed)
api.add_api_route("/health", lambda: {"ok": True, "app": "showcase"})

app = FastAPI(title=TITLE)
for router in (pages, streamed, api):
    app.include_router(router)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)
document.mount(app)  # htmx middleware + CSP middleware from the runtimes
