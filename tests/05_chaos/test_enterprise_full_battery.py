"""Enterprise battery: silent bugs, load, stress, pentest, regression.

Critical / medium / minor checks across core, security, concurrency, and
response surfaces. Complements the modular suites under tests/01–06.
"""
from __future__ import annotations

import asyncio
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ux_dom import Component, Document, Fragment, ReactiveComponent
from ux_dom.dom import a, div, h1, p, span
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.plugins.control import NullControl
from ux_dom.plugins.csp import build_csp_header, generate_nonce
from ux_dom.response import HTMLResponse, StreamingResponse


@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(span(str(count)), id="c")

    def inc(self):
        self.count += 1


@dataclass(eq=False)
class Boom(ReactiveComponent):
    n: int = 0

    def render(self, n=0):
        if n >= 99:
            raise RuntimeError("boom")
        return div(str(n), id="boom")


@dataclass(eq=False)
class Multi(ReactiveComponent):
    n: int = 0

    def render(self, n=0):
        return [span(str(n), id="a"), span(str(n + 1), id="b")]


class TestCriticalReactiveDesync(unittest.TestCase):
    def test_failed_render_rolls_back_field_state(self):
        """Failed re-render must not leave field values ahead of the DOM tree."""
        b = Boom(n=1)
        self.assertIn("1", b.__render__(pretty=False))
        b.n = 99
        with self.assertRaises(RuntimeError):
            b.__render__(pretty=False)
        self.assertEqual(b.n, 1)
        html = b.__render__(pretty=False)
        self.assertIn("1", html)
        self.assertNotIn("99", html)

    def test_after_fail_can_advance_again(self):
        b = Boom(n=0)
        b.n = 99
        with self.assertRaises(RuntimeError):
            str(b)
        b.n = 5
        self.assertIn("5", str(b))
        self.assertEqual(b.n, 5)

    def test_increment_path(self):
        c = Counter(count=0)
        for _ in range(50):
            c.inc()
        self.assertEqual(c.count, 50)
        self.assertIn("50", c.__render__(pretty=False))


class TestCriticalXSS(unittest.TestCase):
    PAYLOADS = [
        "<script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        "<svg onload=alert(1)>",
        "javascript:alert(1)",
    ]

    def test_component_escapes_text(self):
        class Box(Component):
            def render(self, *a, **k):
                return div(self.attributes.get("t", ""))

        for payload in self.PAYLOADS:
            html = Box(t=payload).__render__(pretty=False)
            self.assertNotIn("<script>", html.lower())

    def test_defhtml_escape_strips_handlers(self):
        for payload in self.PAYLOADS:
            nodes = defHTML(f"<div>{payload}</div>", escape=True)
            html = "".join(n.__render__(pretty=False) for n in nodes)
            self.assertNotRegex(html, r"(?i)<script[\s>]")
            self.assertNotRegex(html, r"(?i)\son\w+\s*=")

    def test_reactive_xss_field(self):
        @dataclass(eq=False)
        class X(ReactiveComponent):
            text: str = ""

            def render(self, text=""):
                return div(text)

        x = X(text="<script>x</script>")
        html = x.__render__(pretty=False)
        self.assertNotIn("<script>x</script>", html)


class TestCriticalFragment(unittest.TestCase):
    def test_unique_id_only_on_first_child(self):
        f = Fragment(span("a"), span("b"), id="once")
        html = f.__render__(pretty=False)
        self.assertEqual(html.count('id="once"'), 1)

    def test_bad_x_data_no_crash(self):
        f = Fragment(
            div(x_data='{"a":1}'),
            div(x_data="NOT_JSON"),
            x_data='{"b":2}',
        )
        self.assertIsInstance(str(f), str)


class TestLoadConcurrency(unittest.TestCase):
    def test_uniqueid_5000(self):
        ids = [next(uniqueid) for _ in range(5000)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_concurrent_component_render(self):
        class C(Component):
            def render(self, *a, **k):
                return div(*[span(str(i)) for i in range(10)])

        with ThreadPoolExecutor(32) as ex:
            outs = list(ex.map(lambda _: C().__render__(pretty=False), range(300)))
        self.assertTrue(all("span" in o for o in outs))
        self.assertEqual(len(set(outs)), 1)

    def test_concurrent_reactive_instances(self):
        def work(i):
            c = Counter(count=i)
            c.inc()
            return c.count, c.__render__(pretty=False)

        with ThreadPoolExecutor(16) as ex:
            results = list(ex.map(work, range(100)))
        for i, (n, html) in enumerate(results):
            self.assertEqual(n, i + 1)
            self.assertIn(str(i + 1), html)

    def test_document_many_pages(self):
        doc = Document(head=[], body=[], ensure_csrf_token=False)
        for i in range(200):
            html = str(doc(h1(f"page-{i}")))
            self.assertIn(f"page-{i}", html)


class TestMediumMultiRoot(unittest.TestCase):
    def test_multi_root_rerender(self):
        m = Multi(n=1)
        self.assertIs(m._entry, m)
        m.n = 7
        html = m.__render__(pretty=False).replace(" ", "")
        self.assertIn(">7<", html)
        self.assertIn(">8<", html)

    def test_parent_slot_stable(self):
        m = Multi(n=0)
        root = div(m, id="root")
        m.n = 4
        html = root.__render__(pretty=False)
        self.assertIn('id="root"', html)
        self.assertIs(m.parent, root)


class TestPentestSurfaces(unittest.TestCase):
    def test_html_response_escapes(self):
        r = HTMLResponse(div("<script>z</script>"))
        body = r.body.decode() if isinstance(r.body, (bytes, bytearray)) else str(r.body)
        self.assertNotIn("<script>z</script>", body)

    def test_streaming_response_async_consumable(self):
        async def consume():
            sr = StreamingResponse(div(p("stream-ok")))
            chunks = []
            async for c in sr.body_iterator:
                chunks.append(
                    c if isinstance(c, (bytes, bytearray)) else str(c).encode()
                )
            return b"".join(chunks)

        data = asyncio.run(consume())
        self.assertIn(b"stream-ok", data)

    def test_csp_header_builds(self):
        nonce = generate_nonce()
        header = build_csp_header(nonce)
        self.assertIsInstance(header, str)
        self.assertIn(nonce, header)
        self.assertIn("script-src", header)

    def test_null_control_artifacts(self):
        n = NullControl()
        self.assertEqual(tuple(n.document_head() or ()), ())
        self.assertEqual(tuple(n.document_body() or ()), ())
        self.assertEqual(n.wire(x=1), {})

    def test_text_content_escaped_in_anchor(self):
        el = a("click me <script>", href="https://example.com")
        html = el.__render__(pretty=False)
        self.assertNotIn("<script>", html)


class TestMinorCoverage(unittest.TestCase):
    def test_ui_tokens_cn(self):
        from ux_dom.ui.tokens import cn

        self.assertEqual(cn("a", None, "b", False, "c"), "a b c")

    def test_fragment_empty(self):
        self.assertIsInstance(str(Fragment()), str)

    def test_component_not_implemented_render(self):
        class Bad(Component):
            pass

        with self.assertRaises(NotImplementedError):
            Bad()


class TestStressLoops(unittest.TestCase):
    def test_1000_reactive_updates(self):
        c = Counter(count=0)
        for i in range(1, 1001):
            c.count = i
            if i % 100 == 0:
                self.assertIn(str(i), c.__render__(pretty=False))
        self.assertEqual(c.count, 1000)

    def test_threaded_document(self):
        doc = Document(head=[], body=[], ensure_csrf_token=False)
        errors: list[BaseException] = []

        def worker(k):
            try:
                html = str(doc(div(f"t-{k}")))
                assert f"t-{k}" in html
            except BaseException as e:  # noqa: BLE001 — collect for join
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
