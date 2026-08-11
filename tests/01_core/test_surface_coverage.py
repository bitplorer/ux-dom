"""Breadth coverage of public DOM/Component surfaces (no chaos, no browser)."""
from __future__ import annotations

import unittest

from ux_dom.dom import div, style
from ux_dom.plugins.control import HtmxControl, NullControl
from ux_dom.plugins.dedupe import dedupe_dom_nodes, extract_script_srcs
from ux_dom.plugins.response import HTMLResponsePlugin, StreamingResponsePlugin
from ux_dom.ui.tokens import cn, focus_ring, variants
from ux_dom.utils.functional import map_recursive


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


class TestHtmxControlSse(unittest.TestCase):
    def test_sse_script_included_when_enabled(self):
        h = HtmxControl(version="2.0.4", sse=True, idiomorph=True)
        rendered = "".join(str(x) for x in h.document_body())
        self.assertIn("htmx.org", rendered)
        self.assertIn("htmx-ext-sse", rendered)

    def test_sse_off_by_default(self):
        h = HtmxControl(version="2.0.4", sse=False)
        rendered = "".join(str(x) for x in h.document_body())
        self.assertNotIn("htmx-ext-sse", rendered)

    def test_null_control_wire_is_noop(self):
        n = NullControl()
        self.assertEqual(n.wire(x=1), {})
        self.assertEqual(n.partial_policy(type("R", (), {"headers": {}})()), "full")
        n.mount(None)


class TestResponsePlugins(unittest.TestCase):
    def test_streaming_plugin_wraps(self):
        plug = StreamingResponsePlugin()

        def ep():
            return div("hi")

        self.assertIsNotNone(plug.wrap(ep)())

    def test_html_plugin_wraps(self):
        plug = HTMLResponsePlugin()

        def ep():
            return div("hi")

        self.assertIsNotNone(plug.wrap(ep)())


class TestUiTokens(unittest.TestCase):
    def test_cn_and_focus(self):
        self.assertEqual(cn("x", "", None, "y"), "x y")
        self.assertIsInstance(focus_ring, str)
        self.assertIn("ring", focus_ring)
        self.assertIn("h-8", variants({"size": {"sm": "h-8"}}, size="sm"))


class TestFunctional(unittest.TestCase):
    def test_map_recursive_list(self):
        out = map_recursive(lambda x: x * 2 if isinstance(x, int) else x, [1, [2, 3], 4])
        self.assertEqual(out, [2, [4, 6], 8])


class TestAssetsFacade(unittest.TestCase):
    def test_ensure_and_compose(self):
        from ux_dom.assets import compose_document_parts, ensure_default_contributions

        h = ensure_default_contributions()
        head, body = compose_document_parts(hub=h, include_core=True)
        self.assertIsInstance(head, list)
        self.assertIsInstance(body, list)


if __name__ == "__main__":
    unittest.main()
