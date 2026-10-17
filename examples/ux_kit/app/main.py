from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app import settings
from app.pages import index
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.response.fastapi import StreamingRoute

pages = APIRouter(route_class=StreamingRoute)
pages.get("/")(index.get)

asgi = FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG)
asgi.include_router(pages)
app = App(debug=settings.DEBUG).use(HtmxControl(middleware=True, version="2.0.4")).build(asgi=asgi)
