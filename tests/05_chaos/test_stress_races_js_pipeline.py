"""Load/chaos races, deadlock guards, py→js pipeline, concurrent HTTP."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ux_dom import Component
from ux_dom.dom import div, span, button
from ux_dom.dom.src.dom_tag import get_current
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.response.starlette import StreamingResponse


class Card(Component):
    def render(self, n=0):
        return div(span(f"c{n}", id=f"t{n}"), id=f"c{n}", hx_get="/x")


class TestContextRaces(unittest.TestCase):
    def test_threads_and_async_isolation(self):
        errors = []

        def thr(tid):
            for i in range(40):
                with div(id=f"T{tid}-{i}") as r:
                    Card(n=i)
                if f"T{tid}-{i}" not in r.__render__(pretty=False):
                    errors.append((tid, i))

        async def ath(aid):
            for i in range(40):
                async with div(id=f"A{aid}-{i}") as r:
                    Card(n=i)
                if f"A{aid}-{i}" not in r.__render__(pretty=False):
                    errors.append((f"a{aid}", i))

        async def run_a():
            await asyncio.gather(*[ath(a) for a in range(8)])

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            futs = [ex.submit(thr, t) for t in range(8)]
            asyncio.run(run_a())
            concurrent.futures.wait(futs)
        self.assertEqual(errors, [])

    def test_exception_storm_clean(self):
        async def one(i):
            try:
                async with div(id=f"e{i}"):
                    if i % 2 == 0:
                        raise RuntimeError("x")
                    span("ok")
            except RuntimeError:
                pass
            try:
                get_current()
                return False
            except ValueError:
                return True

        async def run():
            return await asyncio.gather(*[one(i) for i in range(100)])

        self.assertTrue(all(asyncio.run(run())))


class TestRenderRaces(unittest.TestCase):
    def test_concurrent_idempotent_render(self):
        root = div(*[Card(n=i) for i in range(30)], id="deck")
        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            outs = list(ex.map(lambda _: root.__render__(pretty=False), range(100)))
        self.assertEqual(len(set(outs)), 1)

    def test_mutate_render_same_tree_no_crash(self):
        live = div(id="live")
        crash = []

        def mutator():
            for i in range(150):
                try:
                    live.add(span(str(i)))
                except Exception as e:
                    crash.append(str(e))

        def renderer():
            for _ in range(150):
                try:
                    live.__render__(pretty=False)
                except Exception as e:
                    crash.append(str(e))

        with concurrent.futures.ThreadPoolExecutor(2) as ex:
            concurrent.futures.wait([ex.submit(mutator), ex.submit(renderer)])
        self.assertEqual(crash, [])
        live.__render__(pretty=False)

    def test_uniqueid_race(self):
        bag = []
        lock = threading.Lock()

        def gen(_):
            local = [uniqueid() if i % 2 == 0 else next(uniqueid) for i in range(300)]
            with lock:
                bag.extend(local)

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            list(ex.map(gen, range(12)))
        self.assertEqual(len(bag), len(set(bag)))


class TestDeadlockGuards(unittest.TestCase):
    def test_deep_async_with_timeout(self):
        async def deep(i, d=15):
            async def nest(level):
                if level == 0:
                    span("L")
                    return
                async with div(id=f"d{i}-{level}"):
                    await nest(level - 1)

            async with div(id=f"root{i}") as r:
                await nest(d)
            return r.__render__(pretty=False)

        async def many():
            return await asyncio.wait_for(
                asyncio.gather(*[deep(i) for i in range(20)]), timeout=10
            )

        outs = asyncio.run(many())
        for i, h in enumerate(outs):
            self.assertIn(f"root{i}", h)


class TestJsPipeline(unittest.TestCase):
    def test_py_attrs_to_html_js_hooks(self):
        h = div(
            button(
                "x",
                hx_get="/api",
                hx_target="#m",
                hx_swap="outerHTML",
                hx_on_click="console.log(1)",
                x_on_click="f()",
                ws_send=True,
                data_channel_id="R1",
            )
        ).__render__(pretty=False)
        for token in (
            "hx-get",
            "hx-target",
            "hx-swap",
            "hx-on:click",
            "@click",
            "ws-send",
            "data-channel-id",
        ):
            self.assertIn(token, h)

    def test_static_js_assets_present(self):
        root = Path(__file__).resolve().parents[2]
        for rel in (
            "src/ux_dom/scripts/x_element.js",
        ):
            p = root / rel
            self.assertTrue(p.exists() and p.stat().st_size > 50, rel)


class TestHttpChaos(unittest.TestCase):
    def test_stream_concurrent(self):
        app = FastAPI()

        @app.get("/s")
        def s():
            return StreamingResponse(div(*[Card(n=i) for i in range(20)], id="d"))

        client = TestClient(app)

        def hit(_):
            r = client.get("/s")
            return r.status_code == 200 and "c0" in r.text

        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            res = list(ex.map(hit, range(150)))
        self.assertTrue(all(res))


if __name__ == "__main__":
    unittest.main()
