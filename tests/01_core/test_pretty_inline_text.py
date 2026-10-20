"""Pretty render keeps the displayed text (#79, #89).

A pretty newline between two inline nodes (text, ``<b>``, unknown tags) shows
as a space in a browser, so they render flat; a newline next to a block sits
at a line edge, where the browser drops it. The browser check is
``tests/06_browser/test_pretty_inner_text_browser.py``.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from ux_dom import Fragment
from ux_dom.dom import (
    Var,
    a,
    b,
    body,
    comment,
    dd,
    div,
    head,
    header,
    hr,
    html,
    i,
    lazy,
    li,
    meta,
    option,
    p,
    pre,
    q,
    ruby,
    script,
    span,
    style,
    table,
    tbody,
    td,
    textarea,
    tr,
    ul,
)
from ux_dom.dom.src import ext
from ux_dom.dom.src.htmltags import html_tag

dialog = type("dialog", (html_tag,), {})
nobr = type("nobr", (html_tag,), {})


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

    def test_adjacent_inline_elements_stay_inline(self):
        self.assertPretty(div(b("a"), i("b")), "<div><b>a</b><i>b</i></div>")
        self.assertPretty(Fragment("<b>a</b><i>b</i>"), "<b>a</b><i>b</i>")
        self.assertPretty(
            div(b("a"), comment("c"), i("b")), "<div><b>a</b><!-- c --><i>b</i></div>"
        )
        # An empty wrapper between them does not separate them.
        self.assertPretty(
            div(Fragment(b("a")), Fragment(), i("b")), "<div><b>a</b><i>b</i></div>"
        )
        self.assertPretty(p("a", Var("x")), "<p>a{{ x }}</p>")

    def test_phrasing_content_is_inline(self):
        # HTML spec, "Phrasing content". Unknown and custom tags too.
        phrasing = """a abbr area audio b bdi bdo br button canvas cite code
            data datalist del dfn em embed i iframe img input ins kbd label link
            map mark math meta meter noscript object output picture progress q
            ruby s samp script select slot small span strong sub sup svg
            template textarea time u var video wbr my-widget x-y""".split()
        for name in phrasing:
            with self.subTest(name=name):
                self.assertNotIn(name, ext._BLOCK_ELEMENTS)

    def test_inline_element_edges_stay_inline(self):
        # ``<q>`` draws quotes inside its edges: ``<q> x </q>`` shows the spaces.
        self.assertPretty(q("x"), "<q>x</q>")
        self.assertPretty(div(a()), "<div>\n  <a></a>\n</div>")
        self.assertPretty(p(span(b("x"))), "<p>\n  <span><b>x</b></span>\n</p>")

    def test_block_neighbours_keep_their_layout(self):
        self.assertPretty(
            div(b("a"), p("x"), i("b")),
            "<div>\n  <b>a</b>\n  <p>\n    x\n  </p>\n  <i>b</i>\n</div>",
        )
        self.assertPretty(
            div("text", p("x")), "<div>\n  text\n  <p>\n    x\n  </p>\n</div>"
        )
        self.assertPretty(
            a(div("x"), div("y")),
            "<a>\n  <div>\n    x\n  </div>\n  <div>\n    y\n  </div>\n</a>",
        )
        self.assertPretty(
            table(tbody(tr(td("a"), td("b")))),
            "<table>\n  <tbody>\n    <tr>\n      <td>\n        a\n      </td>"
            "\n      <td>\n        b\n      </td>\n    </tr>\n  </tbody>\n</table>",
        )
        # Nothing in <head> is displayed.
        self.assertPretty(
            html(head(meta(charset="utf-8"), script("x")), body(p("y"))),
            '<html>\n  <head>\n    <meta charset="utf-8">\n    <script>x</script>'
            "\n  </head>\n  <body>\n    <p>\n      y\n    </p>\n  </body>\n</html>",
        )

    def test_elements_the_parser_moves_render_flat(self):
        # The parser closes the outer <li> / <p> early, or drops a <td> outside
        # a table, and the tail lands next to the siblings.
        self.assertPretty(div(li(li(), "y"), "x"), "<div><li><li></li>y</li>x</div>")
        self.assertPretty(div("x", p(div("y"))), "<div>x<p><div>y</div></p></div>")
        self.assertPretty(div(td("1"), "w"), "<div><td>1</td>w</div>")
        self.assertPretty(
            table(tbody(tr(td("a"))), "x"),
            "<table><tbody><tr><td>a</td></tr></tbody>x</table>",
        )
        # <dialog> closes a <p>; an <a> or <nobr> closes the one it is in.
        self.assertPretty(
            div(p("a", dialog("b")), "c"), "<div><p>a<dialog>b</dialog></p>c</div>"
        )
        self.assertPretty(
            nobr(div("a"), nobr(), div("b")),
            "<nobr><div>a</div><nobr></nobr><div>b</div></nobr>",
        )
        # A table part in a cell closes it; the tail lands in front of the table.
        self.assertPretty(
            div("x", table(tbody(tr(td(tbody("y")))))),
            "<div>x<table><tbody><tr><td><tbody>y</tbody></td></tr></tbody>"
            "</table></div>",
        )
        # Below the top of the document the parser drops <html>/<head>/<body>.
        self.assertPretty(div("x", body("y")), "<div>x<body>y</body></div>")
        self.assertPretty(div(html("x"), "y"), "<div><html>x</html>y</div>")
        self.assertPretty(div(head("x", "y")), "<div>\n  <head>xy</head>\n</div>")
        # A void element writes no end tag, so its children follow it.
        self.assertPretty(div(hr("x"), "y"), "<div><hr>xy</div>")
        # A nested list ends the search for a nested <li>.
        self.assertPretty(
            li(ul(li("a"))),
            "<li>\n  <ul>\n    <li>\n      a\n    </li>\n  </ul>\n</li>",
        )

    def test_option_and_ruby_bodies_render_flat(self):
        # An <option> shows its label, which joins its text with one space per
        # whitespace run, and <ruby> lays out everything in it inline (#94).
        self.assertPretty(
            div(option(dd(header("a"), "b"))),
            "<div>\n  <option><dd><header>a</header>b</dd></option>\n</div>",
        )
        self.assertPretty(
            div(ruby(div("a"), div("b"))),
            "<div>\n  <ruby><div>a</div><div>b</div></ruby>\n</div>",
        )

    def test_layout_check_is_linear(self):
        depth = 200
        wrappers, elements, lists = p("x"), "x", b("x")
        for _ in range(depth):
            wrappers = Fragment(p("x"), wrappers)
            elements = div(elements, p("z"))
            lists = li(span("y"), lists)
        for node in (wrappers, elements, lists):
            real, calls = ext._scan, []

            def counting(*args):
                calls.append(1)
                return real(*args)

            with self.subTest(node=type(node).__name__):
                with mock.patch.object(ext, "_scan", counting):
                    str(node)
                # At most 8 per level; a re-walk of every subtree is depth**2.
                self.assertLess(len(calls), 12 * depth)

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
