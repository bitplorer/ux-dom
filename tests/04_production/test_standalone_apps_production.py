"""Production / load / chaos tests for standalone SSE, WS, MCP, HTMX apps."""

from __future__ import annotations

import concurrent.futures
import unittest

from fastapi.testclient import TestClient

from standalone.htmx_stream_app.app import SearchBox, create_app as htmx_app
from standalone.mcp_app.app import create_app as mcp_app
from standalone.sse_app.app import create_app as sse_app
from standalone.ws_app.app import create_app as ws_app
from ux_dom.dom import div


class TestSSEApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(sse_app())

    def test_health_and_page(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("tick", r.text)

    def test_sse_dialect(self):
        h = div(sse_connect="/sse/x", sse_swap="message").__render__(pretty=False)
        self.assertIn("sse-connect", h)
        self.assertIn("sse-swap", h)

    def test_sse_stream_and_load(self):
        r = self.client.get("/sse/market?n=5")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/event-stream", r.headers.get("content-type", ""))
        self.assertIn("market:0", r.text)

        def hit(i):
            rr = self.client.get(f"/sse/t{i}?n=2")
            return rr.status_code == 200 and f"t{i}:0" in rr.text

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            self.assertTrue(all(ex.map(hit, range(30))))


class TestWSApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(ws_app())

    def test_page_and_protocol(self):
        self.assertIn("WS Counter", self.client.get("/").text)
        with self.client.websocket_connect("/ws/counter") as ws:
            hello = ws.receive_json()
            self.assertEqual(hello.get("event"), "hello")
            ws.send_json({"event": "bump", "data": {"delta": 3}})
            msg = ws.receive_json()
            self.assertEqual(msg["data"]["n"], 3)
            ws.send_json({"event": "reset", "data": {}})
            self.assertEqual(ws.receive_json()["data"]["n"], 0)

    def test_isolation_and_cleanup(self):
        cms = []
        for _ in range(6):
            cm = self.client.websocket_connect("/ws/counter")
            w = cm.__enter__()
            w.receive_json()
            cms.append((cm, w))
        ns = []
        for i, (_, w) in enumerate(cms):
            w.send_json({"event": "bump", "data": {"delta": i + 1}})
            ns.append(w.receive_json()["data"]["n"])
        self.assertEqual(ns, list(range(1, 7)))
        for cm, _ in cms:
            cm.__exit__(None, None, None)
        h = self.client.get("/health").json()
        self.assertEqual(h.get("instances"), 0)
        self.assertEqual(h.get("connections"), 0)

    def test_malformed_data_without_event_keeps_connection(self):
        with self.client.websocket_connect("/ws/counter") as ws:
            ws.receive_json()  # hello
            ws.send_json({"data": {"x": 1}})  # no event — must not kill conn
            ws.send_json({"event": "get", "data": {}})
            msg = ws.receive_json()
            self.assertEqual(msg.get("event"), "update")


class TestMCPApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(mcp_app())

    def test_tools_http(self):
        self.assertGreaterEqual(
            len(self.client.get("/mcp/tools/list").json()["tools"]), 3
        )
        r = self.client.post(
            "/mcp/tools/call", json={"name": "echo", "arguments": {"text": "hi"}}
        )
        self.assertEqual(r.json()["result"], "hi")
        self.assertIn("hi", r.json()["html"])
        r = self.client.post(
            "/mcp/tools/call",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "add", "arguments": {"a": 2, "b": 3}},
            },
        )
        self.assertEqual(r.json()["result"]["result"], 5)

    def test_tools_ws_and_load(self):
        with self.client.websocket_connect("/mcp/ws") as ws:
            ws.send_json({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertIn("tools", ws.receive_json()["result"])
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "echo", "arguments": {"text": "ws"}},
                }
            )
            self.assertEqual(ws.receive_json()["result"]["result"], "ws")

        def hit(i):
            rr = self.client.post(
                "/mcp/tools/call", json={"name": "add", "arguments": {"a": i, "b": 1}}
            )
            return rr.json().get("result") == i + 1

        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            self.assertTrue(all(ex.map(hit, range(40))))


class TestHTMXStreamApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(htmx_app())

    def test_route_shadow_and_partials(self):
        sb = SearchBox.get()
        self.assertTrue(sb.get(id="q"))
        r = self.client.get("/search?q=abc", headers={"HX-Request": "true"})
        self.assertIn("abc-0", r.text)

        def hit(i):
            rr = self.client.get(f"/search?q=q{i}", headers={"HX-Request": "true"})
            return rr.status_code == 200 and f"q{i}-0" in rr.text

        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            self.assertTrue(all(ex.map(hit, range(50))))


if __name__ == "__main__":
    unittest.main()
