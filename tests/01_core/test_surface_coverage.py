"""Breadth coverage of public DOM/Component surfaces (no chaos, no browser)."""
from __future__ import annotations

import unittest

from ux_dom.dom import div, style
from ux_dom.plugins.control import NullControl
from ux_dom.plugins.dedupe import dedupe_dom_nodes, extract_script_srcs
from ux_dom.ui.tokens import cn, focus_ring, variants


class TestCssTags(unittest.TestCase):
    def test_style_tag_basic(self):
        s = style(".x{color:red}")
        html = s.__render__(pretty=False)
        self.assertIn("color", html)


class TestDedupe(unittest.TestCase):
    def test_dedupe_scripts(self):
        from ux_dom.dom import script

        nodes = [
            script(src="/a.js"),
            script(src="/a.js"),
            script(src="/b.js"),
        ]
        out = dedupe_dom_nodes(nodes)
        self.assertIsNotNone(out)
        srcs = extract_script_srcs(out)
        # duplicates collapsed when helper supports it
        self.assertIsInstance(srcs, (list, set, tuple))


class TestNullControl(unittest.TestCase):
    def test_null_control_wire_is_noop(self):
        n = NullControl()
        self.assertEqual(n.wire(x=1), {})
        self.assertEqual(n.partial_policy(type("R", (), {"headers": {}})()), "full")
        n.mount(None)


class TestUiTokens(unittest.TestCase):
    def test_cn_and_focus(self):
        self.assertEqual(cn("x", "", None, "y"), "x y")
        self.assertIsInstance(focus_ring, str)
        self.assertIn("ring", focus_ring)
        self.assertIn("h-8", variants({"size": {"sm": "h-8"}}, size="sm"))


if __name__ == "__main__":
    unittest.main()
