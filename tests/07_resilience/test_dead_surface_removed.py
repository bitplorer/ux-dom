"""Dead surface stays gone (ux-dom is unpublished, so removed with no shims)."""
from __future__ import annotations

import unittest


class DeadSurfaceRemoved(unittest.TestCase):
    def test_app_web_tombstone_removed(self):
        from ux_dom.plugins.hub import App

        self.assertFalse(hasattr(App, "web"))

    def test_assets_compat_facade_removed(self):
        import importlib.util

        self.assertIsNone(importlib.util.find_spec("ux_dom.assets"))

    def test_asset_writers_removed_with_uxdom_build(self):
        # Their only callers were ux_dom.cli.build / static_assets (#109).
        from ux_dom.plugins import hub

        for name in ("materialize", "served_static_files", "all_artifacts"):
            self.assertFalse(hasattr(hub.PluginHub, name), name)
        self.assertFalse(hasattr(hub.App, "materialize_assets"))
        self.assertFalse(hasattr(hub, "MaterializeReport"))
        self.assertFalse(hasattr(hub, "MaterializedFile"))
        from ux_dom.plugins.contribution import StaticArtifact

        self.assertFalse(hasattr(StaticArtifact, "bytes"))

    def test_package_dir_removed(self):
        # Its only caller was a test (#111).
        from ux_dom.plugins import package_static

        self.assertFalse(hasattr(package_static, "package_dir"))


if __name__ == "__main__":
    unittest.main()
