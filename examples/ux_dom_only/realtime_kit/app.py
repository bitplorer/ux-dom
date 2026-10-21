"""
Realtime kit — **ux_dom only**: SSE ticker, HTML streaming.

Run::

    uvicorn examples.ux_dom_only.realtime_kit.app:app --host 0.0.0.0 --port 8092
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse as ASGIStreamingResponse

from ux_dom import Component, Document
from ux_dom.dom import a, button, div, h1, h2, p
from ux_dom.response.starlette import HTMLResponse, StreamingResponse

# ── Pages ─────────────────────────────────────────────────────────────────


class Home(Component):
    def render(self):
        return div(
            h1("UxDom Realtime Kit"),
            p("SSE · streaming HTML — no ux-channel."),
            p(a("SSE ticker page", href="/sse")),
            p(a("Streamed partial", href="/stream")),
            id="home",
        )


class SsePage(Component):
    def render(self, topic: str = "market"):
        return div(
            h2("SSE Ticker"),
            div(
                "waiting…",
                id="tick",
                hx_ext="sse",
                sse_connect=f"/api/sse/{topic}",
                sse_swap="message",
            ),
            p(a("← Home", href="/")),
            id="sse-page",
            data_topic=topic,
        )


def create_app() -> FastAPI:
    app = FastAPI(title="ux_dom-realtime-kit")
    doc = Document(ensure_csrf_token=False)

    @app.get("/health")
    def health():
        return {"ok": True, "app": "ux_dom_only.realtime_kit"}

    @app.get("/")
    def home():
        return HTMLResponse(doc(Home()))

    @app.get("/sse")
    def sse_page():
        return HTMLResponse(doc(SsePage(topic="market")))

    @app.get("/stream")
    def stream_page():
        return StreamingResponse(
            div(h2("Streamed"), p("compact async walk"), id="streamed")
        )

    async def event_gen(topic: str, n: int = 0) -> AsyncIterator[str]:
        i = 0
        while n == 0 or i < n:
            payload = {"topic": topic, "i": i, "msg": f"{topic}:{i}"}
            yield f"event: message\ndata: {json.dumps(payload)}\n\n"
            i += 1
            await asyncio.sleep(0.05)

    @app.get("/api/sse/{topic}")
    async def sse(topic: str, request: Request, n: int = 0):
        async def gen():
            async for chunk in event_gen(topic, n=n):
                if await request.is_disconnected():
                    break
                yield chunk

        return ASGIStreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
