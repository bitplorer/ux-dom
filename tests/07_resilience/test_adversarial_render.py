"""ADV — adversarial attributes, path, and script surfaces on the render path."""
from __future__ import annotations

import unittest
from html.parser import HTMLParser

from ux_dom.dom import a, div, script


class TestAttrBreakout(unittest.TestCase):
    def test_attribute_quote_breakout_escaped(self):
        evil = '"><img src=x onerror=alert(1)>'
        html = div(title=evil, **{"data-x": evil}).__render__(pretty=False)
        # The payload must stay inert text inside the quoted value: parse the
        # output and require exactly one element (the div) whose attribute
        # values round-trip to the payload. A substring check for "onerror="
        # is wrong here; it appears legitimately as escaped attribute text.
        tags = []

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                tags.append((tag, dict(attrs)))

        P().feed(html)
        self.assertEqual([t for t, _ in tags], ["div"])
        self.assertEqual(tags[0][1], {"title": evil, "data-x": evil})
        self.assertNotIn("<img", html)

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
