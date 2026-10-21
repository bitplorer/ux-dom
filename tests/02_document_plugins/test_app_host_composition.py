"""Leftover App composition: Document parts + controls (not product host)."""
from __future__ import annotations

import asyncio
import unittest


from ux_dom import __version__
from ux_dom.dom import div, span, button
from ux_dom.plugins import App
from ux_dom.plugins.control import NullControl
from ux_dom.response.starlette import StreamingResponse


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
        walked = "".join(el._walk_render_tokens(0, "  ", False))
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
    def test_null_control_partial_policy(self):
        n = NullControl()
        self.assertEqual(n.partial_policy(None), "full")


class TestPluginSummary(unittest.TestCase):
    def test_summary_order(self):
        app = (
            App()
            .use(NullControl())
        )
        summary = app.plugin_summary()
        self.assertIn("control:null", summary)
        self.assertNotIn("host:fastapi", summary)


if __name__ == "__main__":
    unittest.main()
