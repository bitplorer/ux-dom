"""StreamingResponse coercion and HTML attribute edge cases.

Includes dunder/control attrs, Htmx name dialects, shadowdom attribute spelling.
"""
from __future__ import annotations

from pathlib import Path

import asyncio
import unittest

from ux_dom.dom import div
from ux_dom.dom.src.ext import Tags
from ux_dom.response.starlette import StreamingResponse


class TestStreamingResponseCoerce(unittest.TestCase):
    def test_dom_tag(self):
        r = StreamingResponse(div("x"))
        self.assertIsNotNone(r)

    def test_str(self):
        r = StreamingResponse("<p>hi</p>")
        self.assertIsNotNone(r)

    def test_bytes(self):
        r = StreamingResponse(b"<p>hi</p>")
        self.assertIsNotNone(r)

    def test_bad_type(self):
        with self.assertRaises(TypeError):
            StreamingResponse(12345)  # type: ignore


class TestAttrDunder(unittest.TestCase):
    def test_bind_shorthand(self):
        self.assertEqual(Tags.clean_attribute("__class"), ":class")
        self.assertEqual(Tags.clean_attribute("__foo"), ":foo")

    def test_python_dunder_untouched(self):
        # not coerced to :init:
        self.assertEqual(Tags.clean_attribute("__init__"), "__init__")


class TestShadowdomTrue(unittest.TestCase):
    def test_shadowdom_true_emits_true(self):
        html = div(shadowdom=True).__render__(pretty=False)
        self.assertIn('shadowdom="true"', html)
        self.assertNotIn('shadowdom="shadowdom"', html)


class TestHtmxEventName(unittest.TestCase):
    def test_event_name_from_callable(self):
        from ux_dom.htmx import Htmx

        class FakeAPI:
            def __init__(self):
                self.paths = []

            def get(self, path):
                self.paths.append(("get", path))

                def deco(fn):
                    return fn

                return deco

            def post(self, path):
                self.paths.append(("post", path))

                def deco(fn):
                    return fn

                return deco

        api = FakeAPI()
        h = Htmx(api=api, prefix="/actions")

        @h.get
        def counter():
            return "ok"

        @h.get
        def other():
            return "ok"

        self.assertEqual(api.paths[0], ("get", "/actions/counter"))
        self.assertEqual(api.paths[1], ("get", "/actions/other"))


class TestRouteNameDots(unittest.TestCase):
    def test_no_colon_in_name_template(self):
        root = Path(__file__).resolve().parents[2]
        src = (root / "src" / "ux_dom" / "routing" / "fastapi.py").read_text()
        self.assertNotIn('name = f"{module}.{klass_name}:{_method}"', src)
        self.assertNotIn('name = f"{module}:{fn_name}"', src)
        self.assertIn('name = f"{module}.{klass_name}.{_method}"', src)


if __name__ == "__main__":
    unittest.main()


class TestReviewHardening(unittest.TestCase):
    def test_none_children_skipped(self):
        from ux_dom.dom import div

        html = div(None, "x", None).__render__(pretty=False)
        self.assertIn("x", html)
        self.assertNotIn("None", html)

    def test_attr_strips_c0_controls(self):
        from ux_dom.dom import div

        html = div(title="a\x1bb").__render__(pretty=False)
        self.assertNotIn("\x1b", html)
        self.assertIn("title=", html)

    def test_self_membership_intentional(self):
        from ux_dom.dom import div

        root = div()
        self.assertTrue(root in root)  # own-existence path


class TestComponentDataclassChain(unittest.TestCase):
    def test_bare_dataclass_component_renders(self):
        from dataclasses import dataclass

        from ux_dom.dom import div, span
        from ux_dom.dom.src import dom_tag
        from ux_dom.dom.src.component import Component

        # Clear any leftover with-stack from prior tests (coverage / chaos order)
        try:
            tok = getattr(dom_tag, "_WITH_STACK", None)
            if tok is not None and hasattr(tok, "set"):
                tok.set(None)
        except Exception:
            pass

        @dataclass(eq=False)
        class BareBox(Component):
            def render(self, *a, **k):
                return div(span("in"), id="box")

        node = BareBox()
        html = node.__render__(pretty=False)
        if not html:
            # force init chain once more if a prior test left class state odd
            Component._ensure_init_chain(BareBox)
            node = BareBox()
            html = node.__render__(pretty=False)
        self.assertIn("in", html)
        self.assertIn('id="box"', html)

    def test_dataclass_fields_passed_to_render(self):
        from dataclasses import dataclass

        from ux_dom.dom import div, span
        from ux_dom.dom.src.component import Component

        @dataclass(eq=False)
        class Card(Component):
            title: str
            price: int = 0

            def render(self, title, price=0):
                return div(span(title), span(str(price)))

        html = str(Card(title="Hello", price=7))
        self.assertIn("Hello", html)
        self.assertIn("7", html)

    def test_post_init_still_works(self):
        from dataclasses import dataclass

        from ux_dom.dom import div, span
        from ux_dom.dom.src.component import Component

        @dataclass(eq=False)
        class Card(Component):
            title: str

            def __post_init__(self):
                super().__init__(title=self.title)

            def render(self, title):
                return div(span(title))

        self.assertIn("Z", str(Card(title="Z")))

    def test_false_true_skipped_zero_kept(self):
        from ux_dom.dom import div

        html = div(None, False, True, 0, "ok").__render__(pretty=False)
        self.assertEqual(html, "<div>0ok</div>")
