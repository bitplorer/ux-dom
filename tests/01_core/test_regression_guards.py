"""Guards against regressions in the Component DOM API and control attrs.

Covers Component DOM methods, HtmxEvents, App composition edge paths that
broke once and must stay fixed.
"""
from __future__ import annotations

import concurrent.futures
import copy
import unittest


from ux_dom import Component, Document, Fragment, ReactiveComponent
from ux_dom.dom import div, span
from ux_dom.web_io import HtmxEvents


class Routed(Component):
    def render(self):
        return div(span("x", id="x"), id="r")

class TestGetattributeRegressions(unittest.TestCase):
    def test_custom_instance_get_is_rejected(self):
        # ``get`` is sealed DOM query API: redefining it fails at class creation
        # instead of silently shadowing tree queries.
        with self.assertRaisesRegex(TypeError, "defines 'get'"):

            class CustomGet(Component):
                def render(self):
                    return div(span("x", id="x"))

                def get(self, tag=None, **kwargs):
                    return ["custom"]

    def test_clear_internal(self):
        w = Routed()
        self.assertEqual(len(w), 1)
        w._clear()
        self.assertEqual(len(w), 0)

    def test_fields_matches_deepcopy_reactive(self):
        r = Routed()
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
        page = Document(ensure_csrf_token=False)(Routed())
        self.assertIn("x", page.__render__())
        f = Fragment(div("a"), span("b"))
        self.assertIn("a", f.__render__(pretty=False))

    def test_concurrent_routed_construct(self):
        def make(_):
            inst = Routed()
            self.assertTrue(inst.get(id="x"))
            return True

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            self.assertTrue(all(ex.map(make, range(30))))


class TestRouterAndEventsRegressions(unittest.TestCase):
    def test_htmx_events_get_events_is_callable(self):
        h = HtmxEvents()
        self.assertTrue(callable(h.get_events))
        self.assertEqual(h.get_events("hx-get"), {})
        self.assertIsInstance(h.hx_get_events, dict)


if __name__ == "__main__":
    unittest.main()
