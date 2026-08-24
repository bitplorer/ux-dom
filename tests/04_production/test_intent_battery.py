"""End-to-end intent checks: scaffolded apps behave as product docs claim."""
from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import random
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from ux_dom import Component, Document, Fragment, ReactiveComponent, MergeClassAttribute
from ux_dom.dom import div, span, button, attr, raw
from ux_dom.dom.src.dom_tag import get_current
from ux_dom.dom.src.ext import Tags, StyleTags
from ux_dom.dom.src.parse_html import tokenize_html
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.htmx import Htmx
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl, NullControl
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.response.starlette import StreamingResponse
from ux_dom.web_io import HtmxEvents, WebSocketAdapter, WebSocketEvents


class Card(Component):
    def render(self, title="Hi", n=0):
        return div(
            span(title, id=f"title-{n}"),
            button("Go", id=f"btn-{n}", hx_get="/x"),
            id=f"card-{n}",
            className="card",
        )


class Multi(Component):
    def render(self, n=0):
        return [div(f"A{n}", id=f"A{n}"), span(f"B{n}", id=f"B{n}")]


class RoutedHome(Component):
    """Mirrors real apps: routes include get/add that must not shadow DOM API."""

    routes = ["get", "add"]

    def render(self):
        return div(span("home", id="h"), id="home")

    @classmethod
    def get(cls):
        return cls()

    @classmethod
    def add(cls):
        return cls()


class CartCounter(Component):
    routes = ["get", "add", "clear"]

    def render(self, n=0):
        return div(f"cart={n}", id="cart")

    @classmethod
    def get(cls):
        return cls(n=0)

    @classmethod
    def add(cls):
        return cls(n=1)

    @classmethod
    def clear(cls):
        return cls(n=0)


class TestIntentContracts(unittest.TestCase):
    def test_bool_matches_get_eq_hash(self):
        self.assertTrue(bool(div()) and bool(Card()))
        c = Card(n=1)
        child = c.get(id="title-1")[0]
        self.assertTrue(c.matches(Card) and c.matches(div))
        self.assertFalse(c.matches(span) or c.matches(child))
        self.assertEqual(c.get(child), [child])
        self.assertIn(child, c)
        self.assertTrue(c == c._entry and c is not c._entry)
        self.assertNotEqual(hash(c), hash(c._entry))
        self.assertNotIn(c._entry, {c})

    def test_route_classmethods_do_not_shadow_dom_api(self):
        h = RoutedHome.get()
        self.assertEqual(h.get(id="h")[0].attributes.get("id"), "h")
        self.assertIn(span, h)
        # classmethod routes still work
        self.assertIsInstance(RoutedHome.add(), RoutedHome)
        cart = CartCounter.get()
        self.assertIn("cart=0", cart.__render__(pretty=False))
        self.assertTrue(cart.get(id="cart"))
        self.assertIn("cart=1", CartCounter.add().__render__(pretty=False))

    def test_build_vs_serialize_and_sync_async(self):
        enters = []

        class T(div):
            def __enter__(self):
                enters.append("e")
                return super().__enter__()

            def __exit__(self, *a):
                enters.append("x")
                return super().__exit__(*a)

        with T(id="p") as n:
            span("s")
        self.assertEqual(enters, ["e", "x"])
        n.__render__(pretty=False)
        n.__render__(pretty=False)
        self.assertEqual(enters, ["e", "x"])

        el = div(Card(n=4), span("z"))
        sync = el.__render__(pretty=False)

        async def coll(e):
            return "".join([t async for t in e.__async_render__(pretty=False)])

        self.assertEqual(asyncio.run(coll(el)), sync)

    def test_dialect_escape_idempotent_cycle(self):
        self.assertEqual(Tags.clean_attribute("hx_get"), "hx-get")
        self.assertTrue(Tags.clean_attribute("x_on_click").startswith("@"))
        self.assertFalse(StyleTags.clean_attribute("x_on_click").startswith("@"))
        h = div("<b>x</b>").__render__(pretty=False)
        self.assertIn("&" + "lt;b&" + "gt;", h)
        raw_html = div(raw("<b>x</b>")).__render__(pretty=False)
        self.assertIn("<b>x</b>", raw_html)
        el = div("body")
        el["open_tag"] = "<!--O-->"
        a = el.__render__(pretty=False)
        self.assertEqual(a, el.__render__(pretty=False))
        self.assertTrue(a.startswith("<!--O-->"))
        x, y = div(id="a"), div(id="b")
        x.add(y)
        y.add(x)
        out = x.__render__(pretty=False)
        self.assertIn("cycle", out)
        self.assertLess(len(out), 500)

    def test_htmx_events_method(self):
        h = HtmxEvents()
        self.assertTrue(callable(h.get_events))
        self.assertEqual(h.get_events("hx-get"), {})


class TestChaos(unittest.TestCase):
    def test_concurrent_cards(self):
        def work(i):
            with div(id=f"w{i}") as r:
                for j in range(8):
                    Card(title=f"{i}-{j}", n=i * 100 + j)
            h = r.__render__(pretty=False)
            self.assertIn(f'id="w{i}"', h)
            self.assertEqual(len(r.get(Card)), 8)
            return True

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            self.assertTrue(all(ex.map(work, range(30))))

    def test_exception_stack_and_uniqueid(self):
        async def storm(i):
            try:
                async with div(id=f"e{i}"):
                    span("x")
                    if i % 2 == 0:
                        raise RuntimeError("x")
            except RuntimeError:
                pass
            try:
                get_current()
                return False
            except ValueError:
                return True

        async def run():
            return await asyncio.gather(*[storm(i) for i in range(50)])

        self.assertTrue(all(asyncio.run(run())))
        bag = []
        lock = threading.Lock()

        def gen(_):
            local = [uniqueid() for _ in range(200)] + [
                next(uniqueid) for _ in range(50)
            ]
            with lock:
                bag.extend(local)

        with concurrent.futures.ThreadPoolExecutor(10) as ex:
            list(ex.map(gen, range(10)))
        self.assertEqual(len(bag), len(set(bag)))

    def test_streaming_load(self):
        app = FastAPI(default_response_class=HTMLResponse)
        app.add_middleware(HtmxMiddleware)

        @app.get("/s")
        def s():
            return StreamingResponse(div(*[Card(n=i) for i in range(15)], id="deck"))

        client = TestClient(app)

        def sh(_):
            r = client.get("/s")
            return r.status_code == 200 and "card" in r.text

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            self.assertTrue(all(ex.map(sh, range(40))))


class TestStandaloneShopApp(unittest.TestCase):
    def test_shop_app_routes_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            rootp = Path(td)
            pkg = rootp / "shop"
            for sub in [
                "app",
                "app/products",
                "app/products/[id]",
                "app/api.v1",
                "app/cart",
                "app/_private",
            ]:
                (pkg / sub).mkdir(parents=True, exist_ok=True)
                (pkg / sub / "__init__.py").write_text("")
            (pkg / "__init__.py").write_text("")
            (pkg / "app" / "home.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div, span, button
                    __all__ = ["Home"]
                    class Home(Component):
                        routes = ["get"]
                        def render(self):
                            return div(span("Welcome", id="welcome"), id="home")
                        @classmethod
                        def get(cls):
                            return cls()
                    """))
            (pkg / "app" / "products" / "list.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div, span
                    __all__ = ["ProductList"]
                    class ProductList(Component):
                        routes = ["get"]
                        def render(self):
                            return div(span("Products", id="plist-title"), id="plist")
                        @classmethod
                        def get(cls):
                            return cls()
                    """))
            (pkg / "app" / "products" / "[id]" / "route.py").write_text(
                "def get(id: str):\n"
                "    from ux_dom.dom import div, span\n"
                "    return div(span(f'product-{id}'), id='pdetail')\n"
            )
            (pkg / "app" / "cart" / "counter.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div, button
                    __all__ = ["CartCounter"]
                    class CartCounter(Component):
                        routes = ["get", "add", "clear"]
                        def render(self, n=0):
                            return div(f"cart={n}", id="cart")
                        @classmethod
                        def get(cls):
                            return cls(n=0)
                        @classmethod
                        def add(cls):
                            return cls(n=1)
                        @classmethod
                        def clear(cls):
                            return cls(n=0)
                    """))
            (pkg / "app" / "api.v1" / "route.py").write_text(
                "def get():\n"
                "    from ux_dom.dom import div\n"
                "    return div('api-v1', id='api')\n"
            )
            (pkg / "app" / "_private" / "secret.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div
                    __all__ = ["Secret"]
                    class Secret(Component):
                        routes = ["get"]
                        def render(self):
                            return div("SECRET")
                        @classmethod
                        def get(cls):
                            return cls()
                    """))
            sys.path.insert(0, str(rootp))
            try:
                api = (
                    App(debug=False)
                    .use(
                        DirectoryRouting(
                            package_dir=pkg, base_directory="app", prefix="/shop"
                        )
                    )
                    .use(HtmxControl(middleware=True))
                    .build(asgi=FastAPI(title="Shop", debug=False, default_response_class=HTMLResponse))
                )
                client = TestClient(api)
                paths = list(api.openapi()["paths"])
                self.assertFalse(any("Secret" in p for p in paths))

                r = client.get("/shop/home")
                self.assertEqual(r.status_code, 200)
                self.assertIn("Welcome", r.text)

                r = client.get("/shop/products/sku99/")
                self.assertEqual(r.status_code, 200)
                self.assertIn("product-sku99", r.text)

                r = client.get("/shop/api.v1/")
                self.assertEqual(r.status_code, 200)
                self.assertIn("api-v1", r.text)

                hit_paths = [
                    "/shop/home",
                    "/shop/products/sku99/",
                    "/shop/api.v1/",
                    "/shop/products/p1/",
                ]

                def hit(_):
                    p = random.choice(hit_paths)
                    hdr = {"HX-Request": "true"} if random.random() > 0.1 else {}
                    return client.get(p, headers=hdr).status_code

                with concurrent.futures.ThreadPoolExecutor(16) as ex:
                    codes = list(ex.map(hit, range(150)))
                self.assertTrue(all(c == 200 for c in codes), set(codes))
            finally:
                sys.path.remove(str(rootp))


class TestEdges(unittest.TestCase):
    def test_empty_nested_mixed_deep_copy(self):
        class E1(Component):
            def render(self):
                return ""

        class E2(Component):
            def render(self):
                return []

        self.assertEqual(E1().__render__(pretty=False), "")
        self.assertEqual(E2().__render__(pretty=False), "")
        doc = Document(ensure_csrf_token=False)
        self.assertIn("nest", doc(doc(div("nest"))).__render__())

        async def sia():
            async with div(id="o") as o:
                with span(id="i"):
                    button("x")
            return o.__render__(pretty=False)

        h = asyncio.run(sia())
        self.assertIn('id="o"', h)
        self.assertIn('id="i"', h)

        node = div("leaf", id="leaf")
        for i in range(25):
            node = div(node, id=f"d{i}")
        a = node.__render__(pretty=False)
        b = "".join(node._walk_render_tokens(0, "  ", False, False))
        self.assertEqual(a, b)

        root = div(Card(n=7), span("s"))
        self.assertEqual(
            root.__render__(pretty=False),
            copy.deepcopy(root).__render__(pretty=False),
        )

    def test_attr_bool_parse_merge_ws(self):
        child = div()
        child["data-x"] = ""
        self.assertTrue(div(child).get(div, data_x=None))
        h = div(hidden=True, disabled=False, open=None).__render__(pretty=False)
        self.assertIn("hidden", h)
        self.assertNotIn("disabled", h)
        self.assertIn("t", str(tokenize_html("<div><p>t</p></div>")))
        with MergeClassAttribute() as m:
            attr(className="one")
            attr(className="two")
            div("x", id="m")
        mh = m.__render__(pretty=False)
        self.assertIn("one", mh)
        self.assertIn("two", mh)
        a = div(span("x", id="x"))
        x = a.get(id="x")[0]
        self.assertNotIn(x, div())

        events = WebSocketEvents()

        class Box:
            def __init__(self):
                self.n = 0

        adapter = WebSocketAdapter(Box, events)

        class Fake:
            pass

        async def ws():
            socks = [Fake() for _ in range(20)]
            insts = await asyncio.gather(*[adapter.ensure_instance(s) for s in socks])
            for i, inst in enumerate(insts):
                inst.n = i
            self.assertTrue(
                all(adapter._instance_for(socks[i]).n == i for i in range(20))
            )
            for s in socks:
                adapter.release_instance(s)
            self.assertEqual(len(adapter._instances), 0)

        asyncio.run(ws())

    def test_htmx_decorator_and_null_control(self):
        class API:
            def __init__(self):
                self.routes = []

            def _r(self, m):
                def path(p):
                    def deco(fn):
                        self.routes.append((m, p))
                        return fn

                    return deco

                return path

            def get(self, p):
                return self._r("GET")(p)

            def post(self, p):
                return self._r("POST")(p)

            put = patch = delete = post

        api = API()
        h = Htmx(api, prefix="/act")

        @h.get
        def ping():
            pass

        @h.post
        def save():
            pass

        self.assertIn(("GET", "/act/ping"), api.routes)
        self.assertIn(("POST", "/act/save"), api.routes)
        self.assertIsNotNone(NullControl())


if __name__ == "__main__":
    unittest.main()
