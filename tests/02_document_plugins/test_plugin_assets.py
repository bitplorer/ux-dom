"""Contribution plugin model — package mount (single copy) + shell_fragments."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom.assets import compose_document_parts, register_js
from ux_dom.cli.scaffold import ScaffoldOptions, create_app
from ux_dom.plugins import App, XElementRuntime, shell_fragments
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XELEMENT_JS_URL


class TestContributionHub(unittest.TestCase):
    def setUp(self):
        set_hub(PluginHub())

    def test_xelement_shell_no_materialize(self):
        hub = PluginHub()
        hub.add_contribution(XElementRuntime())
        # package_mount → zero files written
        with TemporaryDirectory() as td:
            rep = hub.materialize(Path(td))
            self.assertTrue(rep.ok)
            self.assertEqual(rep.files, [])
        head, _ = hub.shell_fragments()
        self.assertIn(XELEMENT_JS_URL, "".join(str(x) for x in head))
        files = hub.served_static_files()
        self.assertTrue(any(f.url == XELEMENT_JS_URL for f in files))

    def test_app_use_order(self):
        builder = (
            App().use(XElementRuntime()).use(HtmxControl(version="2.0.4", cdn=True))
        )
        head, body = builder.shell_fragments()
        self.assertIn("x_element.js", "".join(str(x) for x in head))
        self.assertIn("htmx.org", "".join(str(x) for x in body))

    def test_register_js_adhoc_still_copies_app_owned(self):
        """Ad-hoc app JS is app-owned → materialize under assets is correct."""
        with TemporaryDirectory() as td:
            src = Path(td) / "p.js"
            src.write_text("console.log(1)", encoding="utf-8")
            hub = PluginHub()
            set_hub(hub)
            register_js("demo", "p.js", source=src, placement="body", hub=hub)
            root = Path(td) / "app"
            root.mkdir()
            hub.materialize(root)
            self.assertTrue((root / "assets/js/vendor/demo/p.js").is_file())


class TestScaffoldServesPackageJs(unittest.TestCase):
    def test_page_and_runtime_url(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "ps", dest=Path(td) / "ps", force=True, with_tailwind=False
                )
            )
            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                from app.main import app

                c = TestClient(app)
                self.assertEqual(c.get(XELEMENT_JS_URL).status_code, 200)
                page = c.get("/index/Index")
                self.assertEqual(page.status_code, 200)
                self.assertIn("ux-dom/static/x_element.js", page.text)
            finally:
                if str(root) in sys.path:
                    sys.path.remove(str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]


if __name__ == "__main__":
    unittest.main()
