"""Build phase (enter/aenter) vs serialize phase (render/async_render).

Invariant
---------
* ``__enter__`` / ``__exit__`` and ``__aenter__`` / ``__aexit__`` only run during
  tree **construction** (``with`` / ``async with``).
* ``__render__`` / ``__async_render__`` only **serialize** an already-built tree;
  they must not open/close context frames.

Recommended pairing
-------------------
* sync:  ``with``  → ``__render__()`` or compact token walk
* async: ``async with`` → ``__async_render__()`` stream

Cross pairing remains supported (sync-built tree may async-stream, etc.).
"""

from __future__ import annotations

import asyncio
import unittest

from ux_dom.dom import div, span, button
from ux_dom.dom.src.dom_tag import dom_tag


async def _collect(el, **kwargs):
    parts = []
    async for t in el.__async_render__(pretty=False, **kwargs):
        parts.append(t)
    return "".join(parts)


class TestBuildVsSerialize(unittest.TestCase):
    def test_sync_with_uses_enter_exit_not_async(self):
        calls = {"enter": 0, "exit": 0, "aenter": 0, "aexit": 0}
        o_enter, o_exit = dom_tag.__enter__, dom_tag.__exit__
        o_aenter, o_aexit = dom_tag.__aenter__, dom_tag.__aexit__

        def enter(self):
            calls["enter"] += 1
            return o_enter(self)

        def exit_(self, *a):
            calls["exit"] += 1
            return o_exit(self, *a)

        async def aenter(self):
            calls["aenter"] += 1
            return await o_aenter(self)

        async def aexit(self, *a):
            calls["aexit"] += 1
            return await o_aexit(self, *a)

        dom_tag.__enter__, dom_tag.__exit__ = enter, exit_
        dom_tag.__aenter__, dom_tag.__aexit__ = aenter, aexit
        try:
            with div(id="s") as root:
                span("x")
            self.assertEqual(calls["enter"], 1)
            self.assertEqual(calls["exit"], 1)
            self.assertEqual(calls["aenter"], 0)
            self.assertEqual(calls["aexit"], 0)

            # serialize must not touch context managers
            before = dict(calls)
            html = root.__render__(pretty=False)
            self.assertEqual(calls, before)
            self.assertIn("x", html)

            before = dict(calls)
            streamed = asyncio.run(_collect(root))
            self.assertEqual(calls, before)
            self.assertEqual(streamed, html)
        finally:
            dom_tag.__enter__, dom_tag.__exit__ = o_enter, o_exit
            dom_tag.__aenter__, dom_tag.__aexit__ = o_aenter, o_aexit

    def test_async_with_uses_aenter_aexit(self):
        calls = {"enter": 0, "exit": 0, "aenter": 0, "aexit": 0}
        o_enter, o_exit = dom_tag.__enter__, dom_tag.__exit__
        o_aenter, o_aexit = dom_tag.__aenter__, dom_tag.__aexit__

        def enter(self):
            calls["enter"] += 1
            return o_enter(self)

        def exit_(self, *a):
            calls["exit"] += 1
            return o_exit(self, *a)

        async def aenter(self):
            calls["aenter"] += 1
            return await o_aenter(self)

        async def aexit(self, *a):
            calls["aexit"] += 1
            return await o_aexit(self, *a)

        dom_tag.__enter__, dom_tag.__exit__ = enter, exit_
        dom_tag.__aenter__, dom_tag.__aexit__ = aenter, aexit
        try:

            async def build():
                async with div(id="a") as root:
                    span("y")
                    button("go", hx_get="/z")
                return root

            root = asyncio.run(build())
            # aenter delegates stack push to enter → both increment
            self.assertEqual(calls["aenter"], 1)
            self.assertEqual(calls["aexit"], 1)
            self.assertEqual(calls["enter"], 1)
            self.assertEqual(calls["exit"], 1)

            before = dict(calls)
            html = root.__render__(pretty=False)
            streamed = asyncio.run(_collect(root))
            self.assertEqual(calls, before)  # serialize still no enter/exit
            self.assertEqual(html, streamed)
            self.assertIn("y", html)
            self.assertIn("hx-get", html)
        finally:
            dom_tag.__enter__, dom_tag.__exit__ = o_enter, o_exit
            dom_tag.__aenter__, dom_tag.__aexit__ = o_aenter, o_aexit

    def test_recommended_pairings_produce_identical_html(self):
        # sync build → sync render
        with div(className="box") as sroot:
            span("hello")
        sync_html = sroot.__render__(pretty=False)

        # async build → async render
        async def async_pipeline():
            async with div(className="box") as aroot:
                span("hello")
            return await _collect(aroot)

        async_html = asyncio.run(async_pipeline())
        self.assertEqual(sync_html, async_html)

    def test_cross_pairing_still_works(self):
        # sync build → async stream
        with div(id="c") as root:
            span("cross")
        self.assertEqual(
            asyncio.run(_collect(root)),
            root.__render__(pretty=False),
        )

        # async build → sync render
        async def abuild():
            async with div(id="d") as root:
                span("cross2")
            return root

        root = asyncio.run(abuild())
        self.assertIn("cross2", root.__render__(pretty=False))

    def test_nested_async_with_stack(self):
        async def build():
            async with div(id="outer") as outer:
                async with span(id="inner") as inner:
                    button("ok")
                span("sibling")
            return outer

        html = asyncio.run(build()).__render__(pretty=False)
        self.assertIn('id="outer"', html)
        self.assertIn('id="inner"', html)
        self.assertIn("sibling", html)
        self.assertIn("ok", html)

    def test_component_render_uses_sync_with_then_either_serialize(self):
        from ux_dom import Component

        class Card(Component):
            def render(self, title="t"):
                with div(className="card") as root:
                    span(title)
                return root

        c = Card(title="Hi")
        sync = c.__render__(pretty=False)
        async_ = asyncio.run(_collect(c))
        self.assertEqual(sync, async_)
        self.assertIn("Hi", sync)
        self.assertIn("card", sync)


if __name__ == "__main__":
    unittest.main()
