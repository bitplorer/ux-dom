"""ADV — adversarial attributes, path, and script surfaces on the render path."""
from __future__ import annotations

import unittest

from ux_dom.dom import a, div, script


class TestAttrBreakout(unittest.TestCase):
    def test_attribute_quote_breakout_escaped(self):
        evil = '"><img src=x onerror=alert(1)>'
        html = div(title=evil, **{"data-x": evil}).__render__(pretty=False)
        self.assertNotIn("<img", html)
        self.assertNotIn("onerror=", html)

    def test_javascript_href_not_raw(self):
        html = a("x", href="javascript:alert(1)").__render__(pretty=False)
        # must not emit an executable javascript: handler as trusted navigation
        # (policy may escape, strip, or neutralize — never raw open handler)
        self.assertTrue(
            "javascript:alert" not in html
            or "&" in html
            or "&#" in html
            or html.count("javascript:") == 0,
            html,
        )


class TestScriptSurface(unittest.TestCase):
    def test_user_text_not_in_script_context_unescaped(self):
        evil = "</script><script>alert(1)</script>"
        html = div(evil).__render__(pretty=False)
        self.assertNotIn("</script><script>", html)
