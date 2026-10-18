"""Leftover App composition (not product host)."""

from __future__ import annotations

import asyncio
import unittest

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from ux_dom import __version__
from ux_dom.dom import button, div, span
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl, NullControl
from ux_dom.response.starlette import StreamingResponse, html_response


class TestVersion(unittest.TestCase):
    def test_version_0_2(self):
        self.assertTrue(__version__.startswith("0.2"))


class TestWalkStream(unittest.TestCase):
    def test_walk_matches_compact_render(self):
        el = div(
            span("a", id="s"),
            button("go", hx_get="/x", ws_send=True),
            className="box",
        )
        compact = el.__render__(pretty=False)
        walked = "".join(el._walk_render_tokens(0, "  ", False, False))
        self.assertEqual(compact, walked)
        self.assertIn("ws-send", walked)
        self.assertIn("hx-get", walked)

    def test_async_walk_stream(self):
        el = div(*[span(str(i)) for i in range(20)], id="root")

        async def collect():
            parts = []
            async for t in el.__async_render__(pretty=False, chunk_size=3):
                parts.append(t)
            return "".join(parts)

        body = asyncio.run(collect())
        self.assertEqual(body, el.__render__(pretty=False))
        self.assertIn('id="root"', body)

    def test_streaming_response_uses_compact(self):
        async def consume(resp):
            out = []
            async for c in resp.body_iterator:
                out.append(c.decode() if isinstance(c, bytes) else str(c))
            return "".join(out)

        body = asyncio.run(consume(StreamingResponse(div("fast"))))
        self.assertIn("fast", body)
        # compact: no leading indent newlines for single element necessarily
        self.assertEqual(body, div("fast").__render__(pretty=False))


class TestAppHostComposition(unittest.TestCase):
    def test_build_fastapi_with_explicit_routes(self):
        asgi = FastAPI(title="CutApp", debug=False, default_response_class=HTMLResponse)
        asgi.get("/api/home")(html_response(lambda: div("home-ok", id="home")))
        api = (
            App(debug=False)
            .use(HtmxControl(middleware=True))
            .build(asgi=asgi)
        )
        client = TestClient(api)
        r = client.get("/api/home")
        self.assertEqual(r.status_code, 200)
        self.assertIn("home-ok", r.text)
        self.assertIn("/api/home", api.openapi()["paths"])

class TestPluginSummary(unittest.TestCase):
    def test_summary_order(self):
        app = App().use(NullControl())
        summary = app.plugin_summary()
        self.assertIn("control:null", summary)
        self.assertNotIn("host:fastapi", summary)


if __name__ == "__main__":
    unittest.main()
