"""F-19 — retired demosite/ tree stays gone (absence lock)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestF19DemositeAbsent(unittest.TestCase):
    def test_demosite_directory_absent(self):
        self.assertFalse(
            (ROOT / "demosite").exists(),
            "demosite/ must remain deleted (F-19)",
        )

    def test_no_demosite_python_modules(self):
        hits = list(ROOT.glob("demosite/**/*.py"))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
