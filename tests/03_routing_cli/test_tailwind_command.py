"""TailwindCommand / TailwindStyle fail closed — compiler is uxcompose build."""
from __future__ import annotations

import unittest
from pathlib import Path

from ux_dom import TailwindCommand
from ux_dom.settings.commands import ProductCssMoved


class TestTailwindCommandFailClosed(unittest.TestCase):
    def test_construct_teaches_uxcompose_build(self):
        with self.assertRaises(ProductCssMoved) as ctx:
            TailwindCommand()
        msg = str(ctx.exception).lower()
        self.assertIn("uxcompose build", msg)
        self.assertIn("classname", msg)

    def test_public_import_still_resolves(self):
        from ux_dom.settings.commands import TailwindCommand as TC

        self.assertIs(TC, TailwindCommand)


class TestTailwindStyleFailClosed(unittest.TestCase):
    def test_construct_teaches_uxcompose_build(self):
        from ux_dom.plugins.style import TailwindStyle

        with self.assertRaises(ProductCssMoved) as ctx:
            TailwindStyle(webassets=None)
        self.assertIn("uxcompose build", str(ctx.exception))


class TestCliTailwindFailClosed(unittest.TestCase):
    def test_discover_css_io_teaches_compose(self):
        from ux_dom.cli import tailwind as tw

        with self.assertRaises(ImportError) as ctx:
            tw.discover_css_io(Path("."))
        self.assertIn("uxcompose build", str(ctx.exception).lower())
        self.assertIn("ux_compose.tailwind", str(ctx.exception))

    def test_module_does_not_download(self):
        from pathlib import Path as P

        src = (
            P(__file__).resolve().parents[2]
            / "src"
            / "ux_dom"
            / "cli"
            / "tailwind.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("_download_standalone", src)
        self.assertNotIn("npx --yes", src)
        self.assertNotIn("def resolve_tailwind", src)
        self.assertIn("fail", src.lower())


if __name__ == "__main__":
    unittest.main()
