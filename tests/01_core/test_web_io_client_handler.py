"""Characterize ``WebSocketClientHandler`` end to end over a real Starlette socket."""

from __future__ import annotations

import unittest

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect

from ux_dom.web_io import WebSocketAdapter, WebSocketClientHandler, WebSocketEvents


class Box:
    def __init__(self):
        self.n = 0


def _app():
    events = WebSocketEvents()

    @events.on_connect
    async def hello(self, websocket):
        await websocket.send_json({"event": "hello", "n": self.n})

    @events.on_receive("bump")
    async def bump(self, websocket, message):
        self.n += 1
        await websocket.send_json({"event": "update", "n": self.n})

    adapter = WebSocketAdapter(Box, events)
    handler = WebSocketClientHandler({"box": adapter})

    async def ws(websocket: WebSocket):
        await handler(websocket, websocket.path_params["name"])

    app = Starlette(routes=[WebSocketRoute("/ws/{name}", ws)])
    return app, adapter, handler


class TestWebSocketClientHandler(unittest.TestCase):
    def test_round_trip_then_release(self):
        app, adapter, handler = _app()
        with TestClient(app) as client:
            with client.websocket_connect("/ws/box") as ws:
                self.assertEqual(ws.receive_json(), {"event": "hello", "n": 0})
                ws.send_json({"event": "bump"})
                self.assertEqual(ws.receive_json(), {"event": "update", "n": 1})
                self.assertEqual(len(adapter.connections), 1)
        self.assertEqual(adapter.connections, set())
        self.assertEqual(handler.all_connections["box"], set())
        self.assertEqual(adapter._instances, {})

    def test_each_connection_gets_its_own_instance(self):
        app, _, _ = _app()
        with TestClient(app) as client:
            with client.websocket_connect("/ws/box") as a:
                a.receive_json()
                a.send_json({"event": "bump"})
                self.assertEqual(a.receive_json()["n"], 1)
            with client.websocket_connect("/ws/box") as b:
                self.assertEqual(b.receive_json(), {"event": "hello", "n": 0})

    def test_unknown_adapter_closes(self):
        app, _, _ = _app()
        with TestClient(app) as client:
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect("/ws/nope"):
                    pass


if __name__ == "__main__":
    unittest.main()
