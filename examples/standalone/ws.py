"""WebSocket counter: ``WebSocketAdapter`` on the server, a small script in
the browser.

    uvicorn examples.standalone.ws:app --reload         # from the repo root

Each connection gets its own ``CounterBox`` (``share_instance=False``), freed
on disconnect. The client script is a static file: the CSP runtime stamps a
nonce on its ``<script>`` tag, so no inline script is needed.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from ux_dom import Component, Document
from ux_dom.dom import button, div, h1, output, script, title
from ux_dom.response.fastapi import HTMLRoute
from ux_dom.runtime import Csp
from ux_dom.web_io import WebSocketAdapter, WebSocketClientHandler, WebSocketEvents


class CounterBox:
    def __init__(self) -> None:
        self.n = 0

    def to_dict(self) -> dict:
        return {"n": self.n}


events = WebSocketEvents()
for name in ("bump", "reset", "get"):
    events.register_event(name)


@events.on_connect
async def on_connect(self: CounterBox, websocket):
    await websocket.send_json({"event": "hello", "data": self.to_dict()})


@events.on_receive("bump")
async def on_bump(self: CounterBox, websocket, message):
    self.n += int((message.get("data") or {}).get("delta", 1))
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@events.on_receive("reset")
async def on_reset(self: CounterBox, websocket, message):
    self.n = 0
    await websocket.send_json({"event": "update", "data": self.to_dict()})


@events.on_receive("get")
async def on_get(self: CounterBox, websocket, message):
    await websocket.send_json({"event": "update", "data": self.to_dict()})


adapter = WebSocketAdapter(CounterBox, events, share_instance=False)
handler = WebSocketClientHandler({"counter": adapter})


class CounterPage(Component):
    def render(self):
        return div(
            h1("WebSocket counter"),
            output("…", id="n"),
            button("bump", id="bump", type="button", data_socket="/ws/counter"),
            id="ws-page",
        )


def create_app() -> FastAPI:
    document = Document(
        head=[script(src="/static/ws_counter.js", defer=True)],
    ).use(Csp.auto())
    app = FastAPI(title="ux-dom WebSocket counter")

    def home():
        return document(CounterPage(), head=[title("WebSocket counter")])

    async def socket(websocket: WebSocket, name: str):
        await handler(websocket, name)

    def health():
        return {"ok": True, "connections": len(adapter.connections)}

    routes = APIRouter(route_class=HTMLRoute)
    routes.add_api_route("/", home)
    routes.add_api_route("/health", health)
    app.include_router(routes)
    app.add_api_websocket_route("/ws/{name}", socket)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )
    document.mount(app)
    return app


app = create_app()
