"""HTMX pure-ASGI middleware, WebSocket adapter, async HTML streaming."""
from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import StreamingResponse as StarletteStreaming

from ux_dom import __version__
from ux_dom.dom import div
from ux_dom.htmx.middleware import HtmxDetails, HtmxMiddleware
from ux_dom.htmx import Htmx
from ux_dom.response.starlette import StreamingResponse
from ux_dom.web_io import WebSocketAdapter, WebSocketEvents


class TestVersion(unittest.TestCase):
    def test_version_0_1(self):
        self.assertTrue(__version__.startswith("0.1"))


class TestHtmxPureASGI(unittest.TestCase):
    def test_middleware_sets_request_state(self):
        app = FastAPI()
        app.add_middleware(HtmxMiddleware)

        @app.get("/ping")
        def ping(request: Request):
            h = request.state.htmx
            return {
                "is_htmx": bool(h),
                "target": h.target,
            }

        client = TestClient(app)
        r = client.get("/ping")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["is_htmx"])

        r2 = client.get(
            "/ping",
            headers={"HX-Request": "true", "HX-Target": "main"},
        )
        self.assertTrue(r2.json()["is_htmx"])
        self.assertEqual(r2.json()["target"], "main")

    def test_streaming_still_works_with_middleware(self):
        """BaseHTTPMiddleware historically broke streaming; pure ASGI must not."""
        app = FastAPI()
        app.add_middleware(HtmxMiddleware)

        @app.get("/stream2")
        def stream2():
            return StreamingResponse(div("stream-body"))

        client = TestClient(app)
        r = client.get("/stream2")
        self.assertEqual(r.status_code, 200)
        self.assertIn("stream-body", r.text)

    def test_details_from_request(self):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-trigger", b"btn"),
            ],
            "client": ("127.0.0.1", 123),
            "server": ("test", 80),
            "scheme": "http",
        }
        d = HtmxDetails(scope)
        self.assertTrue(bool(d))
        self.assertEqual(d.trigger, "btn")


class TestHtmxPrefix(unittest.TestCase):
    def test_prefix_paths(self):
        class API:
            def __init__(self):
                self.routes = []

            def _reg(self, method):
                def deco_path(path):
                    def deco(fn):
                        self.routes.append((method, path))
                        return fn

                    return deco

                return deco_path

            def get(self, path):
                return self._reg("GET")(path)

            def post(self, path):
                return self._reg("POST")(path)

            put = patch = delete = post

        api = API()
        h = Htmx(api, prefix="/actions")

        @h.get
        def counter():
            pass

        self.assertEqual(api.routes[0], ("GET", "/actions/counter"))

        api2 = API()
        h2 = Htmx(api2)  # default flat for back-compat

        @h2.post
        def save():
            pass

        self.assertEqual(api2.routes[0], ("POST", "/save"))


class TestWebSocketPerConnection(unittest.TestCase):
    def test_default_not_shared(self):
        events = WebSocketEvents()

        class Box:
            def __init__(self):
                self.n = 0

        adapter = WebSocketAdapter(Box, events)
        self.assertFalse(adapter.share_instance)

        class FakeWS:
            pass

        a, b = FakeWS(), FakeWS()

        async def run():
            ia = await adapter.ensure_instance(a)
            ib = await adapter.ensure_instance(b)
            ia.n = 1
            self.assertEqual(ib.n, 0)  # isolated
            self.assertIsNot(ia, ib)
            adapter.release_instance(a)
            adapter.release_instance(b)

        asyncio.run(run())

    def test_share_instance_opt_in(self):
        events = WebSocketEvents()

        class Box:
            def __init__(self):
                self.n = 0

        adapter = WebSocketAdapter(Box, events, share_instance=True)

        class FakeWS:
            pass

        a, b = FakeWS(), FakeWS()

        async def run():
            ia = await adapter.ensure_instance(a)
            ib = await adapter.ensure_instance(b)
            ia.n = 5
            self.assertIs(ia, ib)
            self.assertEqual(ib.n, 5)

        asyncio.run(run())


class TestAsyncRenderCoop(unittest.TestCase):
    def test_async_render_yields_all(self):
        el = div("hello", id="x")

        async def collect():
            parts = []
            async for t in el.__async_render__(pretty=False, chunk_size=1):
                parts.append(t)
            return "".join(parts)

        body = asyncio.run(collect())
        self.assertEqual(body, el.__render__(pretty=False))
        self.assertIn("hello", body)


if __name__ == "__main__":
    unittest.main()
