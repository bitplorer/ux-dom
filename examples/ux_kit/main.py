"""ASGI entry point.

uvicorn examples.ux_kit.main:app --reload        # from the repo root
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Query

from ux_dom.response.fastapi import HTMLRoute

from . import gallery
from .document import document


def index(
    tab: str = Query("a", pattern="^(a|b)$"),
    slide: int = Query(0, ge=0, le=len(gallery.SLIDES) - 1),
    dialog: bool = False,
):
    return gallery.get(tab=tab, slide=slide, dialog_open=dialog)


pages = APIRouter(route_class=HTMLRoute)
pages.add_api_route("/", index)
pages.add_api_route("/toast", gallery.toast_fragment, methods=["POST"])

app = FastAPI(title="UxDom UI kit")
app.include_router(pages)
app.add_api_route("/health", lambda: {"ok": True, "app": "ux_kit"})
document.mount(app)
