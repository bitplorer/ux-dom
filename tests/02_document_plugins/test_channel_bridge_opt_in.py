"""``ux-bridge.js`` ships only when the app opts in (``bridge=True``)."""

from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

from ux_dom import Channel, Document
from ux_dom.dom import title
from ux_dom.plugins.package_static import ux_channel_static

BRIDGE_JS = "/ux-channel/static/ux-bridge.js"
CHANNEL_JS = "/ux-channel/static/ux-channel.js"


def _page(*runtimes) -> str:
    return str(Document(head=[title("T")]).use(*runtimes)("hi"))


class TestBridgeOptIn(unittest.TestCase):
    def test_default_page_has_no_bridge(self):
        html = _page(ux_channel_static())
        self.assertIn(CHANNEL_JS, html)
        self.assertNotIn("ux-bridge.js", html)

    def test_opted_in_page_has_bridge(self):
        self.assertIn(BRIDGE_JS, _page(ux_channel_static(bridge=True)))

    def test_channel_runtime_defaults_off(self):
        with mock.patch.dict(sys.modules, {"ux_channel": types.ModuleType("ux_channel")}):
            self.assertNotIn("ux-bridge.js", _page(Channel()))
            self.assertIn(BRIDGE_JS, _page(Channel(bridge=True)))


if __name__ == "__main__":
    unittest.main()
