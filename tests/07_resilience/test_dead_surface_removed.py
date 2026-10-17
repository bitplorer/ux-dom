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


def test_unsafe_dom_util_helpers_removed():
    # system() ran shell=True, include() read files as raw HTML and
    # lazy() rendered unescaped; none had a consumer.
    import ux_dom.dom as dom
    from ux_dom.dom.src.utils import dom_util

    removed = (
        "system", "include", "lazy", "unescape", "url_escape", "url_unescape",
    )
    for name in removed:
        assert not hasattr(dom_util, name), name
        assert not hasattr(dom, name), name


def test_import_time_icon_trees_removed():
    import importlib.util

    assert importlib.util.find_spec("ux_dom.dom.icons") is None


def test_top_level_all_is_importable():
    import ux_dom

    for name in ux_dom.__all__:
        assert hasattr(ux_dom, name), name
