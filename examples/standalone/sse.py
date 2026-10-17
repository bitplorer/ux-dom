"""Server-sent events: htmx's SSE extension swaps HTML fragments into the page.

    uvicorn examples.standalone.sse:app --reload        # from the repo root

Each event's data is a rendered ux-dom fragment, written as one ``data:``
line per HTML line (the SSE framing for multi-line data).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import StreamingResponse

from ux_dom import Component, Document
from ux_dom.dom import div, h1, p, span, title
from ux_dom.response.fastapi import HTMLRoute
from ux_dom.runtime import Csp, Htmx


class TickerPage(Component):
    def render(self, topic: str):
        return div(
            h1("SSE ticker"),
            p(f"topic: {topic}", id="topic"),
            div(
                "waiting…",
                id="tick",
                hx_ext="sse",
                sse_connect=f"/sse/{topic}",
                sse_swap="message",
            ),
            id="page",
            data_topic=topic,
        )


class Tick(Component):
    def render(self, topic: str, i: int):
        return span(f"{topic}:{i}", className="tick", data_i=str(i))


def sse_event(html: str, event: str = "message") -> str:
    data = "".join(f"data: {line}\n" for line in html.splitlines())
    return f"event: {event}\n{data}\n"


def create_app() -> FastAPI:
    document = Document().use(Htmx(version="2.0.4", sse=True), Csp.auto())
    app = FastAPI(title="ux-dom SSE ticker")

    def home():
        return document(TickerPage(topic="market"), head=[title("SSE ticker")])

    async def feed(topic: str, request: Request, n: int = 0):
        """``n`` limits the number of events (tests); ``0`` streams forever."""

        async def frames() -> AsyncIterator[str]:
            i = 0
            while n == 0 or i < n:
                if await request.is_disconnected():
                    break
                yield ": heartbeat\n"
                yield sse_event(str(Tick(topic=topic, i=i)))
                i += 1
                await asyncio.sleep(0.01 if n else 1.0)

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    routes = APIRouter(route_class=HTMLRoute)
    routes.add_api_route("/", home)
    routes.add_api_route("/sse/{topic}", feed)
    routes.add_api_route("/health", lambda: {"ok": True})
    app.include_router(routes)
    document.mount(app)
    return app


app = create_app()
