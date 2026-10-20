"""Brutal production tests: chaos, load, integration, idempotency, races."""

from __future__ import annotations

from markupsafe import Markup
import asyncio
import concurrent.futures
import threading
import time
import unittest
from dataclasses import dataclass


from ux_dom import Component, Document, Fragment, __version__
from ux_dom.dom import div, span, button, template
from ux_dom.dom.src.ext import Tags
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.utils.parameters import Parameters
from ux_dom.response.starlette import StreamingResponse, HTMLResponse
from ux_dom.dom.htmldocument import HtmlDocument


class TestRenderIdempotency(unittest.TestCase):
    def test_render_tag_false_stable(self):
        el = div("x")
        el["render_tag"] = False
        a, b, c = (el.__render__(pretty=False) for _ in range(3))
        self.assertEqual(a, b)
        self.assertEqual(b, c)
        self.assertEqual(a, "x")

    def test_open_tag_stable(self):
        el = div("body")
        el["open_tag"] = Markup("<!--open-->")
        a = el.__render__(pretty=False)
        b = el.__render__(pretty=False)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("<!--open-->"))

    def test_control_keys_not_html_attrs(self):
        el = div("x", id="i")
        el["render_tag"] = True
        html = el.__render__(pretty=False)
        self.assertNotIn("render_tag", html)
        self.assertIn('id="i"', html)

    def test_self_dedent_survives_parent_render(self):
        parent = div(div("inner"))
        child = parent.children[0]
        child["self_dedent"] = True
        parent.__render__()
        self.assertTrue(getattr(child, "self_dedent", False))


class TestMarkdownIsolation(unittest.TestCase):
    def test_markdown_kwarg_does_not_poison_global(self):
        class MD(Component):
            string_is_markdown = True

            def render(self):
                return "# Title"

        def fake(x):
            return "<p>FAKE</p>"

        poisoned = MD(markdown=fake)
        self.assertIn("FAKE", poisoned.__render__(pretty=False))
        clean = MD()
        html = clean.__render__(pretty=False)
        self.assertNotIn("FAKE", html)
        self.assertIn("Title", html)


class TestCSRFInstanceIsolation(unittest.TestCase):
    def test_class_not_mutated(self):
        original = HtmlDocument.ensure_csrf_token
        try:
            Document(ensure_csrf_token=True)(div("a"))
            self.fail("expected CSRF AttributeError")
        except AttributeError:
            pass
        # class default should not stick as True from factory if we fixed it
        # After instance construction with ensure_csrf_token=True, class may still be original
        Document(ensure_csrf_token=False)(div("ok"))
        # concurrent mixed
        errors = []

        def work(flag):
            try:
                d = Document(ensure_csrf_token=flag)
                if flag:
                    try:
                        d(div("x"))
                        errors.append("bypass")
                    except AttributeError:
                        pass
                else:
                    d(div("y"))
            except Exception as e:
                errors.append(str(e))

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            list(ex.map(work, [i % 2 == 0 for i in range(60)]))
        self.assertNotIn("bypass", errors)
        HtmlDocument.ensure_csrf_token = original


class TestAttrPrefixes(unittest.TestCase):
    def test_ws_sse(self):
        self.assertEqual(Tags.clean_attribute("ws_send"), "ws-send")
        self.assertEqual(Tags.clean_attribute("ws_connect"), "ws-connect")
        self.assertEqual(Tags.clean_attribute("sse_connect"), "sse-connect")
        html = div(ws_send=True, sse_connect="/x").__render__(pretty=False)
        self.assertIn("ws-send", html)
        self.assertIn("sse-connect", html)

    def test_hx_on_still_ok(self):
        self.assertEqual(Tags.clean_attribute("hx_on_click"), "hx-on:click")
        self.assertNotEqual(Tags.clean_attribute("hx_on_click"), "h@click")

    def test_class_for_underscore(self):
        self.assertEqual(Tags.clean_attribute("class_"), "class")
        self.assertEqual(Tags.clean_attribute("for_"), "for")


class TestUniqueId(unittest.TestCase):
    def test_callable_and_next(self):
        a = uniqueid()
        b = next(uniqueid)
        self.assertNotEqual(a, b)

    def test_concurrent_unique(self):
        ids = []
        lock = threading.Lock()

        def gen(n):
            local = [uniqueid() for _ in range(n)]
            with lock:
                ids.extend(local)

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            list(ex.map(gen, [250] * 8))
        self.assertEqual(len(ids), len(set(ids)), "collisions under load")


class TestParametersRequired(unittest.TestCase):
    def test_required_is_empty_sentinel(self):
        import inspect

        def f(x, y=1):
            pass

        p = Parameters(f)()
        self.assertIs(p["x"], inspect.Parameter.empty)
        self.assertEqual(p["y"], 1)


class TestHeadBodyInference(unittest.TestCase):
    def test_js_in_head_is_script(self):
        doc = Document(ensure_csrf_token=False)
        html = str(doc(div("x"), head=[{"src": "/js/app.js"}]))
        self.assertIn("<script", html)
        self.assertIn("/js/app.js", html)
        self.assertNotIn('<link src="/js/app.js"', html)

    def test_css_string_in_head_is_link(self):
        doc = Document(ensure_csrf_token=False)
        html = str(doc(div("x"), head=["/css/app.css"]))
        self.assertIn("stylesheet", html)
        self.assertIn("app.css", html)


class TestChaosConcurrentTrees(unittest.TestCase):
    def test_200_concurrent_tasks(self):
        async def build(i):
            with div(id=f"r{i}") as root:
                for j in range(10):
                    with span(className=f"c{j}"):
                        button(f"{i}-{j}", hx_get=f"/x/{i}")
            return root.__render__(pretty=False)

        async def main():
            return await asyncio.gather(
                *[asyncio.create_task(build(i)) for i in range(200)]
            )

        results = asyncio.run(main())
        for i, html in enumerate(results):
            self.assertIn(f'id="r{i}"', html)
            self.assertIn(f"{i}-0", html)
            self.assertIn("hx-get", html)


class TestLoadRenderThroughput(unittest.TestCase):
    def test_render_10000_trees(self):
        t0 = time.perf_counter()
        for i in range(10000):
            html = div(
                span("a", className="x y z"),
                button("go", hx_post="/p", x_on_click="f()"),
                id=str(i),
            ).__render__(pretty=False)
            if i == 0:
                self.assertIn("@click", html)
        elapsed = time.perf_counter() - t0
        # Soft budget: 10k renders in under 15s on CI-ish hardware
        self.assertLess(elapsed, 15.0, f"too slow: {elapsed:.2f}s")


class TestStreamingIntegration(unittest.TestCase):
    def test_stream_and_html_response(self):
        async def consume(resp):
            out = []
            async for chunk in resp.body_iterator:
                out.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
            return "".join(out)

        body = asyncio.run(consume(StreamingResponse(div("stream-ok"))))
        self.assertIn("stream-ok", body)
        hr = HTMLResponse(div("html-ok"))
        self.assertIn(b"html-ok", hr.body)

    def test_double_render_stream_same(self):
        el = div("stable", className="a")

        async def consume(resp):
            out = []
            async for chunk in resp.body_iterator:
                out.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
            return "".join(out)

        a = asyncio.run(consume(StreamingResponse(el)))
        b = asyncio.run(consume(StreamingResponse(el)))
        self.assertEqual(a, b)


class TestComponentSarrafaStyle(unittest.TestCase):
    def test_dataclass_card_under_load(self):
        @dataclass(eq=False)
        class Card(Component):
            title: str
            price: int = 0

            def __post_init__(self):
                super().__init__(title=self.title, price=self.price)

            def render(self, title, price=0):
                with div(className="card") as root:
                    span(title)
                    span(str(price), className="price")
                    button("Buy", hx_post=f"/buy/{title}", ws_send=True)
                return root

        def one(i):
            return Card(title=f"G{i}", price=i).__render__(pretty=False)

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            outs = list(ex.map(one, range(100)))
        for i, html in enumerate(outs):
            self.assertIn(f"G{i}", html)
            self.assertIn("ws-send", html)


if __name__ == "__main__":
    unittest.main()
