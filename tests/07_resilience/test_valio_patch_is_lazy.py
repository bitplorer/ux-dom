"""``import ux_dom`` must not load or patch valio (review M6)."""

from __future__ import annotations

import subprocess
import sys


def _run(code: str) -> str:
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_import_ux_dom_leaves_valio_alone():
    assert _run("import sys, ux_dom; print('valio' in sys.modules)") == "False"


def test_elements_import_applies_the_patch():
    out = _run(
        "import sys; from ux_dom.elements.chars import CharInput;"
        "print('valio' in sys.modules, str(CharInput(name='q')))"
    )
    assert out.startswith("True <input")
    assert 'name="q"' in out
