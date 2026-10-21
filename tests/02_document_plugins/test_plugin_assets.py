"""Contribution plugin model — package mount (single copy) + shell_fragments."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from helpers import BodyScript, ScaffoldOptions, create_app
from ux_dom.plugins import App, XElementRuntime, shell_fragments
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XELEMENT_JS_URL
from ux_dom.plugins.safe_static import collect_served_files


class TestContributionHub(unittest.TestCase):
    def setUp(self):
        set_hub(PluginHub())

    def test_xelement_shell_package_mount(self):
        hub = PluginHub()
        hub.add_contribution(XElementRuntime())
        head, _ = hub.shell_fragments()
        self.assertIn(XELEMENT_JS_URL, "".join(str(x) for x in head))
        # the files App.build mounts (_mount_package_static)
        files = collect_served_files(hub)
        self.assertTrue(any(f.url == XELEMENT_JS_URL for f in files))

    def test_app_use_order(self):
        builder = (
            App().use(XElementRuntime()).use(BodyScript())
        )
        head, body = builder.shell_fragments()
        self.assertIn("x_element.js", "".join(str(x) for x in head))
        self.assertIn("cdn.example/lib.js", "".join(str(x) for x in body))

    def test_app_owned_js_contribution_is_auto_tagged(self):
        """A contribution's artifacts become shell tags (ux-dom writes no files)."""
        from ux_dom.plugins.contribution import StaticArtifact

        class DemoJs:
            plugin_kind = "contribution"
            name = "demo"

            def __init__(self):
                self.art = StaticArtifact(
                    key="p.js", public_path="/assets/js/vendor/demo/p.js", inject="body"
                )

            def artifacts(self):
                return (self.art,)

            def document_head(self):
                return ()

            def document_body(self):
                return ()

        hub = PluginHub()
        set_hub(hub)
        hub.add_contribution(DemoJs())
        _, body = hub.shell_fragments()
        self.assertIn('src="/assets/js/vendor/demo/p.js"', "".join(str(x) for x in body))


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
                page = c.get("/")
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
