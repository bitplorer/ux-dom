"""Every third-party package ux_dom imports must be declared, not borrowed."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _dependencies() -> dict:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["poetry"]["dependencies"]


def test_legacy_valio_not_declared():
    declared = {name.lower() for name in _dependencies()}
    assert "valio" not in declared
    assert "typingx" not in declared


def test_ux_valio_is_pinned_to_a_commit_sha():
    # ADR 0004: a ux-* dependency is pinned by exact git SHA, never a branch.
    spec = _dependencies()["ux-valio"]
    assert re.fullmatch(r"[0-9a-f]{40}", spec["rev"]), spec
    assert "branch" not in spec and "tag" not in spec


# Import name -> the dependency (or extra) that must declare it. Third-party
# names missing here fail the test below, so a new import picks its owner.
_IMPORT_OWNER = {
    "jinja2": "Jinja2",
    "markupsafe": "MarkupSafe",
    "marko": "marko",
    "typer": "typer",
    "ux_valio": "ux-valio",
    # ux_dom.response.starlette is the optional adapter: starlette comes with
    # the ``fastapi`` extra (see test_extras_match_imports.py).
    "starlette": "fastapi",
}


def _unguarded_imports() -> dict[str, list[str]]:
    """Third-party top-level names imported unconditionally at import time."""
    import ast
    import sys

    found: dict[str, list[str]] = {}
    for path in sorted((ROOT / "src" / "ux_dom").rglob("*.py")):
        for st in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(st, ast.Import):
                names = [a.name for a in st.names]
            elif isinstance(st, ast.ImportFrom) and not st.level and st.module:
                names = [st.module]
            else:
                continue
            for name in names:
                top = name.partition(".")[0]
                if top not in sys.stdlib_module_names and top not in (
                    "ux_dom",
                    "__future__",
                ):
                    found.setdefault(top, []).append(path.relative_to(ROOT).as_posix())
    return found


def test_unguarded_imports_are_declared_directly():
    # A package reached only through another dependency (markupsafe via Jinja2)
    # can disappear when that dependency changes; declare what we import.
    declared = {name.lower() for name in _dependencies()}
    missing = {
        top: paths
        for top, paths in _unguarded_imports().items()
        if _IMPORT_OWNER.get(top, f"<unmapped {top}>").lower() not in declared
    }
    assert missing == {}
