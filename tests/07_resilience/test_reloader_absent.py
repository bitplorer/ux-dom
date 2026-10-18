"""HMR/reloader residue — ux_dom.reloader stays gone; HMR is uxcompose serve."""
from __future__ import annotations

import importlib
import importlib.util
import unittest


class TestReloaderAbsent(unittest.TestCase):
    def test_package_import_error(self):
        with self.assertRaises(ImportError):
            importlib.import_module("ux_dom.reloader")

    def test_find_spec_none(self):
        self.assertIsNone(importlib.util.find_spec("ux_dom.reloader"))

    def test_submodules_absent(self):
        for mod in (
            "ux_dom.reloader._app",
            "ux_dom.reloader._watch",
            "ux_dom.reloader._notify",
        ):
            with self.subTest(mod=mod):
                with self.assertRaises(ImportError):
                    importlib.import_module(mod)


if __name__ == "__main__":
    unittest.main()
