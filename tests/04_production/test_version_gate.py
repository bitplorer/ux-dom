"""Gate: every file that states the ux-dom version states the real one.

A fixed list of version-bearing files (each must mention the version, and
every X.Y.Z in it must equal ``__version__`` unless listed as a known
non-library string), plus a repo-wide check that no "ux-dom X.Y" brand line
names another version. Add a file here when it starts stating the version.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

import ux_dom

ROOT = Path(__file__).resolve().parents[2]
V = ux_dom.__version__
MAJOR_MINOR = ".".join(V.split(".")[:2])
SEMVER = re.compile(r"(?<![\w.])v?(\d+\.\d+\.\d+)(?!\w|\.\d)")

# file -> X.Y.Z strings in it that are not the ux-dom version
VERSION_FILES: dict[str, frozenset[str]] = {
    "VERSION": frozenset(),
    "src/ux_dom/__init__.py": frozenset(),
    "README.md": frozenset(),
    "INSTALL.md": frozenset({"0.1.0", "0.0.0"}),  # ux-channel floor, bind host
    "docs/INSTALL.md": frozenset(),
    "docs/INDEX.md": frozenset(),
    "docs/reference/API_SURFACE.md": frozenset(),
}

REQUIRED_FORMS = {
    "README.md": rf"^\| \*\*Version\*\* \| `{re.escape(V)}` \|",
    "INSTALL.md": rf"^# ux-dom {re.escape(V)} — Installation$",
    "src/ux_dom/__init__.py": rf'^__version__ = "{re.escape(V)}"$',
    "SECURITY.md": rf"^\| {re.escape(MAJOR_MINOR)}\.x\s+\| Yes",
}

# "ux-dom X.Y" / "uxdom X.Y.Z" brand lines anywhere outside history
BRAND = re.compile(r"\bux-?dom (\d+\.\d+(?:\.\d+)?)\b")
SKIP_DIRS = {".venv", ".git", "node_modules", "examples", "reports", "__pycache__"}
HISTORY = {"CHANGELOG.md", "poetry.lock"}


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pyproject_version_field_matches_package():
    data = tomllib.loads(_text("pyproject.toml"))
    assert data["tool"]["poetry"]["version"] == V


@pytest.mark.parametrize("rel", sorted(VERSION_FILES))
def test_listed_file_states_the_version(rel):
    mentions = [m for m in SEMVER.findall(_text(rel)) if m not in VERSION_FILES[rel]]
    assert mentions, f"{rel}: no version mention (stale list?)"
    wrong = sorted({m for m in mentions if m != V})
    assert not wrong, f"{rel}: {wrong} != __version__ {V}"


@pytest.mark.parametrize("rel", sorted(REQUIRED_FORMS))
def test_required_version_forms(rel):
    assert re.search(REQUIRED_FORMS[rel], _text(rel), re.M), rel


def test_no_stale_brand_version_anywhere():
    stale = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".toml"}:
            continue
        if set(path.relative_to(ROOT).parts) & SKIP_DIRS or path.name in HISTORY:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for m in BRAND.finditer(line):
                if m.group(1) not in (V, MAJOR_MINOR):
                    stale.append(f"{path.relative_to(ROOT)}:{n}: {m.group(0)}")
    assert not stale, "\n".join(stale)
