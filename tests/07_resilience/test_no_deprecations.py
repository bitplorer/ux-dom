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
    def test_serve_modes_removed(self):
        # webassets alias (0.2.0), then dual_copy (#109): package mount is the only path.
        from ux_dom.plugins import package_static, runtime

        for mod in (package_static, runtime):
            self.assertFalse(hasattr(mod, "ServeMode"))
        for mode in ("webassets", "dual_copy", "package_mount"):
            with self.assertRaises(TypeError):
                runtime.XElementRuntime(serve=mode)
            with self.assertRaises(TypeError):
                package_static.PackageStaticContribution(name="x", files=(), serve=mode)
            with self.assertRaises(TypeError):
                package_static.static_from_package("x", "ux_dom.scripts", [], serve=mode)

    def test_carousel_default_alias_removed(self):
        from ux_dom.ui.carousel import Carousel

        self.assertNotIn("default", inspect.signature(Carousel.render).parameters)


if __name__ == "__main__":
    unittest.main()
