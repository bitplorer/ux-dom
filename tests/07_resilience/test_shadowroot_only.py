"""``shadowroot`` is the only shadow attribute; x_element.js has no ``ws_send`` branch."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ux_dom
from ux_dom.cli.lint import lint_project
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import WebComponent

X_ELEMENT_JS = Path(ux_dom.__file__).parent / "scripts" / "x_element.js"


class TestShadowrootOnly(unittest.TestCase):
    def test_webcomponent_with_only_shadowdom_is_missing_shadowroot(self):
        class OnlyShadowdom(WebComponent):
            def render(self, tag_name):
                return template(div("x"), **{"x-tagname": tag_name, "shadowdom": "open"})

        with self.assertRaises(AttributeError) as ctx:
            OnlyShadowdom("only-sd")
        msg = str(ctx.exception)
        self.assertIn("requires 'shadowroot'", msg)
        self.assertNotIn("shadowdom'", msg)

    def test_lint_warns_on_webcomponent_with_only_shadowdom(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "app").mkdir()
            (Path(tmp) / "app" / "wc.py").write_text(
                "class W(WebComponent):\n    attrs = {'shadowdom': 'open'}\n",
                encoding="utf-8",
            )
            messages = [i.message for i in lint_project(Path(tmp))]
        self.assertIn(
            "WebComponent subclass should set shadowroot on definition template", messages
        )

    def test_runtime_reads_no_synonym_or_ws_send(self):
        js = X_ELEMENT_JS.read_text(encoding="utf-8")
        self.assertNotIn("shadowdom", js)
        self.assertNotIn("ws_send", js)


if __name__ == "__main__":
    unittest.main()
