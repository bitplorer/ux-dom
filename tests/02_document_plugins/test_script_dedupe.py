"""Script double-injection prevention."""

from __future__ import annotations

import unittest

from ux_dom.dom import script
from ux_dom.plugins import App, XElementRuntime, shell_fragments
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.dedupe import dedupe_dom_nodes, extract_script_srcs, resource_key
from ux_dom.plugins.hub import PluginHub
from ux_dom.plugins.runtime import XELEMENT_JS_URL


class TestDedupeHelpers(unittest.TestCase):
    def test_resource_key_script(self):
        n = script(src=XELEMENT_JS_URL, defer=True)
        self.assertEqual(resource_key(n), XELEMENT_JS_URL)

    def test_dedupe_keeps_first(self):
        a = script(src="/a.js")
        b = script(src="/a.js")  # duplicate
        c = script(src="/b.js")
        out = dedupe_dom_nodes([a, b, c])
        self.assertEqual(len(out), 2)
        self.assertEqual(extract_script_srcs(*out), ["/a.js", "/b.js"])

    def test_inline_not_deduped_away(self):
        inline = script("console.log(1)")
        out = dedupe_dom_nodes([inline, inline])
        # no src → both kept (inline cannot key); acceptable
        self.assertEqual(len(out), 2)

    def test_raw_html_string_dedupe(self):
        s1 = '<script src="/ux-channel/static/ux-channel.js" defer></script>'
        s2 = '<script defer src="/ux-channel/static/ux-channel.js"></script>'
        out = dedupe_dom_nodes([s1, s2])
        self.assertEqual(len(out), 1)


class TestHubShellDedupe(unittest.TestCase):
    def test_double_xelement_contribution_name_overwrites(self):
        """Same plugin name → last wins; still one tag."""
        hub = PluginHub()
        hub.add_contribution(XElementRuntime())
        hub.add_contribution(XElementRuntime())  # same name overwrites
        head, _ = hub.shell_fragments()
        srcs = extract_script_srcs(*head)
        self.assertEqual(srcs.count(XELEMENT_JS_URL), 1)

    def test_shell_fragments_dedupe_extra(self):
        hub = PluginHub()
        hub.add_contribution(XElementRuntime())
        # extras that re-add same runtime
        head, body = shell_fragments(
            hub,
            script(src=XELEMENT_JS_URL, defer=True),
            extra_body=[script(src="https://unpkg.com/htmx.org@2.0.4")],
        )
        srcs = extract_script_srcs(*head, *body)
        self.assertEqual(srcs.count(XELEMENT_JS_URL), 1)

    def test_app_use_order_single_each(self):
        builder = (
            App().use(XElementRuntime()).use(HtmxControl(cdn=True, version="2.0.4"))
        )
        head, body = builder.shell_fragments()
        srcs = extract_script_srcs(*head, *body)
        self.assertEqual(srcs.count(XELEMENT_JS_URL), 1)
        htmx = [s for s in srcs if "htmx.org" in s]
        self.assertEqual(len(htmx), 1)


if __name__ == "__main__":
    unittest.main()
