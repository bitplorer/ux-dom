"""Lock: deprecated modules and aliases are removed (chore/remove-deprecations).

ux-dom was never published to PyPI, so these paths protect nobody.
"""

import importlib
import inspect
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "ux_dom"


class TestDeprecatedModulesRemoved(unittest.TestCase):
    def test_modules_absent(self):
        for rel, mod in (
            ("dom/src/pythontags.py", "ux_dom.dom.src.pythontags"),
            ("dom/src/sphinxtags.py", "ux_dom.dom.src.sphinxtags"),
            ("alpinejs/ripple_btn.py", "ux_dom.alpinejs.ripple_btn"),
            ("dom/ui.py", "ux_dom.dom.ui"),
        ):
            with self.subTest(mod=mod):
                self.assertFalse((SRC / rel).exists())
                with self.assertRaises(ModuleNotFoundError):
                    importlib.import_module(mod)


class TestDeprecatedAliasesRemoved(unittest.TestCase):
    def test_webassets_serve_alias_rejected(self):
        from ux_dom.plugins import package_static, runtime

        for mod in (package_static, runtime):
            self.assertNotIn("webassets", mod.ServeMode.__args__)
        with self.assertRaises(ValueError):
            runtime.XElementRuntime(serve="webassets")
        with self.assertRaises(ValueError):
            package_static.PackageStaticContribution(
                name="x", files=(), serve="webassets"
            )

    def test_carousel_default_alias_removed(self):
        from ux_dom.ui.carousel import Carousel

        self.assertNotIn("default", inspect.signature(Carousel.render).parameters)


if __name__ == "__main__":
    unittest.main()
