"""Dead surface stays gone (ux-dom is unpublished, so removed with no shims)."""
from __future__ import annotations

import inspect
import unittest


class DeadSurfaceRemoved(unittest.TestCase):
    def test_app_web_tombstone_removed(self):
        from ux_dom.plugins.hub import App

        self.assertFalse(hasattr(App, "web"))

    def test_assets_compat_facade_removed(self):
        import importlib.util

        self.assertIsNone(importlib.util.find_spec("ux_dom.assets"))

    def test_sync_runtime_assets_has_no_ignored_params(self):
        from ux_dom.cli.static_assets import sync_runtime_assets

        params = inspect.signature(sync_runtime_assets).parameters
        self.assertNotIn("vendor", params)
        self.assertNotIn("force", params)


if __name__ == "__main__":
    unittest.main()


def test_css_tags_removed():
    """csstags/StyleTags rendered broken CSS and had no users (review M7)."""
    import importlib

    import pytest

    import ux_dom.dom.src.ext as ext

    assert not hasattr(ext, "StyleTags")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ux_dom.dom.src.csstags")
