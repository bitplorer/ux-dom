"""uxdom build — single-copy package static."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.cli.static_assets import sync_runtime_assets
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XElementRuntime
from ux_dom.scripts import x_element_js_text


class TestStaticSync(unittest.TestCase):
    def test_sync_records_package_mount_not_dual_file(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "app").mkdir()
            hub = PluginHub()
            hub.add_contribution(XElementRuntime())
            set_hub(hub)
            rep = sync_runtime_assets(root, hub=hub)
            self.assertTrue(rep.ok)
            self.assertTrue(any("/ux-dom/static" in m[0] for m in rep.mounts))
            # no dual copy into assets
            self.assertFalse((root / "assets/js/x_element.js").exists())
            self.assertTrue(x_element_js_text())


if __name__ == "__main__":
    unittest.main()
