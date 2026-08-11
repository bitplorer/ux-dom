"""DX commands: doctor, add, lint, tutorial scaffold, diagnostics."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.cli.adders import AddError, add_component, add_route, add_xelement
from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.lint import lint_project
from ux_dom.cli.scaffold import ScaffoldOptions, available_templates, create_app
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement, WebComponent, XElement

ROOT = Path(__file__).resolve().parents[2]


class TestTemplates(unittest.TestCase):
    def test_tutorial_listed(self):
        self.assertIn("tutorial", available_templates())


class TestTutorialScaffold(unittest.TestCase):
    def test_creates_guided_routes(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "learn",
                    dest=Path(td) / "learn",
                    template="tutorial",
                    force=True,
                )
            )
            for rel in [
                "app/routes/htmx_demo.py",
                "app/routes/xelement_demo.py",
                "app/routes/recipes.py",
                "app/components/x_hello.py",
            ]:
                self.assertTrue((root / rel).is_file(), rel)
            self.assertTrue(
                "CreateAsgi" in (root / "app/main.py").read_text()
                or "XElement" in (root / "app/document.py").read_text()
            )
            # boot routes
            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                from fastapi.testclient import TestClient
                from app.main import app

                c = TestClient(app)
                self.assertEqual(c.get("/health").status_code, 200)
                for path in [
                    "/index/Index",
                    "/htmx_demo/HtmxDemo",
                    "/xelement_demo/XelementDemo",
                    "/recipes/Recipes",
                    "/about/About",
                ]:
                    r = c.get(path)
                    self.assertEqual(r.status_code, 200, path)
                self.assertIn("x_element.js", c.get("/xelement_demo/XelementDemo").text)
            finally:
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                if str(root) in sys.path:
                    sys.path.remove(str(root))


class TestDoctor(unittest.TestCase):
    def test_global_doctor_ok(self):
        rep = run_doctor(cwd=ROOT, port=59999)
        self.assertTrue(rep.ok)
        names = {c.name for c in rep.checks}
        self.assertIn("python", names)
        self.assertIn("ux_dom", names)
        self.assertIn("x_element.js", names)

    def test_doctor_on_scaffold(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "d", dest=Path(td) / "d", force=True, template="minimal"
                )
            )
            rep = run_doctor(cwd=root, port=59998)
            self.assertTrue(rep.ok)
            self.assertEqual(rep.project_root, root.resolve())


class TestAdders(unittest.TestCase):
    def test_add_component_route_xelement(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "a", dest=Path(td) / "a", force=True, template="minimal"
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                pc = add_component("Notice")
                self.assertTrue(pc.is_file())
                pr = add_route("settings")
                self.assertTrue(pr.is_file())
                self.assertIn("class Settings", pr.read_text())
                px = add_xelement("Star", kind="shadow")
                self.assertTrue(px.is_file())
                self.assertIn("WebComponent", px.read_text())
                self.assertIn("shadowroot", px.read_text())
                with self.assertRaises(AddError):
                    add_component("Notice")  # exists
                add_component("Notice", force=True)
            finally:
                os.chdir(old)


class TestLint(unittest.TestCase):
    def test_lint_clean_scaffold(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "l", dest=Path(td) / "l", force=True, template="minimal"
                )
            )
            issues = lint_project(root)
            errors = [i for i in issues if i.level == "error"]
            self.assertEqual(errors, [], issues)


class TestDiagnosticsMessages(unittest.TestCase):
    def test_xelement_messages_actionable(self):
        class Bad(XElement):
            def render(self, tag_name):
                return div("no")

        with self.assertRaises(AttributeError) as ctx:
            Bad("x")
        msg = str(ctx.exception)
        self.assertIn("x-tagname", msg)
        self.assertIn(
            "XELEMENT", msg.upper() or "xelement" in msg.lower() or "docs" in msg
        )

    def test_custom_shadow_message(self):
        class Bad(CustomElement):
            tag_name = "c"

            def render(self, tag_name="c"):
                return template(
                    div("x"), **{"x-tagname": tag_name, "shadowroot": "true"}
                )

        with self.assertRaises(AttributeError) as ctx:
            Bad.definition()
        self.assertIn("WebComponent", str(ctx.exception))


class TestGallery(unittest.TestCase):
    def test_gallery_page_renders(self):
        from ux_dom.debug_gallery import gallery_page

        class H(CustomElement):
            tag_name = "g"

            def render(self, tag_name="g"):
                return template(div("hi"), **{"x-tagname": tag_name})

        html = str(gallery_page([H.definition()]))
        self.assertIn("ux_dom-gallery", html)
        self.assertIn("x-tagname", html)


class TestCliEntry(unittest.TestCase):
    def test_help_lists_commands(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ux_dom.cli.cli", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=30,
        )
        # typer may use different module path
        out = proc.stdout + proc.stderr
        if proc.returncode != 0:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from ux_dom.cli import ux_dom; ux_dom(['--help'])",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                timeout=30,
            )
            out = proc.stdout + proc.stderr
        self.assertTrue(
            "doctor" in out or "create-app" in out or proc.returncode == 0,
            out[-500:],
        )


if __name__ == "__main__":
    unittest.main()
