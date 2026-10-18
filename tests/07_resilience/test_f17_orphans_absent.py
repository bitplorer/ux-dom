"""F-17 — zero-consumer orphan modules stay gone (absence locks)."""
from __future__ import annotations

import importlib
import importlib.util
import unittest


_ABSENT = (
    "ux_dom.examples",
    "ux_dom.examples.links",
    "ux_dom.examples.toggle",
    "ux_dom.debug_gallery",
    "ux_dom.plugins.response",
    "ux_dom.plugins.style",
    "ux_dom.assets",
    "ux_dom.cli.envfile",
    "ux_dom.settings.paths",
    "ux_dom.utils.functional",
)


class TestF17OrphansAbsent(unittest.TestCase):
    def test_modules_import_error(self):
        for mod in _ABSENT:
            with self.subTest(mod=mod):
                with self.assertRaises(ImportError):
                    importlib.import_module(mod)

    def test_find_spec_none(self):
        for mod in ("ux_dom.assets", "ux_dom.debug_gallery", "ux_dom.plugins.style"):
            with self.subTest(mod=mod):
                self.assertIsNone(importlib.util.find_spec(mod))


if __name__ == "__main__":
    unittest.main()
