"""Every third-party package ux_dom imports must be declared, not borrowed."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _declared() -> set[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = data["tool"]["poetry"]["dependencies"]
    return {name.lower() for name in deps}


def test_typingx_is_declared():
    # compat/valio_pep649.py imports typingx directly; valio pulling it in
    # transitively is an accident, not a contract.
    assert "typingx" in _declared()
