"""Edge cases found by exploratory discovery (kept as permanent guards)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ux_dom.dom import div, span
from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute


class TestRenderCycleGuard(unittest.TestCase):
    def test_parent_child_cycle_finite(self):
        a, b = div(id="a"), div(id="b")
        a.add(b)
        b.add(a)
        html = a.__render__(pretty=False)
        self.assertIn("cycle", html)
        self.assertLess(len(html), 500)
        self.assertIn("cycle", a.__render__(pretty=False))

    def test_walk_stream_cycle(self):
        a, b = div(id="a"), div(id="b")
        a.add(b)
        b.add(a)
        walked = "".join(a._walk_render_tokens(0, "  ", False, False))
        self.assertIn("cycle", walked)


class TestAttrDialectConventions(unittest.TestCase):
    def test_alpine_modifier_via_dot_token(self):
        h = div(x_on_click_dot_outside="f").__render__(pretty=False)
        self.assertIn("@click.outside", h)

    def test_hx_on_double_colon_via_dunder(self):
        h = div(hx_on_htmx__before_request="f").__render__(pretty=False)
        self.assertIn("hx-on:htmx:before-request", h)

    def test_text_and_attr_escape(self):
        h = div("<script>x</script>", title="a\x22b").__render__(pretty=False)
        self.assertIn("&" + "lt;script&" + "gt;", h)
        self.assertIn("&" + "quot;", h)


class TestDirectoryRouterDottedFolder(unittest.TestCase):
    def test_api_v1_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "dotapp"
            (pkg / "app" / "api.v1").mkdir(parents=True)
            for p in [pkg, pkg / "app", pkg / "app" / "api.v1"]:
                (p / "__init__.py").write_text("")
            (pkg / "app" / "api.v1" / "route.py").write_text(
                "def get():\n"
                "    from ux_dom.dom import div\n"
                "    return div('v1-ok')\n"
            )
            sys.path.insert(0, str(root))
            try:
                app = FastAPI()
                app.include_router(
                    DirectoryRouter(
                        base_directory="app",
                        package_dir=pkg,
                        route_class=StreamingRoute,
                    )
                )
                paths = list(app.openapi()["paths"])
                self.assertTrue(any("api.v1" in p for p in paths), paths)
                r = TestClient(app).get(paths[0])
                self.assertEqual(r.status_code, 200)
                self.assertIn("v1-ok", r.text)
            finally:
                sys.path.remove(str(root))


class TestAddEdges(unittest.TestCase):
    def test_add_dict_and_generator(self):
        d = div()
        d.add({"data-x": "1", "cls": "z"})
        d.add(span(str(i)) for i in range(3))
        h = d.__render__(pretty=False)
        self.assertIn("data-x", h)
        self.assertIn('class="z"', h)
        self.assertEqual(len(d.get(span)), 3)


if __name__ == "__main__":
    unittest.main()
