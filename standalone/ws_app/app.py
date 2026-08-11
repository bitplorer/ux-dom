"""Standalone WebSocket counter using WebSocketAdapter + ux_dom HTML."""
from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ux_dom import Component, Document
from ux_dom.dom import div, span, button, h1
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.response.starlette import HTMLResponse
from ux_dom.web_io import WebSocketAdapter, WebSocketEvents, WebSocketClientHandler


class CounterBox:
    def __init__(self):
        self.n = 0

    def bump(self, delta: int = 1):
        self.n += delta
        return self.n

    def to_dict(self):
        return {"n": self.n}


events = WebSocketEvents()
for name in ("bump", "reset", "get"):
    events.register_event(name)


@events.on_receive("bump")
async def on_bump(self: CounterBox, websocket, message):
    d = int((message.get("data") or {}).get("delta", 1))
    self.bump(d)
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@events.on_receive("reset")
async def on_reset(self: CounterBox, websocket, message):
    self.n = 0
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@events.on_receive("get")
async def on_get(self: CounterBox, websocket, message):
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@events.on_connect
async def on_hello(self: CounterBox, websocket):
    await websocket.send_json({"event": "hello", "data": self.to_dict()})


adapter = WebSocketAdapter(CounterBox, events, share_instance=False)
handler = WebSocketClientHandler({"counter": adapter})


class WSPage(Component):
    def render(self):
        return div(
            h1("WS Counter"),
            span("n=?", id="n"),
            button("bump", id="bump", data_socket="/ws/counter"),
            id="ws-page",
        )


def create_app() -> FastAPI:
    app = FastAPI(title="ux_dom-ws")
    app.add_middleware(HtmxMiddleware)
    doc = Document(ensure_csrf_token=False)

    @app.get("/")
    def home():
        return HTMLResponse(doc(WSPage()))

    @app.websocket("/ws/{name}")
    async def ws_endpoint(websocket: WebSocket, name: str):
        await handler(websocket, name)

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "connections": len(adapter.connections),
            "instances": len(adapter._instances),
        }

    return app


app = create_app()
