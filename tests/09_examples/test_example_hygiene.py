"""Static guards: examples stay on the 0.3.0 API and keep clean scaffolding."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
PY_FILES = sorted(p for p in EXAMPLES.rglob("*.py") if "__pycache__" not in p.parts)
RETIRED = {
    "ux_dom.plugins": "use ux_dom.runtime + Document.use/mount",
    "ux_dom.plugins.control": "use ux_dom.runtime.Htmx",
    "ux_dom.htmx.middleware": "Htmx(middleware=True) installs it via document.mount",
    "ux_dom.scripts": "XElement() serves x_element.js",
}
SCAFFOLD_LEFTOVERS = (
    ".uidom-scaffold.json",
    ".env.example",
    "tailwind.config.js",
    "requirements.txt",
    "pyproject.toml",
    "settings.py",
)


def _rel(path: Path) -> str:
    return str(path.relative_to(EXAMPLES))


@pytest.mark.parametrize("path", PY_FILES, ids=_rel)
def test_no_retired_imports_or_private_rendering(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in RETIRED:
            pytest.fail(f"{_rel(path)} imports {node.module}: {RETIRED[node.module]}")
        if isinstance(node, ast.Attribute) and node.attr == "__render__":
            pytest.fail(
                f"{_rel(path)} calls __render__; use str(node) or a route class"
            )
        if isinstance(node, ast.Name) and node.id in {"get_hub", "shell_fragments"}:
            pytest.fail(f"{_rel(path)} uses the plugin hub")


@pytest.mark.parametrize("path", PY_FILES, ids=_rel)
def test_external_scripts_come_from_runtimes_or_carry_sri(path):
    text = path.read_text(encoding="utf-8")
    for url in re.findall(r"https://(?:unpkg\.com|cdn\.jsdelivr\.net)/[^\"']+", text):
        assert "integrity" in text, f"{_rel(path)} loads {url} without SRI"


def test_no_outdated_scaffolding():
    found = [
        _rel(p)
        for name in SCAFFOLD_LEFTOVERS
        for p in EXAMPLES.rglob(name)
        if "node_modules" not in p.parts
    ]
    assert found == []


def test_every_example_is_importable_by_package_path():
    nested = [_rel(p) for p in EXAMPLES.rglob("app/main.py")]
    assert nested == [], "examples are flat packages: examples.<name>.main:app"
