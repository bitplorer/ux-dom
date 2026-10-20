"""Pretty render keeps the displayed text of mixed content (#79).

A pretty newline next to text shows as a space in a browser, so an element
whose children mix text with other nodes renders them flat. The browser check
is ``tests/06_browser/test_pretty_inner_text_browser.py``.
"""

from __future__ import annotations

import asyncio
import unittest

from ux_dom import Fragment
from ux_dom.dom import b, div, li, p, pre, script, style, textarea, ul


class TestPrettyInlineText(unittest.TestCase):
    def assertPretty(self, node, expected):
        self.assertEqual(str(node), expected)
        self.assertEqual(node.__render__(pretty=True), expected)

    def test_reference_between_text_stays_inline(self):
        self.assertPretty(Fragment("a&#39;b"), "a&#39;b")

    def test_unknown_entity_stays_inline(self):
        self.assertPretty(Fragment("<p>AT&T x</p>"), "<p>AT&amp;T x</p>")

    def test_text_around_inline_elements_stays_inline(self):
        self.assertPretty(
            Fragment('<p>hello <b>world</b>, see <a href="/x">link</a>.</p>'),
            '<p>hello <b>world</b>, see <a href="/x">link</a>.</p>',
        )
        self.assertPretty(p("a", b("x"), "y"), "<p>a<b>x</b>y</p>")

    def test_element_only_parents_keep_their_layout(self):
        self.assertPretty(
            Fragment("<ul><li>one &lt;two&gt;</li><li>a<em>b</em>c</li></ul>"),
            "<ul>\n  <li>one &lt;two&gt;</li>\n  <li>a<em>b</em>c</li>\n</ul>",
        )
        self.assertPretty(
            div(p("x", b("y")), p("z")),
            "<div>\n  <p>x<b>y</b></p>\n  <p>\n    z\n  </p>\n</div>",
        )
        self.assertPretty(ul(li("one")), "<ul>\n  <li>\n    one\n  </li>\n</ul>")

    def test_whitespace_sensitive_elements_render_verbatim(self):
        for node in (
            pre("a\n  b", b("x"), "c"),
            textarea("a\n b"),
            style("a{}", "b{}"),
            script("a", "b"),
        ):
            with self.subTest(node=node.__render__(pretty=False)):
                self.assertEqual(str(node), node.__render__(pretty=False))

    def test_async_pretty_matches_sync(self):
        node = Fragment("<div><p>a&#39;b <i>c</i>d</p><p>e</p></div>")

        async def run():
            return "".join([t async for t in node.__async_render__(pretty=True)])

        self.assertEqual(asyncio.run(run()), str(node))
        self.assertEqual(
            str(node), "<div>\n  <p>a&#39;b <i>c</i>d</p>\n  <p>\n    e\n  </p>\n</div>"
        )


if __name__ == "__main__":
    unittest.main()
