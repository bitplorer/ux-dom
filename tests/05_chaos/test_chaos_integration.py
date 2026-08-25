"""Chaos + integration tests (concurrency, HTTP, cycles, membership)."""

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
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from ux_dom import Component, Document, ReactiveComponent
from ux_dom.dom import div, span, button
from ux_dom.dom.src.dom_tag import get_current
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.response.starlette import StreamingResponse
from ux_dom.web_io import WebSocketAdapter, WebSocketEvents


class Card(Component):
    def render(self, title="t", n=0):
        return div(
            span(title, id=f"title-{n}"),
            button("x", id=f"btn-{n}"),
            id=f"card-{n}",
        )


class TestContextChaos(unittest.TestCase):
    def test_concurrent_nested_async_with(self):
        async def deep_build(i, depth=4):
            async with div(id=f"root-{i}") as root:

                async def build(d, path):
                    if d == 0:
                        span(f"{i}-{path}")
                        return
                    async with div(id=f"n{i}-{path}"):
                        await build(d - 1, path + "0")
                        await build(d - 1, path + "1")

                await build(depth, "")
            return root.__render__(pretty=False)

        async def run():
            return await asyncio.gather(*[deep_build(i) for i in range(40)])

        outs = asyncio.run(run())
        for i, h in enumerate(outs):
            self.assertIn(f'id="root-{i}"', h)

    def test_threads_and_async_isolation(self):
        errors = []

        def thread_worker(tid):
            for i in range(20):
                with div(id=f"t{tid}-{i}") as r:
                    span(f"{tid}-{i}")
                if f'id="t{tid}-{i}"' not in r.__render__(pretty=False):
                    errors.append((tid, i))

        async def async_worker(aid):
            for i in range(20):
                async with div(id=f"a{aid}-{i}") as r:
                    span(f"a{aid}-{i}")
                if f'id="a{aid}-{i}"' not in r.__render__(pretty=False):
                    errors.append((f"a{aid}", i))

        async def run_asyncs():
            return await asyncio.gather(*[async_worker(a) for a in range(6)])

        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            futs = [ex.submit(thread_worker, t) for t in range(6)]
            asyncio.run(run_asyncs())
            concurrent.futures.wait(futs)
        self.assertEqual(errors, [])

    def test_exception_storm_stack_clean(self):
        async def one(i):
            try:
                async with div(id=f"e{i}"):
                    span("x")
                    if i % 2 == 0:
                        raise ValueError("x")
            except ValueError:
                pass
            try:
                get_current()
                return "dirty"
            except ValueError:
                return "clean"

        async def run():
            return await asyncio.gather(*[one(i) for i in range(60)])

        states = asyncio.run(run())
        self.assertTrue(all(s == "clean" for s in states))


class TestRenderChaos(unittest.TestCase):
    def test_concurrent_render_idempotent(self):
        tree = div(*[div(span(str(i)), id=f"c{i}") for i in range(80)], id="big")
        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            renders = list(ex.map(lambda _: tree.__render__(pretty=False), range(60)))
        self.assertEqual(len(set(renders)), 1)

    def test_concurrent_async_render(self):
        tree = div(*[span(str(i)) for i in range(40)], id="t")

        async def one():
            parts = []
            async for t in tree.__async_render__(pretty=False, chunk_size=3):
                parts.append(t)
            return "".join(parts)

        async def run():
            return await asyncio.gather(*[one() for _ in range(30)])

        streams = asyncio.run(run())
        ref = tree.__render__(pretty=False)
        self.assertTrue(all(s == ref for s in streams))

    def test_cycle_concurrent(self):
        cycles = []
        for i in range(15):
            a, b = div(id=f"a{i}"), div(id=f"b{i}")
            a.add(b)
            b.add(a)
            cycles.append(a)
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            hs = list(ex.map(lambda n: n.__render__(pretty=False), cycles * 4))
        self.assertTrue(all("cycle" in h and len(h) < 500 for h in hs))

    def test_document_nested_render(self):
        doc = Document(ensure_csrf_token=False)
        p1 = doc(div("full", id="f"))
        p2 = doc(p1)
        s = p2.__render__()
        self.assertIn("full", s)

    def test_open_tag_sticky_concurrent(self):
        el = div("body")
        el["open_tag"] = "<!--OPEN-->"
        with concurrent.futures.ThreadPoolExecutor(10) as ex:
            outs = list(ex.map(lambda _: el.__render__(pretty=False), range(50)))
        self.assertEqual(len(set(outs)), 1)
        self.assertTrue(outs[0].startswith("<!--OPEN-->"))


class TestMembershipChaos(unittest.TestCase):
    def test_many_cards(self):
        cards = [Card(title=f"T{i}", n=i) for i in range(60)]
        root = div(*cards, id="deck")
        self.assertEqual(len(root.get(Card)), 60)
        for i, c in enumerate(cards):
            self.assertIn(c, root)
            child = c.get(id=f"title-{i}")[0]
            self.assertIn(child, c)
            self.assertFalse(c.matches(child))


class TestHttpIntegration(unittest.TestCase):
    def test_app_directory_router_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            rootp = Path(td)
            pkg = rootp / "chaosapp"
            (pkg / "app" / "users" / "[id]").mkdir(parents=True)
            for p in [
                pkg,
                pkg / "app",
                pkg / "app" / "users",
                pkg / "app" / "users" / "[id]",
            ]:
                (p / "__init__.py").write_text("")
            (pkg / "app" / "home.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div, button, span
                    __all__ = ["Home", "Counter"]
                    class Home(Component):
                        routes = ["get"]
                        def render(self):
                            return div(span("home"), button("go", hx_get="/x"), id="home")
                        @classmethod
                        def get(cls):
                            return cls()
                    class Counter(Component):
                        routes = ["get", "inc"]
                        def render(self, n=0):
                            return div(f"n={n}", id="ctr")
                        @classmethod
                        def get(cls):
                            return cls(n=0)
                        @classmethod
                        def inc(cls):
                            return cls(n=1)
                    """))
            (pkg / "app" / "users" / "[id]" / "route.py").write_text(
                "def get(id: str):\n"
                "    from ux_dom.dom import div\n"
                "    return div(f'user-{id}')\n"
            )
            sys.path.insert(0, str(rootp))
            try:
                api = (
                    App(debug=False)
                    .use(
                        DirectoryRouting(
                            package_dir=pkg, base_directory="app", prefix="/r"
                        )
                    )
                    .use(HtmxControl(middleware=True))
                    .build(asgi=FastAPI(title="Chaos", debug=False, default_response_class=HTMLResponse))
                )
                client = TestClient(api)
                paths = [
                    "/r/home",
                    "/r/users/u42",
                ]

                def hit(_):
                    return client.get(random.choice(paths)).status_code

                with concurrent.futures.ThreadPoolExecutor(16) as ex:
                    codes = list(ex.map(hit, range(120)))
                self.assertTrue(all(c == 200 for c in codes))
                self.assertIn("home", client.get("/r/home").text)
                self.assertIn("user-u42", client.get("/r/users/u42").text)
            finally:
                sys.path.remove(str(rootp))

    def test_streaming_and_htmx_parallel(self):
        app = FastAPI()
        app.add_middleware(HtmxMiddleware)

        @app.get("/s")
        def s():
            return StreamingResponse(div(*[span(str(i)) for i in range(50)], id="big"))

        @app.get("/h")
        def h(request: Request):
            return {"hx": bool(request.state.htmx)}

        client = TestClient(app)

        def hit(_):
            r = client.get("/s")
            return r.status_code == 200 and "49" in r.text

        def hx(_):
            return client.get("/h", headers={"HX-Request": "true"}).json()["hx"]

        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            self.assertTrue(all(ex.map(hit, range(60))))
            self.assertTrue(all(ex.map(hx, range(60))))


class TestWsAndIds(unittest.TestCase):
    def test_ws_isolation(self):
        events = WebSocketEvents()

        class Box:
            def __init__(self):
                self.n = 0

        adapter = WebSocketAdapter(Box, events)

        class FakeWS:
            pass

        async def run():
            sockets = [FakeWS() for _ in range(30)]
            insts = await asyncio.gather(
                *[adapter.ensure_instance(ws) for ws in sockets]
            )
            for i, inst in enumerate(insts):
                inst.n = i
            again = [adapter._instance_for(ws) for ws in sockets]
            self.assertTrue(all(again[i].n == i for i in range(30)))
            for ws in sockets:
                adapter.release_instance(ws)
            self.assertEqual(len(adapter._instances), 0)

        asyncio.run(run())

    def test_uniqueid_parallel(self):
        ids = []
        lock = threading.Lock()

        def gen(_):
            local = [uniqueid() for _ in range(200)]
            with lock:
                ids.extend(local)

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            list(ex.map(gen, range(12)))
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
