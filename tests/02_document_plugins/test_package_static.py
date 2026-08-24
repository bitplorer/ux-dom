"""Single-copy package static — no dual assets for installed libraries."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ux_dom.plugins import App, XElementRuntime
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.package_static import PackageStaticContribution, PackagedFile
from ux_dom.plugins.runtime import XELEMENT_JS_URL, UxChannelRuntime
from helpers import ScaffoldOptions, create_app
from ux_dom.cli.build import run_build
import sys


class TestSingleCopyXElement(unittest.TestCase):
    def test_no_artifacts_by_default(self):
        xe = XElementRuntime()
        self.assertEqual(list(xe.artifacts()), [])
        files = list(xe.served_files())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].url, XELEMENT_JS_URL)
        self.assertTrue(files[0].path.is_file())
        head = list(xe.document_head())
        self.assertIn(XELEMENT_JS_URL, "".join(str(x) for x in head))

    def test_app_build_serves_from_package(self):
        set_hub(PluginHub())
        app = (
            App().use(XElementRuntime()).build(asgi=FastAPI(title="t", debug=True, default_response_class=HTMLResponse))
        )
        c = TestClient(app)
        r = c.get(XELEMENT_JS_URL)
        self.assertEqual(r.status_code, 200, r.text[:100])
        self.assertIn("x-tagname", r.text)

    def test_materialize_writes_nothing_for_package_mount(self):
        hub = PluginHub()
        hub.add_contribution(XElementRuntime())
        with TemporaryDirectory() as td:
            rep = hub.materialize(Path(td))
            self.assertEqual(rep.files, [])
            self.assertFalse((Path(td) / "assets/js/x_element.js").exists())


class TestScaffoldSingleCopy(unittest.TestCase):
    def test_create_app_no_dual_js_file(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "sc",
                    dest=Path(td) / "sc",
                    force=True,
                    template="minimal",
                    with_tailwind=False,
                )
            )
            # Should NOT require dual copy
            self.assertFalse(
                (root / "assets/js/x_element.js").is_file(),
                "scaffold must not dual-copy x_element.js into assets/",
            )
            main = (root / "app/main.py").read_text()
            self.assertTrue(
                "XElement" in main
                or "document.mount" in main
                or "xelement=True" in main
                or "App.web" in main
                or "XElement"
                in Path(str(root if "root" in dir() else "."))
                .joinpath("app/document.py")
                .read_text()
                if False
                else ("XElement" in main or "document.mount" in main)
            )
            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                from app.main import app

                c = TestClient(app)
                r = c.get(XELEMENT_JS_URL)
                self.assertEqual(r.status_code, 200)
                page = c.get("/")
                self.assertEqual(page.status_code, 200)
                self.assertIn("index", page.text.lower())
            finally:
                if str(root) in sys.path:
                    sys.path.remove(str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]

    def test_build_package_ok_without_assets_js(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "bp", dest=Path(td) / "bp", force=True, with_tailwind=False
                )
            )
            rep = run_build(
                cwd=root, skip_tailwind=True, package=True, package_name="bp"
            )
            self.assertTrue(rep.ok, rep.steps)
            # package should not claim dual-copy requirement
            man = (rep.package_path / "MANIFEST.json").read_text()
            self.assertIn("single_copy", man)


class TestUxChannelSingleCopy(unittest.TestCase):
    def test_default_no_artifacts(self):
        rt = UxChannelRuntime.optional()
        if rt is None:
            self.skipTest("uxchannel not installed")
        self.assertEqual(list(rt.artifacts()), [])
        # default: tags only; channel host serves bytes
        self.assertEqual(list(rt.served_files()), [])
        html = "".join(str(x) for x in rt.document_head())
        self.assertIn("/ux-channel/static/ux-channel.js", html)

    def test_ux_dom_can_serve_if_requested(self):
        rt = UxChannelRuntime.optional(mount_via_ux_dom=True)
        if rt is None:
            self.skipTest("uxchannel not installed")
        files = list(rt.served_files())
        self.assertTrue(len(files) >= 1)
        self.assertTrue(all(f.url.startswith("/ux-channel/static/") for f in files))


if __name__ == "__main__":
    unittest.main()
