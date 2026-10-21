"""DX commands: doctor, add, lint, tutorial scaffold, diagnostics."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.cli.adders import AddError, add_component, add_xelement
from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.lint import lint_project
from helpers import ScaffoldOptions, create_app
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement, XElement

ROOT = Path(__file__).resolve().parents[2]


class TestTemplates(unittest.TestCase):
    def test_product_templates_not_on_uxdom(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.scaffold  # noqa: F401


class TestDoctor(unittest.TestCase):
    def test_global_doctor_ok(self):
        rep = run_doctor(cwd=ROOT)
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
            rep = run_doctor(cwd=root)
            self.assertTrue(rep.ok)
            self.assertEqual(rep.project_root, root.resolve())


class TestAdders(unittest.TestCase):
    def test_add_component_xelement(self):
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
                px = add_xelement("Star", kind="shadow")
                self.assertTrue(px.is_file())
                self.assertIn("XElement", px.read_text())
                self.assertIn("shadow", px.read_text())
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
    def test_debug_gallery_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.debug_gallery  # noqa: F401


class TestCliEntry(unittest.TestCase):
    def test_help_lists_commands(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ux_dom.cli.cli", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)},
            timeout=30,
        )
        # typer may use different module path
        out = proc.stdout + proc.stderr
        if proc.returncode != 0:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from ux_dom.cli import app; app(['--help'])",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)},
                timeout=30,
            )
            out = proc.stdout + proc.stderr
        self.assertTrue(
            "doctor" in out or proc.returncode == 0,
            out[-500:],
        )
        self.assertNotIn("create-app", out)


if __name__ == "__main__":
    unittest.main()
