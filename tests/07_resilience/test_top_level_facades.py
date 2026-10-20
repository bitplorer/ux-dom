"""Top-level Document facades are the ``ux_dom.plugins`` classes (no wrapper layer)."""
from __future__ import annotations

import unittest


class TestTopLevelFacades(unittest.TestCase):
    def test_top_level_facades_alias_plugins(self):
        import ux_dom
        from ux_dom.plugins.control import HtmxControl
        from ux_dom.plugins.csp import Csp
        from ux_dom.plugins.runtime import UxChannelRuntime, XElementRuntime

        self.assertIs(ux_dom.XElement, XElementRuntime)
        self.assertIs(ux_dom.Htmx, HtmxControl)
        self.assertIs(ux_dom.Csp, Csp)
        self.assertIs(ux_dom.Channel, UxChannelRuntime)


if __name__ == "__main__":
    unittest.main()
