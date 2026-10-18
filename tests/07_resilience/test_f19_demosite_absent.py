"""F-19 — retired demosite/ stays gone."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestF19DemositeAbsent(unittest.TestCase):
    def test_demosite_dir_gone(self):
        self.assertFalse((ROOT / "demosite").exists())

    def test_demosite_import_error(self):
        with self.assertRaises(ImportError):
            import demosite  # noqa: F401


if __name__ == "__main__":
    unittest.main()
