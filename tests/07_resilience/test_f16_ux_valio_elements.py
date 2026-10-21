"""F-16: elements validate with ux-valio; legacy valio and its PEP 649 shim stay gone."""
from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestElementsOnUxValio(unittest.TestCase):
    def test_validation_still_runs(self):
        from ux_dom.elements.chars import CharInput

        with self.assertRaises(ValueError):
            CharInput(name="q", type="bogus")

    def test_cast_hooks_keep_rendering(self):
        from ux_dom.elements.chars import CharInput
        from ux_dom.elements.floats import FloatInput

        self.assertEqual(
            CharInput(name="q", min_length="3", max_length="9").__render__(pretty=False),
            '<input maxlength="9" minlength="3" name="q" spellcheck="true" type="text">',
        )
        self.assertEqual(
            FloatInput(name="f", min="1.5", max="5").__render__(pretty=False),
            '<input max="5.0" min="1.5" name="f" placeholder type="number">',
        )

    def test_unchecked_radio_renders_unchecked(self):
        from ux_dom.elements.booleans import RadioInput

        html = RadioInput(name="n", checked=False).__render__(pretty=False)
        self.assertEqual(html, '<input name="n" type="radio">')


class TestLegacyValioAbsent(unittest.TestCase):
    def test_compat_package_absent(self):
        self.assertIsNone(importlib.util.find_spec("ux_dom.compat"))

    def test_import_ux_dom_and_elements_do_not_load_valio(self):
        code = (
            "import sys, ux_dom, ux_dom.elements.chars, ux_dom.elements.enums;"
            "print(sorted(m for m in sys.modules if m == 'valio' or m.startswith('valio.')))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(out, "[]")


if __name__ == "__main__":
    unittest.main()
