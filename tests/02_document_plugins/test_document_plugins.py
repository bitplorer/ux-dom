"""Document head/body demarcation + App hub merge."""

from __future__ import annotations

import unittest

from ux_dom import Document
from ux_dom.dom import meta, title
from ux_dom.plugins import App
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XELEMENT_JS_URL


class TestDocumentPluginMerge(unittest.TestCase):
    def test_plugins_go_to_head_and_body(self):
        set_hub(PluginHub())
        App().xelement().htmx(cdn=True, version="2.0.4")  # no build needed for hub
        # manually publish hub — App.use already on builder.hub but get_hub empty
        # use builder.hub
        b = App().xelement().htmx(cdn=True, version="2.0.4")
        set_hub(b.hub)

        doc = Document(
            head=[meta(charset="utf-8"), title("T")],
            body=[],
            include_runtimes=True,
        )
        ph, pb = doc.plugin_head_body()
        head_html = "".join(str(x) for x in doc.resolved_head())
        body_html = "".join(str(x) for x in doc.resolved_body())
        self.assertIn(XELEMENT_JS_URL, head_html)
        self.assertIn("htmx.org", body_html)
        # page content path
        tree = doc("hello")
        html = str(tree)
        self.assertIn(XELEMENT_JS_URL, html)
        self.assertIn("htmx.org", html)

    def test_plugins_false_pure_shell(self):
        b = App().xelement()
        set_hub(b.hub)
        doc = Document(head=[title("X")], include_runtimes=False)
        self.assertEqual(doc.plugin_head_body(), ([], []))
        self.assertNotIn("x_element", "".join(str(x) for x in doc.resolved_head()))


if __name__ == "__main__":
    unittest.main()
