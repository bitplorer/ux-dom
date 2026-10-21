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
