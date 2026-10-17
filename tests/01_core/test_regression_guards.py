"""Guards against regressions in routing, shadow API, and control attrs.

Covers Component route methods, HtmxEvents, App composition edge paths that
broke once and must stay fixed.
"""
from __future__ import annotations

import concurrent.futures
import copy
import unittest


from ux_dom import Component, Document, Fragment, ReactiveComponent
from ux_dom.dom import div, span
from ux_dom.web_io import HtmxEvents


class Widget(Component):
    def render(self):
        return div(span("x", id="x"), id="r")


class CustomGet(Component):
    def render(self):
        return div(span("x", id="x"))

    def get(self, tag=None, **kwargs):
        return ["custom"]


class TestComponentTreeApiRegressions(unittest.TestCase):
    def test_instance_get(self):
        inst = Widget()
        self.assertTrue(inst.get(id="x"))
        self.assertIn(span, inst)

    def test_custom_instance_get_wins(self):
        self.assertEqual(CustomGet().get(id="x"), ["custom"])

    def test_clear(self):
        w = Widget()
        self.assertEqual(len(w), 1)
        w.clear()
        self.assertEqual(len(w), 0)

    def test_fields_matches_deepcopy_reactive(self):
        r = Widget()
        self.assertFalse(r.render_tag)
        self.assertTrue(r.matches(div))
        r2 = copy.deepcopy(r)
        self.assertTrue(r2.get(id="x"))

        class R(ReactiveComponent):
            def render(self, n=0):
                return div(f"n={n}", id="rr")

        x = R(n=1)
        x["data-x"] = "1"
        self.assertIn("rr", x.__render__(pretty=False))

    def test_document_and_fragment(self):
        page = Document(ensure_csrf_token=False)(Widget())
        self.assertIn("x", page.__render__())
        f = Fragment(div("a"), span("b"))
        self.assertIn("a", f.__render__(pretty=False))

    def test_concurrent_construct(self):
        def make(_):
            inst = Widget()
            self.assertTrue(inst.get(id="x"))
            return True

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            self.assertTrue(all(ex.map(make, range(30))))


class TestEventsRegressions(unittest.TestCase):
    def test_htmx_events_get_events_is_callable(self):
        h = HtmxEvents()
        self.assertTrue(callable(h.get_events))
        self.assertEqual(h.get_events("hx-get"), {})
        self.assertIsInstance(h.hx_get_events, dict)


if __name__ == "__main__":
    unittest.main()
