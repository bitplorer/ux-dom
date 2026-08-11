"""SafeStaticFile allowlist — investigation + regression matrix."""

from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ux_dom.plugins import App, XElementRuntime
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.package_static import PackagedFile, PackageStaticContribution
from ux_dom.plugins.runtime import XELEMENT_JS_URL
from ux_dom.plugins.safe_static import (
    ALLOWED_EXTENSIONS,
    SafeStaticFile,
    UnsafeStaticError,
    allowlist_summary,
    collect_served_files,
)


class TestAllowlistMatrix(unittest.TestCase):
    def test_summary_shape(self):
        s = allowlist_summary()
        self.assertIn(".js", s["allowed_extensions"])
        self.assertNotIn(".py", s["allowed_extensions"])
        self.assertNotIn(".json", s["allowed_extensions"])  # tightened

    def test_x_element_ok(self):
        f = SafeStaticFile.from_package(
            "ux_dom.scripts",
            "x_element.js",
            url=XELEMENT_JS_URL,
            plugin="ux_dom.xelement",
        )
        self.assertTrue(f.path.is_file())
        self.assertEqual(f.package_root, f.path.parent)
        self.assertIn(b"x-tagname", f.read_bytes())

    def test_nested_url_ok(self):
        f = SafeStaticFile.from_package(
            "ux_dom.scripts",
            "x_element.js",
            url="/ux-dom/static/vendor/x_element.js",
        )
        self.assertEqual(f.url, "/ux-dom/static/vendor/x_element.js")

    def test_reject_py_file(self):
        with self.assertRaises(UnsafeStaticError):
            SafeStaticFile.from_package(
                "ux_dom.scripts",
                "__init__.py",
                url="/ux-dom/static/__init__.py",
            )

    def test_reject_path_traversal_resource(self):
        with self.assertRaises(UnsafeStaticError):
            SafeStaticFile.from_package(
                "ux_dom.scripts",
                "../settings/document.py",
                url="/ux-dom/static/document.py",
            )

    def test_reject_bad_url_prefix(self):
        for url in ("/etc/passwd", "/app/main.py", "/static/x.js", "/"):
            with self.assertRaises(UnsafeStaticError):
                SafeStaticFile.from_package("ux_dom.scripts", "x_element.js", url=url)

    def test_reject_url_traversal(self):
        with self.assertRaises(UnsafeStaticError):
            SafeStaticFile.from_package(
                "ux_dom.scripts",
                "x_element.js",
                url="/ux-dom/static/../x_element.js",
            )

    def test_reject_space_in_url(self):
        with self.assertRaises(UnsafeStaticError):
            SafeStaticFile.from_package(
                "ux_dom.scripts",
                "x_element.js",
                url="/ux-dom/static/foo bar.js",
            )

    def test_channel_url_shape(self):
        # shape only — file may not exist without ux_channel
        from ux_dom.plugins.safe_static import _validate_url

        self.assertEqual(
            _validate_url("/ux-channel/static/ux-channel.min.js"),
            "/ux-channel/static/ux-channel.min.js",
        )

    def test_loose_pkg_url_without_static_rejected(self):
        with self.assertRaises(UnsafeStaticError):
            SafeStaticFile.from_package(
                "ux_dom.scripts",
                "x_element.js",
                url="/ux-pkg/demo/x_element.js",  # missing /static/
            )


class TestNoDirectoryLeak(unittest.TestCase):
    def test_app_serves_js_not_init_py(self):
        set_hub(PluginHub())
        app = (
            App()
            .use(XElementRuntime())
            .use(FastAPIHost(title="sec", debug=True))
            .build()
        )
        c = TestClient(app)
        r = c.get(XELEMENT_JS_URL)
        self.assertEqual(r.status_code, 200)
        self.assertIn("x-tagname", r.text)
        self.assertEqual(c.get("/ux-dom/static/__init__.py").status_code, 404)
        self.assertEqual(c.get("/ux-dom/static/").status_code, 404)
        self.assertEqual(c.get("/ux-dom/static/../../etc/passwd").status_code, 404)

    def test_collect_only_allowlisted(self):
        hub = PluginHub()
        hub.add_contribution(XElementRuntime())
        files = collect_served_files(hub)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].url, XELEMENT_JS_URL)
        self.assertEqual(files[0].path.suffix, ".js")


class TestContributionExplicitFiles(unittest.TestCase):
    def test_package_static_refuses_py_resource(self):
        with self.assertRaises(UnsafeStaticError):
            PackageStaticContribution(
                name="bad",
                files=[
                    PackagedFile(
                        package="ux_dom.scripts",
                        resource="__init__.py",
                        public_name="init.py",
                    )
                ],
                serve="package_mount",
                public_url_prefix="/ux-pkg/bad/static",
            ).served_files()


if __name__ == "__main__":
    unittest.main()
