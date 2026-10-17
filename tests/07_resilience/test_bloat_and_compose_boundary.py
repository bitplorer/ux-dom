"""Task A boundary: ux-dom must not import ux-compose (new dependency and a cycle).

Task B (deprecated public modules) was removed in 0.2.0; see test_no_deprecations.py.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "ux_dom"


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
        # ux-channel integration runs against a pinned commit, never skipped.
        self.assertIn('UX_DOM_REQUIRE_CHANNEL: "1"', text)
        self.assertRegex(text, r"ux-channel\.git@[0-9a-f]{40}#subdirectory=python")


if __name__ == "__main__":
    unittest.main()
