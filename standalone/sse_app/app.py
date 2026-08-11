"""Standalone SSE ticker: ux_dom HTML pages + text/event-stream feed."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse as ASGIStreamingResponse
from starlette.responses import Response

from ux_dom import Component, Document
from ux_dom.dom import div, span, button, script, h1, p
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.response.starlette import HTMLResponse, StreamingResponse


class TickerPage(Component):
    def render(self, topic: str = "market"):
        return div(
            h1("SSE Ticker"),
            p(f"topic={topic}", id="topic"),
            div("waiting…", id="tick", sse_swap="message", hx_ext="sse", sse_connect=f"/sse/{topic}"),
            # raw hooks for non-htmx clients
            div(id="log", className="log"),
            id="page",
            data_topic=topic,
        )


def create_app() -> FastAPI:
    app = FastAPI(title="ux_dom-sse")
    app.add_middleware(HtmxMiddleware)
    doc = Document(ensure_csrf_token=False)

    @app.get("/")
    def home():
        return HTMLResponse(doc(TickerPage(topic="market")))

    @app.get("/partial")
    def partial():
        # HTMX partial stream of a component
        return StreamingResponse(TickerPage(topic="partial"))

    async def event_gen(topic: str, n: int = 0) -> AsyncIterator[str]:
        """SSE event stream. n=0 means infinite (capped in tests via client close)."""
        i = 0
        while n == 0 or i < n:
            payload = {"topic": topic, "i": i, "msg": f"{topic}:{i}"}
            # comment + event + data lines
            yield f": heartbeat\n"
            yield f"event: message\n"
            yield f"data: {json.dumps(payload)}\n\n"
            i += 1
            await asyncio.sleep(0.01)

    @app.get("/sse/{topic}")
    async def sse(topic: str, request: Request, n: int = 0):
        async def gen():
            async for chunk in event_gen(topic, n=n):
                if await request.is_disconnected():
                    break
                yield chunk

        return ASGIStreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
