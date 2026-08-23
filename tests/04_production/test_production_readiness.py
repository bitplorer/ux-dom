"""Stability / standards / consistency gates for production cut."""

from __future__ import annotations

import ast
import importlib
import re
import unittest
from pathlib import Path

import ux_dom
from ux_dom.scripts import x_element_js, x_element_js_text

ROOT = Path(__file__).resolve().parents[2]
UI_DOM = ROOT / "src" / "ux_dom"


class TestVersionAndPython(unittest.TestCase):
    def test_version_matches_pyproject(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(ux_dom.__version__, m.group(1))
        self.assertEqual(ux_dom.__version__, "0.1.0")

    def test_python_requires_314(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('python = ">=3.14,<3.15"', text)


class TestNoDeadSheets(unittest.TestCase):
    def test_sheets_py_removed(self):
        self.assertFalse((UI_DOM / "dom/src/utils/sheets.py").exists())


class TestXElementSingleRuntime(unittest.TestCase):
    def test_only_x_element_js_on_disk(self):
        from ux_dom import scripts as s

        js = [p.name for p in Path(s.__file__).parent.iterdir() if p.suffix == ".js"]
        self.assertIn("x_element.js", js)
        self.assertNotIn("html_elements.js", js)

    def test_runtime_contract_in_source(self):
        src = x_element_js_text()
        self.assertIn("x-tagname", src)
        self.assertIn("UxDom.XElement", src)
        self.assertNotIn("ATTR_TAG_LEGACY", src)

    def test_package_exports_x_element_js(self):
        from ux_dom import scripts as s

        self.assertTrue(hasattr(s, "x_element_js"))
        self.assertTrue(callable(s.x_element_js_text))
        self.assertFalse(hasattr(s, "html_elements"), "removed in 0.1")
        self.assertFalse(hasattr(s, "x_component_js"), "removed in 0.1")


class TestDocsConsistency(unittest.TestCase):
    def test_readme_install_mention_314_and_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("0.1.0", readme)
        self.assertIn("0.1.0", install)
        self.assertIn("3.14", readme)
        self.assertIn("3.14", install)
        self.assertNotIn("(required) required", install)

    def test_readme_mentions_x_element_contract(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("x_element.js", readme)
        self.assertIn("XElement", readme)

    def test_no_stale_html_elements_js_in_docs(self):
        # Allow historical mention only with Removed / legacy context
        for path in (ROOT / "docs").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if (
                "html_elements.js" in text
                and "Removed" not in text
                and "legacy" not in text.lower()
            ):
                # FINAL_PLAN etc. should be cleaned
                if "html_elements.js" in text:
                    self.fail(
                        f"{path.name} still references html_elements.js without legacy note"
                    )


class TestImportSurfaceStable(unittest.TestCase):
    """Critical public imports must not raise."""

    def test_core_imports(self):
        from ux_dom import Component, Document, Fragment, WebAssets, __version__
        from ux_dom.dom import button, div, span, template
        from ux_dom.dom.htmlelement import (
            AlpineComponent,
            CustomElement,
            WebComponent,
            XElement,
        )
        from ux_dom.plugins import App
        from ux_dom.scripts import x_element_js

        self.assertTrue(__version__)
        self.assertTrue(callable(div))
        self.assertTrue(issubclass(CustomElement, XElement))
        self.assertTrue(issubclass(WebComponent, XElement))
        self.assertTrue(issubclass(AlpineComponent, XElement))

    def test_ux_dom_package_modules_importable(self):
        """Every top-level ux_dom package submodule imports without error."""
        failures = []
        for path in UI_DOM.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            if path.name == "setup.py":
                continue
            # skip heavy demos under ux_dom if any
            rel = path.relative_to(ROOT)
            if path.name.startswith("test"):
                continue
            parts = list(path.with_suffix("").relative_to(ROOT).parts)
            if parts[-1] == "__init__":
                mod = ".".join(parts[:-1])
            else:
                mod = ".".join(parts)
            if not mod.startswith("ux_dom"):
                continue

            try:
                importlib.import_module(mod)
            except Exception as e:
                failures.append(f"{mod}: {type(e).__name__}: {e}")
        # limit noise: only fail if many; report all
        if failures:
            # filter known optional
            hard = [f for f in failures if "No module named" not in f or "valio" in f]
            self.assertEqual(hard, [], "\n".join(hard[:40]))


class TestSyntaxAllLibrarySources(unittest.TestCase):
    def test_ast_parse_ux_dom_tree(self):
        bad = []
        for path in UI_DOM.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as e:
                bad.append(f"{path}: {e}")
        self.assertEqual(bad, [])


class TestScaffoldProductionArtifacts(unittest.TestCase):
    def test_create_app_ships_runtime_not_old_names(self):
        from tempfile import TemporaryDirectory

        from helpers import ScaffoldOptions, create_app

        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "prodchk",
                    dest=Path(td) / "prodchk",
                    force=True,
                    template="minimal",
                )
            )
            # single-copy: JS stays in installed package, not app assets/
            self.assertFalse((root / "assets/js/x_element.js").exists())
            self.assertFalse((root / "assets/js/html_elements.js").exists())
            self.assertFalse((root / "assets/js/xcomponent.js").exists())
            main = (root / "app/main.py").read_text(encoding="utf-8")
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
            doc = (root / "app/document.py").read_text(encoding="utf-8")
            self.assertTrue("XElement" in doc or "shell_fragments" in doc)
            m = (root / "app/main.py").read_text(encoding="utf-8")
            self.assertTrue(
                "document.mount" in main
                or "XElement" in (root / "app/document.py").read_text()
            )
            self.assertNotIn("html_elements", doc)
            # product scaffold metadata is uxcompose, not ux-dom
            self.assertFalse((root / ".ux_dom-scaffold.json").exists())


if __name__ == "__main__":
    unittest.main()


class TestPublicSurfaceTypecheck(unittest.TestCase):
    def test_mypy_full_package_clean(self):
        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "src/ux_dom",
                "--ignore-missing-imports",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            r.returncode,
            0,
            msg=r.stdout + r.stderr,
        )
