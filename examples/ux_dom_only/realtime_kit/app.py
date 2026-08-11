"""
Realtime kit — **ux_dom only**: SSE ticker, WebSocket counter, HTML streaming.

Run::

    uvicorn examples.ux_dom_only.realtime_kit.app:app --host 0.0.0.0 --port 8092
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse as ASGIStreamingResponse

from ux_dom import Component, Document
from ux_dom.dom import a, button, div, h1, h2, p, span
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.response.starlette import HTMLResponse, StreamingResponse
from ux_dom.web_io import WebSocketAdapter, WebSocketClientHandler, WebSocketEvents

# ── WS state ──────────────────────────────────────────────────────────────

class CounterBox:
    def __init__(self) -> None:
        self.n = 0

    def to_dict(self) -> dict:
        return {"n": self.n}


_events = WebSocketEvents()


@_events.on_receive("bump")
async def _on_bump(self: CounterBox, websocket, message):
    delta = int((message.get("data") or {}).get("delta", 1))
    self.n += delta
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@_events.on_receive("get")
async def _on_get(self: CounterBox, websocket, message):
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@_events.on_connect
async def _on_hello(self: CounterBox, websocket):
    await websocket.send_json({"event": "hello", "data": self.to_dict()})


_adapter = WebSocketAdapter(CounterBox, _events, share_instance=False)
_handler = WebSocketClientHandler({"counter": _adapter})

# ── Pages ─────────────────────────────────────────────────────────────────


class Home(Component):
    def render(self):
        return div(
            h1("UxDom Realtime Kit"),
            p("SSE · WebSocket · streaming HTML — no ux-channel."),
            p(a("SSE ticker page", href="/sse")),
            p(a("WebSocket counter page", href="/ws-page")),
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


class WsPage(Component):
    def render(self):
        return div(
            h2("WebSocket Counter"),
            span("n=?", id="n"),
            p("Open DevTools → Network → WS → send ", span('{"event":"bump","data":{"delta":1}}', className="code")),
            p(a("← Home", href="/")),
            id="ws-page",
            data_socket="/ws/counter",
        )


def create_app() -> FastAPI:
    app = FastAPI(title="ux_dom-realtime-kit")
    app.add_middleware(HtmxMiddleware)
    doc = Document(ensure_csrf_token=False)

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "app": "ux_dom_only.realtime_kit",
            "ws_connections": len(_adapter.connections),
            "ws_instances": len(_adapter._instances),
        }

    @app.get("/")
    def home():
        return HTMLResponse(doc(Home()))

    @app.get("/sse")
    def sse_page():
        return HTMLResponse(doc(SsePage(topic="market")))

    @app.get("/ws-page")
    def ws_page():
        return HTMLResponse(doc(WsPage()))

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

    @app.websocket("/ws/{name}")
    async def ws_endpoint(websocket: WebSocket, name: str):
        await _handler(websocket, name)

    return app


app = create_app()
