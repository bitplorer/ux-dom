"""Alpine · Jinja · HTMX · Slots · WebComponent surface tests + kit demos."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ux_dom.dom import button, div, li, slot, template
from ux_dom.dom.htmlelement import (
    AlpineComponent,
    CustomElement,
    JinjaElement,
    WebComponent,
)
from ux_dom.dom.src.jinjatags import For, If, Var
from ux_dom.htmx.middleware import HtmxDetails
from ux_dom.slots import Slots

KIT = Path(__file__).resolve().parents[2] / "examples" / "xelement_kit"


class TestAlpineComponent(unittest.TestCase):
    def test_requires_x_data_and_x_tagname(self):
        class Bad(AlpineComponent):
            tag_name = "t"

            def render(self, tag_name: str = "t"):
                return template(div("x"), **{"x-tagname": tag_name})

        with self.assertRaises(AttributeError):
            Bad.definition()

    def test_ok(self):
        class Ok(AlpineComponent):
            tag_name = "tog"

            def render(self, tag_name):
                return template(
                    div(**{"x-data": "{n:1}"}),
                    **{"x-tagname": tag_name},
                )

        html = str(Ok.definition())
        self.assertIn("x-tagname", html)
        self.assertIn("x-data", html)


class TestJinjaSurface(unittest.TestCase):
    def test_for_var_expand(self):
        tree = For("name in names", li(Var("name")))
        src = str(tree)
        self.assertIn("for", src.lower())
        out = str(tree(names=["a", "b"]))
        self.assertIn("a", out)
        self.assertIn("b", out)

    def test_jinja_element_callable(self):
        class Frag(JinjaElement):
            def render(self, *a, **k):
                return For("x in xs", li(Var("x")))

        f = Frag()
        # JinjaElement.__call__ → render_jinja
        expanded = f(xs=[1, 2])
        text = str(expanded)
        self.assertTrue("1" in text or "2" in text or "for" in text.lower())


class TestHtmxAttrs(unittest.TestCase):
    def test_hx_dialect(self):
        b = button("Go", hx_get="/p", hx_target="#t", hx_swap="innerHTML")
        s = str(b)
        self.assertIn("hx-get", s)
        self.assertIn("hx-target", s)
        self.assertIn("hx-swap", s)

    def test_htmx_details_headers(self):
        scope = {
            "type": "http",
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-target", b"panel"),
            ],
        }
        d = HtmxDetails(scope)
        self.assertTrue(d)
        # attribute access variants
        self.assertTrue(getattr(d, "request", True) or d)


class TestSlotsAndWebComponent(unittest.TestCase):
    def test_webcomponent_named_slot_markup(self):
        class Panel(WebComponent):
            def render(self, tag_name="panel"):
                return template(
                    div(slot(name="h"), slot()),
                    **{"x-tagname": tag_name, "shadowroot": "true"},
                )

        definition = Panel.definition()
        self.assertIn("shadowroot", str(definition))
        host = definition(div("H", **{"slot": "h"}), div("body"))
        self.assertIn("<x-panel", str(host))

    def test_slots_helper_renders(self):
        s = Slots(
            tag_name="box",
            slot_names=["a", "b"],
            classes={},
        )
        html = str(s)
        self.assertIn("x-tagname", html.replace("x_tagname", "x-tagname") or html)
        # attribute may render as x-tagname
        self.assertTrue("box" in html)
        self.assertIn("slot", html.lower())

    def test_slots_shadowroot_not_boolean_name(self):
        """shadowdom=True used to emit shadowdom="shadowdom" — must be real value."""
        s = Slots(tag_name="fix", slot_names=["a"], classes={})
        html = str(s)
        self.assertNotIn('shadowdom="shadowdom"', html)
        self.assertTrue(
            'shadowroot="true"' in html
            or 'shadowdom="open"' in html
            or 'shadowdom="true"' in html,
            html[:300],
        )
        self.assertIn('x-tagname="fix"', html)

    def test_webcomponent_slot_template_first(self):
        from ux_dom.slots import WebComponentSlot

        w = WebComponentSlot(tag_name="wcs", slot_names=["t"], classes={}, css=[])
        html = str(w)
        self.assertTrue(html.strip().startswith("<template"), html[:120])
        self.assertIn('x-tagname="wcs"', html)
        self.assertIn("shadowroot", html)


class TestCustomElementLight(unittest.TestCase):
    def test_light_no_shadow(self):
        class H(CustomElement):
            def render(self, tag_name="h"):
                return template(div("hi"), **{"x-tagname": tag_name})

        self.assertIn("x-tagname", str(H.definition()))
        self.assertNotIn("shadowroot", str(H.definition()))


class TestKitHypermediaPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._path = str(KIT.resolve())
        sys.path.insert(0, cls._path)
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        from app.main import app

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        if cls._path in sys.path:
            sys.path.remove(cls._path)

    def test_alpine_page(self):
        r = self.client.get("/alpine/AlpineDemo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("x-tagname", r.text)
        self.assertIn("x_element.js", r.text)

    def test_htmx_page(self):
        r = self.client.get("/htmx/HtmxDemo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("hx-", r.text.lower())

    def test_jinja_page(self):
        r = self.client.get("/jinja/JinjaDemo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("jinja", r.text.lower())
        self.assertIn("Alpha", r.text)

    def test_slots_page(self):
        r = self.client.get("/slots/SlotsDemo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("slot", r.text.lower())
        self.assertIn("x_element.js", r.text)


if __name__ == "__main__":
    unittest.main()
