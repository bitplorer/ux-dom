"""Product CSS is not on ux-dom. Compiler is uxcompose build."""
from __future__ import annotations

import unittest


class TestTailwindCommandAbsent(unittest.TestCase):
    def test_not_a_public_export(self):
        import ux_dom

        self.assertFalse(hasattr(ux_dom, "TailwindCommand"))
        with self.assertRaises(ImportError):
            import ux_dom.settings.commands  # noqa: F401


class TestTailwindStyleAbsent(unittest.TestCase):
    def test_only_null_style(self):
        from ux_dom.plugins import style

        self.assertFalse(hasattr(style, "TailwindStyle"))
        self.assertTrue(callable(style.NullStyle))


class TestCliTailwindAbsent(unittest.TestCase):
    def test_module_is_gone(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.tailwind  # noqa: F401


if __name__ == "__main__":
    unittest.main()
