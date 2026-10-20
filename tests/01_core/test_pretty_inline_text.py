"""Pretty render keeps the displayed text of mixed content (#79).

A pretty newline next to text shows as a space in a browser, so an element
whose children mix text with other nodes renders them flat. The browser check
is ``tests/06_browser/test_pretty_inner_text_browser.py``.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from ux_dom import Fragment
from ux_dom.dom import b, div, lazy, li, p, pre, script, span, style, textarea, ul
from ux_dom.dom.src import ext


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

    def test_lazy_counts_as_text(self):
        # Its result is unknown until it renders, so its parent renders flat.
        self.assertPretty(p(b("x"), lazy(lambda: "y")), "<p><b>x</b>y</p>")
        self.assertPretty(
            div(lazy(lambda: span("a")), lazy(lambda: "b&c")),
            "<div><span>a</span>b&amp;c</div>",
        )
        self.assertPretty(p("a", lazy(lambda: b("x")), "c"), "<p>a<b>x</b>c</p>")

    def test_mixed_content_check_is_linear_in_wrapper_depth(self):
        depth = 200
        node = p("x")
        for _ in range(depth):
            node = Fragment(p("x"), node)
        real, calls = ext._shows_text, []

        def counting(*args):
            calls.append(1)
            return real(*args)

        with mock.patch.object(ext, "_shows_text", counting):
            str(node)
        # About 4 per level; a re-walk of every subtree is about depth**2.
        self.assertLess(len(calls), 8 * depth)

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
