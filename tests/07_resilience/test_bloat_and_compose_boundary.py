"""Task A boundary and Task B public-module deprecation shims.

Task A stops: ux-dom must not import ux-compose (new dependency and a cycle).
Task B: public modules with no in-repo consumers stay, and warn on import.
"""

from __future__ import annotations

import ast
import importlib
import sys
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "ux_dom"

DOM_UI_PUBLIC_NAMES = (
    "ModelValidator",
    "ModelField",
    "Queries",
    "init",
    "query",
    "UiMeta",
    "UIBase",
)


def _fresh_import(module_name: str):
    sys.modules.pop(module_name, None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        module = importlib.import_module(module_name)
    return module, caught


class TestComposeDependencyDirection(unittest.TestCase):
    """Characterization: ux-dom does not depend on ux-compose."""

    def test_pyproject_has_no_ux_compose_dependency(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        deps = text.split("[tool.poetry.dependencies]", 1)[1].split("[", 1)[0]
        self.assertNotIn("ux-compose", deps)
        self.assertNotIn("ux_compose", deps)

    def test_library_source_does_not_import_ux_compose(self):
        offenders = []
        for path in SRC.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                if any(
                    name == "ux_compose" or name.startswith("ux_compose.")
                    for name in names
                ):
                    offenders.append(f"{path}:{node.lineno}")
        self.assertEqual(offenders, [])


class TestPublicBloatModulesStay(unittest.TestCase):
    """Characterization: public-by-name modules are not deleted."""

    def test_module_files_remain(self):
        expected = {
            "ux_dom.dom.src.pythontags": SRC / "dom/src/pythontags.py",
            "ux_dom.dom.src.sphinxtags": SRC / "dom/src/sphinxtags.py",
            "ux_dom.alpinejs.ripple_btn": SRC / "alpinejs/ripple_btn.py",
            "ux_dom.dom.ui": SRC / "dom/ui.py",
        }
        for module_name, path in expected.items():
            self.assertTrue(path.is_file(), module_name)

    def test_pythontags_class_still_renders(self):
        from ux_dom.dom.src.pythontags import Class, Def

        rendered = Class(
            "Person",
            Def("render", args="*args **kwargs"),
            bases="models.Model",
        ).__render__()
        self.assertIn("class Person(models.Model):", rendered)
        self.assertIn("def render(self, *args, **kwargs):", rendered)

    def test_sphinxtags_heading_still_renders(self):
        from ux_dom.dom.src.sphinxtags import Class, Function, Heading, VarName

        rendered = Heading(
            "Hello",
            Class("BaseClass", VarName("something")),
            Function("ls"),
        ).__render__()
        self.assertIn("Hello", rendered)
        self.assertIn(":class BaseClass:", rendered)
        self.assertIn("`something`", rendered)

    def test_ripple_btn_still_renders_a_button(self):
        from ux_dom.alpinejs.ripple_btn import Button

        rendered = Button("Login").__render__()
        self.assertIn("<button", rendered)
        self.assertIn("Login", rendered)

    def test_dom_ui_public_names_remain_in_source(self):
        tree = ast.parse((SRC / "dom/ui.py").read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in DOM_UI_PUBLIC_NAMES:
            self.assertIn(name, names)


class TestPublicBloatDeprecationWarnings(unittest.TestCase):
    """Importing a public zero-consumer module warns; it is not removed."""

    def test_each_importable_bloat_module_warns(self):
        for module_name in (
            "ux_dom.dom.src.pythontags",
            "ux_dom.dom.src.sphinxtags",
            "ux_dom.alpinejs.ripple_btn",
        ):
            with self.subTest(module_name=module_name):
                _module, caught = _fresh_import(module_name)
                messages = [
                    str(item.message)
                    for item in caught
                    if issubclass(item.category, DeprecationWarning)
                ]
                self.assertTrue(
                    any(module_name in message for message in messages),
                    messages,
                )

    def test_dom_ui_warns_before_optional_tortoise_import(self):
        sys.modules.pop("ux_dom.dom.ui", None)
        sys.modules.pop("ux_dom.dom._ui_deprecation", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                importlib.import_module("ux_dom.dom.ui")
            except ImportError as exc:
                self.assertIn("tortoise", str(exc).lower())
        messages = [
            str(item.message)
            for item in caught
            if issubclass(item.category, DeprecationWarning)
        ]
        self.assertTrue(
            any("ux_dom.dom.ui" in message for message in messages), messages
        )


class TestPytestWorkflow(unittest.TestCase):
    def test_github_pytest_workflow_runs_pytest_on_python_314(self):
        path = ROOT / ".github" / "workflows" / "pytest.yml"
        self.assertTrue(path.is_file(), "pytest workflow missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("pytest", text)
        self.assertIn("3.14", text)
        self.assertIn("poetry install", text)


if __name__ == "__main__":
    unittest.main()
