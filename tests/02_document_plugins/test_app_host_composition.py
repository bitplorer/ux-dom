"""App + FastAPIHost + DirectoryRouting composition (production cut)."""
from __future__ import annotations

import asyncio
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ux_dom import __version__, Component
from ux_dom.dom import div, span, button
from ux_dom.plugins import App
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.plugins.control import HtmxControl, NullControl
from ux_dom.plugins.style import NullStyle
from ux_dom.plugins.response import StreamingResponsePlugin
from ux_dom.response.starlette import StreamingResponse


class TestVersion(unittest.TestCase):
    def test_version_0_1(self):
        self.assertTrue(__version__.startswith("0.1"))


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
    def test_build_fastapi_with_directory_routes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "cutapp"
            (pkg / "app").mkdir(parents=True)
            (pkg / "__init__.py").write_text("")
            (pkg / "app" / "__init__.py").write_text("")
            (pkg / "app" / "home.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div
                    __all__ = ["Home"]
                    class Home(Component):
                        routes = ["get"]
                        def render(self):
                            return div("home-ok", id="home")
                        @classmethod
                        def get(cls):
                            return cls()
                    """))
            sys.path.insert(0, str(root))
            try:
                api = (
                    App(debug=False)
                    .use(FastAPIHost(title="CutApp", debug=False))
                    .use(
                        DirectoryRouting(
                            package_dir=pkg,
                            base_directory="app",
                            prefix="/api",
                        )
                    )
                    .use(HtmxControl(middleware=True))
                    .use(NullStyle())
                    .build()
                )
                self.assertIsNotNone(api)
                client = TestClient(api)
                # HTMX middleware present
                r = client.get("/api/home/Home")
                self.assertEqual(r.status_code, 200)
                self.assertIn("home-ok", r.text)
                # openapi lists path
                paths = api.openapi()["paths"]
                self.assertTrue(any("Home" in p for p in paths))
            finally:
                sys.path.remove(str(root))

    def test_null_control_and_response_plugin(self):
        n = NullControl()
        self.assertEqual(n.partial_policy(None), "full")
        wrap = StreamingResponsePlugin().wrap

        @wrap
        def ep():
            return div("w")

        resp = ep()
        self.assertTrue(hasattr(resp, "body_iterator"))


class TestPluginSummary(unittest.TestCase):
    def test_summary_order(self):
        app = (
            App()
            .use(NullStyle())
            .use(NullControl())
            .use(FastAPIHost(title="x", debug=False))
        )
        summary = app.plugin_summary()
        self.assertIn("style:null", summary)
        self.assertIn("control:null", summary)
        self.assertIn("host:fastapi", summary)


if __name__ == "__main__":
    unittest.main()
