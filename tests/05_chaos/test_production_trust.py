"""Production-trust battery: concurrent render, CSP, static safety under load."""
from __future__ import annotations

import asyncio
import random
import re
import string
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ux_dom import Document
from ux_dom.dom import (
    button,
    div,
    form,
    h1,
    input_,
    li,
    p,
    script,
    span,
    style,
    ul,
)
from ux_dom.dom.src.component import Component, Fragment, ReactiveComponent
from ux_dom.dom.src.concurrency import tree_lock_for
from ux_dom.dom.src.ext import PlaceholderTag, StyleTags, Tags
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.plugins.control import HtmxControl, NullControl
from ux_dom.plugins.csp import build_csp_header, generate_nonce
from ux_dom.response import HTMLResponse, StreamingResponse


@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(span(str(count)), id="c")


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


class TestTagsSerializeTrust(unittest.TestCase):
    def test_attr_dialects(self):
        self.assertEqual(Tags.clean_attribute("hx_on_click"), "hx-on:click")
        self.assertEqual(Tags.clean_attribute("x_on_click"), "@click")
        self.assertEqual(Tags.clean_attribute("__class"), ":class")
        self.assertEqual(Tags.clean_attribute("class_"), "class")
        self.assertEqual(StyleTags.clean_attribute("background_color"), "background-color")
        self.assertFalse(StyleTags.clean_attribute("x_on_click").startswith("@"))

    def test_walk_equals_render_random_trees(self):
        rng = random.Random(42)
        for i in range(40):
            kids = [
                span(rng.choice(string.ascii_letters) * rng.randint(1, 4), id=f"k{j}")
                for j in range(rng.randint(0, 6))
            ]
            el = div(
                *kids,
                id=f"r{i}",
                data_x=str(i),
                cls="a  b\nc" if i % 2 == 0 else "x",
            )
            walk = "".join(el._walk_render_tokens(0, "  ", False, False))
            rend = el.__render__(pretty=False)
            self.assertEqual(walk, rend, msg=f"tree {i}")

    def test_pretty_stream_equals_render(self):
        el = div(div(span("a"), span("b")), p("c"))
        a = el.__render__(pretty=True)
        b = "".join(el._walk_render_tokens(0, "  ", True, False))
        self.assertEqual(a, b)

    def test_async_equals_sync(self):
        el = div(span("y"), p("z"), id="pair")

        async def ar():
            return "".join([t async for t in el.__async_render__(pretty=False)])

        self.assertEqual(asyncio.run(ar()), el.__render__(pretty=False))

    def test_boolean_and_json_attrs(self):
        h = div(hidden=True, disabled=False, open=None, x_data={"a": 1}).__render__(
            pretty=False
        )
        self.assertIn("hidden", h)
        self.assertNotIn("disabled", h)
        self.assertIn("x-data", h)

    def test_htmx_alpine_attrs(self):
        h = button(
            "Add", hx_post="/cart", hx_target="#c", x_on_click="n++"
        ).__render__(pretty=False)
        self.assertIn('hx-post="/cart"', h)
        self.assertIn("hx-target", h)

    def test_placeholder_and_cycle_guard(self):
        html = (div("a") & span("b")).__render__(pretty=False)
        self.assertIn("a", html)
        self.assertIn("b", html)
        a = div(id="a")
        b = div(id="b")
        a.add(b)
        b.children.append(a)
        a.parent = b
        # must not stack-overflow
        out = a.__render__(pretty=False)
        self.assertIsInstance(out, str)

    def test_deep_nest(self):
        node = span("leaf")
        for i in range(35):
            node = div(node, id=f"n{i}")
        html = node.__render__(pretty=False)
        self.assertIn("leaf", html)
        self.assertIn("n0", html)


class TestReactiveTrust(unittest.TestCase):
    def test_fail_closed_rolls_back_field(self):
        b = Boom(n=1)
        b.n = 99
        with self.assertRaises(RuntimeError):
            b.__render__(pretty=False)
        self.assertEqual(b.n, 1)
        self.assertIn("1", b.__render__(pretty=False))

    def test_multi_root_and_updates(self):
        m = Multi(n=1)
        self.assertIs(m._entry, m)
        m.n = 7
        html = m.__render__(pretty=False).replace(" ", "")
        self.assertIn(">7<", html)
        self.assertIn(">8<", html)

    def test_list_reassign(self):
        @dataclass(eq=False)
        class LB(ReactiveComponent):
            items: list = field(default_factory=list)

            def render(self, items=None):
                items = items if items is not None else []
                return div(*[span(str(x)) for x in items], id="lb")

        b = LB(items=[1, 2])
        self.assertEqual(b.__render__(pretty=False).count("<span>"), 2)
        b.items = [1, 2, 3, 4]
        self.assertEqual(b.__render__(pretty=False).count("<span>"), 4)


class TestConcurrencyTrust(unittest.TestCase):
    def test_independent_roots_different_locks(self):
        a, b = div("a"), div("b")
        self.assertIsNot(tree_lock_for(a), tree_lock_for(b))

    def test_atomic_replace_under_load(self):
        root = div(span("0", id="v"), id="box")

        def mut():
            for i in range(300):
                root.replace_children(span(str(i), id="v"))

        def ren():
            for _ in range(300):
                html = root.__render__(pretty=False)
                self.assertEqual(html.count('id="v"'), 1)

        with ThreadPoolExecutor(6) as ex:
            futs = [ex.submit(mut)] + [ex.submit(ren) for _ in range(4)]
            for f in futs:
                f.result()

    def test_parallel_independent_builds(self):
        def work(i):
            with div(id=f"t{i}") as r:
                for j in range(15):
                    span(f"{i}-{j}")
            return r.__render__(pretty=False)

        with ThreadPoolExecutor(20) as ex:
            outs = list(ex.map(work, range(80)))
        for i, h in enumerate(outs):
            self.assertIn(f"t{i}", h)


class TestSecurityTrust(unittest.TestCase):
    PAYLOADS = [
        "<script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        "<svg onload=alert(1)>",
    ]

    def test_defhtml_strips(self):
        for p in self.PAYLOADS:
            nodes = defHTML(f"<div>{p}</div>", escape=True)
            html = "".join(n.__render__(pretty=False) for n in nodes)
            self.assertIsNone(re.search(r"(?i)<script[\s>]", html))
            self.assertIsNone(re.search(r"(?i)\son\w+\s*=", html))

    def test_component_escapes_text(self):
        class Box(Component):
            def render(self, *a, **k):
                return div(self.attributes.get("t", ""))

        html = Box(t="<script>x</script>").__render__(pretty=False)
        self.assertNotIn("<script>x</script>", html)

    def test_csp_header(self):
        n = generate_nonce()
        h = build_csp_header(n)
        self.assertIn(n, h)
        self.assertIn("script-src", h)


class TestDocumentResponseTrust(unittest.TestCase):
    def test_document_rich(self):
        d = Document(head=[], body=[], ensure_csrf_token=False)
        html = str(
            d(
                div(
                    h1("Title"),
                    ul(*[li(f"item {i}") for i in range(8)]),
                    form(input_(name="q"), button("go"), method="get"),
                )
            )
        )
        self.assertIn("Title", html)
        self.assertIn("item 7", html)

    def test_html_and_stream(self):
        r = HTMLResponse(div(p("hi")))
        body = r.body.decode() if isinstance(r.body, (bytes, bytearray)) else str(r.body)
        self.assertIn("hi", body)

        async def consume():
            sr = StreamingResponse(div(p("stream-ok")))
            chunks = []
            async for c in sr.body_iterator:
                chunks.append(
                    c if isinstance(c, (bytes, bytearray)) else str(c).encode()
                )
            return b"".join(chunks)

        self.assertIn(b"stream-ok", asyncio.run(consume()))


class TestFragmentControlUidTrust(unittest.TestCase):
    def test_fragment_unique_id(self):
        f = Fragment(span("a"), span("b"), id="once")
        self.assertEqual(f.__render__(pretty=False).count('id="once"'), 1)

    def test_htmx_control_sse(self):
        body = "".join(str(x) for x in HtmxControl(version="2.0.4", sse=True).document_body())
        self.assertIn("htmx.org", body)
        self.assertIn("htmx-ext-sse", body)
        self.assertEqual(NullControl().wire(), {})

    def test_uniqueid_load(self):
        ids = [uniqueid() for _ in range(2000)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_tag_save_roundtrip(self):
        d = Path(tempfile.mkdtemp())
        el = div("save-me", id="s")
        name = el.save(file_name="t", folder_name=None, file_or_dir=d)
        self.assertIn("save-me", (d / name).read_text())

    def test_style_tag(self):
        html = style(".x{color:red}").__render__(pretty=False)
        self.assertTrue("color" in html or "red" in html)


if __name__ == "__main__":
    unittest.main()
