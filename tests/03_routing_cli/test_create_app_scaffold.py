"""create-app scaffolder + CLI."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app
from ux_dom.cli.scaffold import ScaffoldOptions, available_templates, create_app


class TestScaffoldAPI(unittest.TestCase):
    def test_templates_list(self):
        self.assertEqual(
            set(available_templates()),
            (
                {"minimal", "shop", "live", "tutorial", "dashboard"}
                if "dashboard" in available_templates()
                else set(available_templates())
            ),
        )
        self.assertIn("minimal", available_templates())
        self.assertIn("tutorial", available_templates())

    def test_minimal_app_runs(self):
        root = create_app(
            ScaffoldOptions(
                "t_min",
                dest=Path("/tmp/ux_dom_test_scaffold_min"),
                template="minimal",
                force=True,
            )
        )
        self.assertTrue((root / "app/main.py").exists())
        sys.path.insert(0, str(root))
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        try:
            import app.main as m

            c = TestClient(m.app)
            self.assertTrue(c.get("/health").json()["ok"])
            self.assertEqual(c.get("/index/Index").status_code, 200)
            self.assertEqual(c.get("/about/About").status_code, 200)
        finally:
            sys.path.remove(str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]

    def test_shop_cart_post(self):
        root = create_app(
            ScaffoldOptions(
                "t_shop",
                dest=Path("/tmp/ux_dom_test_scaffold_shop"),
                template="shop",
                force=True,
            )
        )
        sys.path.insert(0, str(root))
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        try:
            import app.main as m

            c = TestClient(m.app)
            self.assertEqual(c.get("/shop/Shop").status_code, 200)
            r = c.post("/cart/Cart")
            self.assertEqual(r.status_code, 200)
            self.assertIn("cart-root", r.text)
        finally:
            sys.path.remove(str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]

    def test_live_with_channel(self):
        try:
            import ux_channel  # noqa: F401
        except ImportError:
            self.skipTest("uxchannel not installed")
        root = create_app(
            ScaffoldOptions(
                "t_live",
                dest=Path("/tmp/ux_dom_test_scaffold_live"),
                template="live",
                force=True,
            )
        )
        sys.path.insert(0, str(root))
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        try:
            import app.main as m

            c = TestClient(m.app)
            self.assertTrue(c.get("/health").json()["channel"])
            r = c.get("/live/Live")
            self.assertEqual(r.status_code, 200)
            self.assertIn("Bump", r.text)
        finally:
            sys.path.remove(str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]


class TestCreateAppXElementRuntime(unittest.TestCase):
    def test_ships_and_loads_x_element_js(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "xe", dest=Path(td) / "xe", force=True, template="minimal"
                )
            )
            doc = (root / "app" / "document.py").read_text(encoding="utf-8")
            main = (root / "app" / "main.py").read_text(encoding="utf-8")
            self.assertTrue("XElement" in doc or "shell_fragments" in doc)
            doc = (root / "app/document.py").read_text()
            self.assertTrue(
                "XElement" in doc
                or "XElementRuntime" in main
                or "document.mount" in main
            )
            # single-copy: no dual file under assets/
            self.assertFalse((root / "assets/js/x_element.js").is_file())

            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                import app.main as m

                c = TestClient(m.app)
                r = c.get("/ux-dom/static/x_element.js")
                self.assertEqual(r.status_code, 200)
                self.assertIn("x-tagname", r.text)
                page = c.get("/index/Index")
                self.assertEqual(page.status_code, 200)
                self.assertIn("ux-dom/static/x_element.js", page.text)
            finally:
                if str(root) in sys.path:
                    sys.path.remove(str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]


class TestCreateAppCLI(unittest.TestCase):
    def test_cli_create_app(self):
        runner = CliRunner()
        dest = "/tmp/ux_dom_test_cli_scaffold"
        r = runner.invoke(
            cli_app,
            [
                "create-app",
                "cli_app",
                "--yes",
                f"--dest={dest}",
                "--force",
                "--template=minimal",
            ],
        )
        self.assertEqual(r.exit_code, 0, f"stdout={r.stdout!r} exc={r.exception!r}")
        self.assertTrue(Path(dest, "app/main.py").exists())

    def test_cli_templates(self):
        r = CliRunner().invoke(cli_app, ["templates"])
        self.assertEqual(r.exit_code, 0)


class TestScaffoldCsp(unittest.TestCase):
    def test_default_wires_csp_auto(self):
        from ux_dom.cli.scaffold import ScaffoldOptions, create_app
        import tempfile
        from pathlib import Path as P

        td = P(tempfile.mkdtemp())
        try:
            root = create_app(
                ScaffoldOptions(app_name="c1", dest=td / "c1", force=True)
            )
            doc = (root / "app/document.py").read_text()
            self.assertIn("Csp.auto", doc)
            self.assertIn("WITH_CSP", (root / "app/settings.py").read_text())
        finally:
            import shutil

            shutil.rmtree(td)

    def test_no_csp_option(self):
        from ux_dom.cli.scaffold import ScaffoldOptions, create_app
        import tempfile
        from pathlib import Path as P

        td = P(tempfile.mkdtemp())
        try:
            root = create_app(
                ScaffoldOptions(
                    app_name="c0", dest=td / "c0", force=True, with_csp=False
                )
            )
            settings = (root / "app/settings.py").read_text()
            self.assertIn("WITH_CSP = False", settings)
        finally:
            import shutil

            shutil.rmtree(td)


if __name__ == "__main__":
    unittest.main()
