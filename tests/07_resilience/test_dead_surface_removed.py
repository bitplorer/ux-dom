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


if __name__ == "__main__":
    unittest.main()
