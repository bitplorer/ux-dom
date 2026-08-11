"""Pretty serialize — safe same-thread default; optional hardened worker."""

from __future__ import annotations

import asyncio
import threading
import unittest

from ux_dom import Document
from ux_dom.dom import div, p, span
from ux_dom.dom.src.ext import Tags


class TestPrettyStream(unittest.TestCase):
    def test_pretty_walk_equals_str(self):
        tree = div(div(span("a"), span("b")), p("hello"))
        s = tree.__render__(pretty=True)
        w = "".join(tree._walk_render_tokens(0, "  ", True, False))
        self.assertEqual(s, w)

    def test_pretty_async_equals_str(self):
        tree = div(span("x"), div(p("y")))
        s = tree.__render__(pretty=True)

        async def run():
            return "".join(
                [t async for t in tree.__async_render__(pretty=True, chunk_size=1)]
            )

        self.assertEqual(asyncio.run(run()), s)

    def test_safe_mode_matches_str(self):
        tree = div(*[span(str(i)) for i in range(30)])
        s = tree.__render__(pretty=True)
        streamed = "".join(
            tree._iter_pretty_stream(0, "  ", True, False, stream_mode="safe")
        )
        self.assertEqual(s, streamed)

    def test_worker_mode_matches_str(self):
        tree = div(*[span(str(i)) for i in range(30)])
        s = tree.__render__(pretty=True)
        streamed = "".join(
            tree._iter_pretty_stream(
                0, "  ", True, False, maxsize=8, stream_mode="worker"
            )
        )
        self.assertEqual(s, streamed)

    def test_safe_mode_no_extra_thread(self):
        tree = div(span("a"))
        before = threading.active_count()
        list(tree._iter_pretty_stream(0, "  ", True, False, stream_mode="safe"))
        after = threading.active_count()
        self.assertEqual(before, after)

    def test_compact_does_not_call_render_list(self):
        tree = div(span("a"), span("b"))
        calls = {"n": 0}
        orig = Tags._render

        def counting(self, sb, *a, **k):
            calls["n"] += 1
            return orig(self, sb, *a, **k)

        Tags._render = counting  # type: ignore
        try:
            list(tree._walk_render_tokens(0, "  ", False, False))
            self.assertEqual(calls["n"], 0)
        finally:
            Tags._render = orig  # type: ignore

    def test_document_async_pretty(self):
        tree = Document(ensure_csrf_token=False)(div("x"))

        async def run():
            return "".join([t async for t in tree.__async_render__(pretty=True)])

        html = asyncio.run(run())
        self.assertIn("charset", html)

    def test_unknown_mode_raises(self):
        tree = div("x")
        with self.assertRaises(ValueError):
            list(tree._iter_pretty_stream(0, "  ", True, False, stream_mode="nope"))


if __name__ == "__main__":
    unittest.main()
