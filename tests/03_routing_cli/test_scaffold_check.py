"""Product scaffold integrity lives on uxcompose; its ux-dom modules are gone."""

from __future__ import annotations

import unittest


class TestProductScaffoldMoved(unittest.TestCase):
    def test_cli_scaffold_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.scaffold  # noqa: F401

    def test_scaffold_check_module_gone(self):
        with self.assertRaises(ImportError):
            from ux_dom.cli.scaffold_check import assert_scaffold_ok  # noqa: F401


if __name__ == "__main__":
    unittest.main()
