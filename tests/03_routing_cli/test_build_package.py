"""uxdom build — single-copy package static + runnable package."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom.cli.build import run_build
from helpers import ScaffoldOptions, create_app
from ux_dom.cli.static_assets import sync_runtime_assets, write_runnable_package
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XELEMENT_JS_URL, XElementRuntime
from ux_dom.scripts import x_element_js_text


class TestStaticSync(unittest.TestCase):
    def test_sync_records_package_mount_not_dual_file(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "app").mkdir()
            hub = PluginHub()
            hub.add_contribution(XElementRuntime())
            set_hub(hub)
            rep = sync_runtime_assets(root, hub=hub)
            self.assertTrue(rep.ok)
            self.assertTrue(any("/ux-dom/static" in m[0] for m in rep.mounts))
            # no dual copy into assets
            self.assertFalse((root / "assets/js/x_element.js").exists())
            self.assertTrue(x_element_js_text())


class TestRunnablePackage(unittest.TestCase):
    def test_package_without_vendored_js(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "pkg", dest=Path(td) / "pkg", force=True, with_tailwind=False
                )
            )
            dest = write_runnable_package(root, name="pkg")
            self.assertTrue((dest / "run.sh").is_file())
            man = json.loads((dest / "MANIFEST.json").read_text())
            self.assertEqual(man.get("static_model"), "single_copy_from_site_packages")
            self.assertEqual(man.get("x_element_js_url"), XELEMENT_JS_URL)
            # library JS not vendored into package tree
            self.assertFalse((dest / "assets/js/x_element.js").exists())

    def test_build_and_serve_from_package_mount(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "run", dest=Path(td) / "run", force=True, with_tailwind=False
                )
            )
            rep = run_build(
                cwd=root, skip_tailwind=True, package=True, package_name="run"
            )
            self.assertTrue(rep.ok, rep.steps)
            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                from app.main import app

                c = TestClient(app)
                r = c.get(XELEMENT_JS_URL)
                self.assertEqual(r.status_code, 200)
                self.assertIn("x-tagname", r.text)
                page = c.get("/index")
                self.assertIn(XELEMENT_JS_URL.lstrip("/").split("/")[0], page.text)
                self.assertIn("x_element.js", page.text)
            finally:
                if str(root) in sys.path:
                    sys.path.remove(str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]


if __name__ == "__main__":
    unittest.main()
