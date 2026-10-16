"""Task A boundary and Task B public-module deprecation shims.

Task A stops: ux-dom must not import ux-compose (new dependency and a cycle).
Task B: public modules stay and warn on import. The MRO walkers import every
module, so a second import must still warn.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
import tempfile
import unittest
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


def _imported_deprecations(
    module_name: str,
    *,
    extra_pops: tuple[str, ...] = (),
    prime: bool = False,
):
    """Import ``module_name`` from a real file so the warning names that file.

    ``prime`` repeats the MRO walkers: import once with warnings ignored, leave
    any package attribute in place, then pop ``sys.modules`` and import again.
    """
    pops = "\n".join(
        f"sys.modules.pop({name!r}, None)" for name in (module_name, *extra_pops)
    )
    prime_source = ""
    if prime:
        prime_source = (
            "with warnings.catch_warnings():\n"
            "    warnings.simplefilter('ignore')\n"
            "    try:\n"
            f"        import {module_name}\n"
            "    except Exception:\n"
            "        pass\n"
        )
    source = (
        "import sys\n"
        "import warnings\n"
        f"{prime_source}"
        f"{pops}\n"
        "with warnings.catch_warnings(record=True) as caught:\n"
        "    warnings.simplefilter('always')\n"
        "    try:\n"
        f"        import {module_name}\n"
        "    except ImportError as exc:\n"
        "        import_error = exc\n"
        "    else:\n"
        "        import_error = None\n"
        "deprecations = [\n"
        "    item\n"
        "    for item in caught\n"
        "    if issubclass(item.category, DeprecationWarning)\n"
        "]\n"
    )
    with tempfile.TemporaryDirectory() as directory:
        importer = Path(directory) / "importer.py"
        importer.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location(
            "bloat_boundary_importer", importer
        )
        if spec is None or spec.loader is None:
            raise AssertionError("importer spec missing")
        module = importlib.util.module_from_spec(spec)
        sys.modules.pop("bloat_boundary_importer", None)
        spec.loader.exec_module(module)
        return importer.resolve(), list(module.deprecations), module.import_error


def _bound_import_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bound: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound.append(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bound.append(alias.asname or alias.name)
    return bound


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
    """Importing a public bloat module warns; it is not removed."""

    def test_each_importable_bloat_module_warns(self):
        for module_name in (
            "ux_dom.dom.src.pythontags",
            "ux_dom.dom.src.sphinxtags",
            "ux_dom.alpinejs.ripple_btn",
        ):
            with self.subTest(module_name=module_name):
                importer, deprecations, error = _imported_deprecations(module_name)
                self.assertIsNone(error)
                self.assertEqual(len(deprecations), 1, deprecations)
                warning = deprecations[0]
                self.assertEqual(Path(warning.filename).resolve(), importer)
                self.assertIn(module_name, str(warning.message))
                loaded = sys.modules[module_name]
                self.assertFalse(
                    hasattr(loaded, "warnings"),
                    "import must not publish a warnings attribute",
                )

    def test_dom_ui_warns_before_optional_tortoise_import(self):
        self.assertFalse((SRC / "dom" / "_ui_deprecation.py").is_file())
        importer, deprecations, error = _imported_deprecations(
            "ux_dom.dom.ui",
            prime=True,
        )
        self.assertIsNotNone(error)
        self.assertIn("tortoise", str(error).lower())
        self.assertEqual(len(deprecations), 1, deprecations)
        warning = deprecations[0]
        self.assertEqual(Path(warning.filename).resolve(), importer)
        self.assertEqual(
            str(warning.message),
            "ux_dom.dom.ui is a deprecated Tortoise form helper.",
        )
        self.assertNotIn("remains importable", str(warning.message))
        self.assertNotIn("ux_dom.ui", str(warning.message))

    def test_dom_ui_does_not_bind_ux_dom(self):
        bound = _bound_import_names(SRC / "dom" / "ui.py")
        self.assertNotIn("ux_dom", bound)
        self.assertNotIn("warnings", bound)
        self.assertIn("_warnings", bound)


class TestPytestWorkflow(unittest.TestCase):
    def test_github_pytest_workflow_runs_pytest_on_python_314(self):
        path = ROOT / ".github" / "workflows" / "pytest.yml"
        self.assertTrue(path.is_file(), "pytest workflow missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn('python-version: "3.14"', text)
        self.assertIn("poetry install", text)
        self.assertIn("run: poetry run pytest tests/", text)
        self.assertNotIn("continue-on-error", text)
        # Browser tests run for real in CI: toolchain installed, skips forbidden.
        self.assertIn('UX_DOM_REQUIRE_BROWSER: "1"', text)
        self.assertIn("npm ci --prefix tests/browser", text)
        self.assertIn("playwright install --with-deps chromium", text)


if __name__ == "__main__":
    unittest.main()
