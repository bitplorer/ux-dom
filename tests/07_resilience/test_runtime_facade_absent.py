"""Absence lock: ``ux_dom.runtime`` (alias-only facade) is gone.

The Document-facing names live on the top level and alias ``ux_dom.plugins``.
"""
from __future__ import annotations

import importlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestRuntimeFacadeAbsent(unittest.TestCase):
    def test_module_does_not_import(self):
        with self.assertRaises(ImportError):
            importlib.import_module("ux_dom.runtime")

    def test_dir_absent(self):
        self.assertFalse((ROOT / "src" / "ux_dom" / "runtime").exists())

    def test_top_level_facades_alias_plugins(self):
        import ux_dom
        from ux_dom.plugins.control import HtmxControl
        from ux_dom.plugins.csp import Csp
        from ux_dom.plugins.runtime import UxChannelRuntime, XElementRuntime

        self.assertIs(ux_dom.XElement, XElementRuntime)
        self.assertIs(ux_dom.Htmx, HtmxControl)
        self.assertIs(ux_dom.Csp, Csp)
        self.assertIs(ux_dom.Channel, UxChannelRuntime)

    def test_no_runtime_import_in_tree(self):
        hits = []
        for base in ("src", "tests", "examples", "standalone"):
            for py in (ROOT / base).rglob("*.py"):
                if py.name == Path(__file__).name:
                    continue
                text = py.read_text(encoding="utf-8", errors="replace")
                if "from ux_dom.runtime" in text or "import ux_dom.runtime" in text:
                    hits.append(str(py.relative_to(ROOT)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
