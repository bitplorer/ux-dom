"""Guards against regressions in routing, shadow API, and control attrs.

Covers Component route methods, HtmxEvents, App composition edge paths that
broke once and must stay fixed.
"""
from __future__ import annotations

import concurrent.futures
import copy
import inspect
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from ux_dom import Component, Document, Fragment, ReactiveComponent
from ux_dom.dom import div, span
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.web_io import HtmxEvents


class Routed(Component):
    routes = ["get", "add", "clear"]

    def render(self):
        return div(span("x", id="x"), id="r")

    @classmethod
    def get(cls):
        return cls()

    @classmethod
    def add(cls):
        return cls()

    @classmethod
    def clear(cls):
        return cls()


class CustomGet(Component):
    def render(self):
        return div(span("x", id="x"))

    def get(self, tag=None, **kwargs):
        return ["custom"]


class TestGetattributeRegressions(unittest.TestCase):
    def test_classmethod_and_instance_get(self):
        inst = Routed.get()
        self.assertTrue(inst.get(id="x"))
        self.assertIsInstance(inspect.getattr_static(Routed, "get"), classmethod)
        self.assertIn(span, inst)

    def test_custom_instance_get_wins(self):
        self.assertEqual(CustomGet().get(id="x"), ["custom"])

    def test_clear_shadow(self):
        w = Routed()
        self.assertEqual(len(w), 1)
        w.clear()
        self.assertEqual(len(w), 0)
        self.assertIsInstance(Routed.clear(), Routed)

    def test_fields_matches_deepcopy_reactive(self):
        r = Routed.get()
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
        page = Document(ensure_csrf_token=False)(Routed.get())
        self.assertIn("x", page.__render__())
        f = Fragment(div("a"), span("b"))
        self.assertIn("a", f.__render__(pretty=False))

    def test_concurrent_routed_construct(self):
        def make(_):
            inst = Routed.get()
            self.assertTrue(inst.get(id="x"))
            return True

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            self.assertTrue(all(ex.map(make, range(30))))


class TestRouterAndEventsRegressions(unittest.TestCase):
    def test_static_and_dynamic_coexist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "pkg"
            (pkg / "app" / "items" / "[id]").mkdir(parents=True)
            for p in [
                pkg,
                pkg / "app",
                pkg / "app" / "items",
                pkg / "app" / "items" / "[id]",
            ]:
                (p / "__init__.py").write_text("")
            (pkg / "app" / "items" / "static.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div
                    __all__ = ["Static"]
                    class Static(Component):
                        routes = ["get"]
                        def render(self):
                            return div("STATIC")
                        @classmethod
                        def get(cls):
                            return cls()
                    """))
            (pkg / "app" / "items" / "[id]" / "route.py").write_text(
                "def get(id: str):\n"
                "    from ux_dom.dom import div\n"
                "    return div(f'DYN-{id}')\n"
            )
            sys.path.insert(0, str(root))
            try:
                api = (
                    App(debug=False)
                    .use(
                        DirectoryRouting(
                            package_dir=pkg, base_directory="app", prefix="/r"
                        )
                    )
                    .use(HtmxControl(middleware=True))
                    .build(asgi=FastAPI(title="t", debug=False, default_response_class=HTMLResponse))
                )
                client = TestClient(api)
                self.assertIn("STATIC", client.get("/r/items/static").text)
                self.assertIn("DYN-z", client.get("/r/items/z/").text)
            finally:
                sys.path.remove(str(root))

    def test_htmx_events_get_events_is_callable(self):
        h = HtmxEvents()
        self.assertTrue(callable(h.get_events))
        self.assertEqual(h.get_events("hx-get"), {})
        self.assertIsInstance(h.hx_get_events, dict)


if __name__ == "__main__":
    unittest.main()
