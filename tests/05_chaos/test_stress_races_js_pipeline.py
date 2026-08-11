"""Load/chaos races, deadlock guards, py→js pipeline, concurrent HTTP."""

from __future__ import annotations

import asyncio
import concurrent.futures
import random
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ux_dom import Component
from ux_dom.dom import div, span, button
from ux_dom.dom.src.dom_tag import get_current
from ux_dom.dom.src.ws_rpc import ws_rpc
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.reloader._notify import Notify
from ux_dom.response.starlette import StreamingResponse
from ux_dom.web_io import WebSocketAdapter, WebSocketEvents


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

    def test_notify_publish_subscribe(self):
        async def chaos():
            n = Notify()
            received = []

            async def watcher():
                count = 0
                async for _ in n.watch():
                    count += 1
                    if count >= 3:
                        break
                received.append(count)

            tasks = [asyncio.create_task(watcher()) for _ in range(6)]
            await asyncio.sleep(0.01)
            for _ in range(30):
                await n.notify()
                if all(t.done() for t in tasks):
                    break
                await asyncio.sleep(0.001)
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            return received

        rec = asyncio.run(asyncio.wait_for(chaos(), timeout=8))
        self.assertTrue(all(c >= 3 for c in rec))


class TestWsAndJsPipeline(unittest.TestCase):
    def test_ws_adapter_isolation(self):
        events = WebSocketEvents()

        class Box:
            def __init__(self):
                self.n = 0
                self.hist = []

        adapter = WebSocketAdapter(Box, events)

        class Fake:
            pass

        async def run():
            socks = [Fake() for _ in range(50)]
            await asyncio.gather(*[adapter.ensure_instance(s) for s in socks])

            async def bump(i):
                inst = adapter._instance_for(socks[i])
                for _ in range(10):
                    inst.n += 1
                    inst.hist.append(i)
                return inst.n

            ns = await asyncio.gather(*[bump(i) for i in range(50)])
            self.assertTrue(all(n == 10 for n in ns))
            for i in range(50):
                inst = adapter._instance_for(socks[i])
                self.assertTrue(all(x == i for x in inst.hist))
            for s in socks:
                adapter.release_instance(s)
            self.assertEqual(len(adapter._instances), 0)

        asyncio.run(run())

    def test_ws_rpc_js_asset(self):
        js = ws_rpc().__render__(pretty=False)
        self.assertIn("WebSocket", js)
        self.assertIn("addEventListener", js)
        self.assertNotIn("def ", js)
        self.assertNotIn("self.", js)

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
            "src/ux_dom/reloader/script/reloader.js",
        ):
            p = root / rel
            self.assertTrue(p.exists() and p.stat().st_size > 50, rel)


class TestHttpChaos(unittest.TestCase):
    def test_stream_and_htmx_concurrent(self):
        app = FastAPI()
        app.add_middleware(HtmxMiddleware)

        @app.get("/s")
        def s():
            return StreamingResponse(div(*[Card(n=i) for i in range(20)], id="d"))

        @app.get("/h")
        def h(request: Request):
            return {"hx": bool(request.state.htmx)}

        client = TestClient(app)

        def hit(_):
            if random.random() > 0.5:
                r = client.get("/s")
                return r.status_code == 200 and "c0" in r.text
            r = client.get("/h", headers={"HX-Request": "true"})
            return r.status_code == 200 and r.json().get("hx") is True

        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            res = list(ex.map(hit, range(150)))
        self.assertTrue(all(res))

    def test_directory_router_get_add_load(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "pkg"
            (pkg / "app").mkdir(parents=True)
            for p in [pkg, pkg / "app"]:
                (p / "__init__.py").write_text("")
            (pkg / "app" / "ctr.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div, span
                    __all__ = ["Ctr"]
                    class Ctr(Component):
                        routes = ["get", "add"]
                        def render(self, n=0):
                            return div(span(f"n={n}"), id="ctr")
                        @classmethod
                        def get(cls):
                            return cls(n=0)
                        @classmethod
                        def add(cls):
                            return cls(n=1)
                    """))
            sys.path.insert(0, str(root))
            try:
                api = (
                    App(debug=False)
                    .use(FastAPIHost(title="t", debug=False))
                    .use(
                        DirectoryRouting(
                            package_dir=pkg, base_directory="app", prefix="/x"
                        )
                    )
                    .use(HtmxControl(middleware=True))
                    .build()
                )
                client = TestClient(api)

                def hit(_):
                    p = random.choice(["/x/ctr/Ctr", "/x/ctr/Ctr/add"])
                    r = client.get(p)
                    return r.status_code == 200 and "n=" in r.text

                with concurrent.futures.ThreadPoolExecutor(16) as ex:
                    res = list(ex.map(hit, range(120)))
                self.assertTrue(all(res))
            finally:
                sys.path.remove(str(root))


if __name__ == "__main__":
    unittest.main()
