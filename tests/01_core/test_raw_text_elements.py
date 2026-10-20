"""<script> / <style> are raw text elements (HTML spec §13.1.2).

Their string children render verbatim (the browser never entity-decodes them),
and only sequences that could end the element early are neutralized:
``</script`` / ``</style`` (any case) and, in script, ``<!--``.
"""
from __future__ import annotations

import asyncio
import json
import re
import unittest

from ux_dom import Component
from ux_dom.dom import div, raw, script, span, style, textarea, title
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.src.utils.dom_util import neutralize_raw_text
from ux_dom.plugins.csp import stamp_nonce, stamp_tree

JS = 'if (a < b && c > d) { s = "<b>" + \'&amp;\'; }'
CSS = 'a > b::after { content: "&<"; } p ~ q { color: red }'


def _async(node, **kw):
    async def go():
        return "".join([t async for t in node.__async_render__(**kw)])

    return asyncio.run(go())


def _end_tags(html, name):
    return [m.start() for m in re.finditer(r"</%s" % name, html, re.I)]


class TestVerbatim(unittest.TestCase):
    def test_script_js_verbatim(self):
        self.assertEqual(script(JS).__render__(pretty=False), f"<script>{JS}</script>")

    def test_style_css_verbatim(self):
        self.assertEqual(style(CSS).__render__(pretty=False), f"<style>{CSS}</style>")

    def test_spec_example(self):
        self.assertEqual(
            script("a < b && c").__render__(pretty=False), "<script>a < b && c</script>"
        )

    def test_other_elements_still_escaped(self):
        self.assertEqual(div("a<b").__render__(pretty=False), "<div>a&lt;b</div>")
        # escapable raw text elements: entities ARE decoded, so escaping stays
        self.assertIn("a&lt;/title&gt;", title("a</title>").__render__(pretty=False))
        self.assertIn("&lt;/textarea&gt;", textarea("</textarea>").__render__(pretty=False))

    def test_multiple_children_and_add(self):
        s = script("var a = 1 < 2;")
        s.add(" var b = a && true;")
        self.assertEqual(
            s.__render__(pretty=False), "<script>var a = 1 < 2; var b = a && true;</script>"
        )


class TestBreakout(unittest.TestCase):
    PAYLOADS = [
        'x="</script><img src=x onerror=alert(1)>"',
        "</SCRIPT >alert(1)",
        "</ScRiPt\n>alert(1)",
        "</script/x>",
        "<!--<script>alert(1)</script>-->",
        "a</scriptx",
    ]

    def test_script_cannot_be_closed_by_text(self):
        for p in self.PAYLOADS:
            with self.subTest(p=p):
                html = script(p).__render__(pretty=False)
                ends = _end_tags(html, "script")
                self.assertEqual(ends, [len(html) - len("</script>")], html)
                self.assertNotIn("<!--", html)
                self.assertTrue(html.startswith("<script>"))

    def test_neutralized_forms(self):
        self.assertEqual(neutralize_raw_text("</ScRiPt>", "script"), "<\\/ScRiPt>")
        self.assertEqual(neutralize_raw_text("a<!--b", "script"), "a\\u003C!--b")
        self.assertEqual(neutralize_raw_text("</STYLE>", "style"), "<\\/STYLE>")
        # style has no escaped states: <!-- and </script are left alone
        self.assertEqual(neutralize_raw_text("<!--</script>", "style"), "<!--</script>")
        self.assertEqual(neutralize_raw_text("</style>", "script"), "</style>")

    def test_style_cannot_be_closed_by_text(self):
        for p in ("</style><script>alert(1)</script>", "</STYLE\t>x", "</style/"):
            with self.subTest(p=p):
                html = style(p).__render__(pretty=False)
                self.assertEqual(_end_tags(html, "style"), [len(html) - len("</style>")])

    def test_breakout_inside_nested_tree_and_pretty(self):
        page = div(script("</script><b>x</b>"), span("ok"))
        for pretty in (False, True):
            html = page.__render__(pretty=pretty)
            self.assertEqual(len(_end_tags(html, "script")), 1)
            self.assertIn("<span>", html)

    def test_escape_string_false_still_neutralized(self):
        s = script("</script>", __escape_string=False)
        self.assertEqual(s.__render__(pretty=False), "<script><\\/script></script>")


def _all_modes(node):
    """(label, html) for sync/async x pretty/compact."""
    out = []
    for pretty in (False, True):
        out.append((f"sync pretty={pretty}", node.__render__(pretty=pretty)))
        out.append((f"async pretty={pretty}", _async(node, pretty=pretty)))
    return out


class TestSplitChildBreakout(unittest.TestCase):
    """Neutralization must see the joined body, not each child in isolation."""

    def _assert_single_end(self, node, name):
        for label, html in _all_modes(node):
            with self.subTest(mode=label):
                ends = _end_tags(html, name)
                self.assertEqual(len(ends), 1, html)
                self.assertTrue(html.rstrip().endswith("</%s>" % name), html)
                if name == "script":
                    self.assertNotIn("<!--", html)

    def test_style_split_children(self):
        self._assert_single_end(
            style("a{content:'</sty", "le><img src=x onerror=alert(1)>'}"), "style"
        )

    def test_script_split_children(self):
        self._assert_single_end(script("x='</scr", "ipt><img src=x onerror=alert(1)>'"), "script")

    def test_script_split_comment_open(self):
        self._assert_single_end(script("x='<!", "--<script>'"), "script")

    def test_successive_add(self):
        s = script("x='<")
        s.add("/script")
        s.add("><img src=x onerror=alert(1)>'")
        self._assert_single_end(s, "script")

    def test_index_assignment(self):
        s = script("ok")
        s[0] = "</script><b>x</b>"
        self._assert_single_end(s, "script")

    def test_split_inside_nested_tree(self):
        page = div(style("p{}</st", "yle><b>x</b>"), span("ok"))
        for label, html in _all_modes(page):
            with self.subTest(mode=label):
                self.assertEqual(len(_end_tags(html, "style")), 1, html)


class TestDataScripts(unittest.TestCase):
    """Neutralized forms must stay valid JSON (and JS / u-flag regex)."""

    def test_json_round_trip(self):
        data = {"a": "</script><b>", "b": "<!--<script>", "c": "</SCRIPT x", "d": "a<b&c"}
        body = json.dumps(data)
        for label, html in _all_modes(script(body, type="application/json")):
            with self.subTest(mode=label):
                inner = re.match(r"<script[^>]*>(.*)</script>\s*$", html.strip(), re.S).group(1)
                self.assertEqual(json.loads(inner), data)

    def test_importmap_round_trip(self):
        imap = {"imports": {"x": "/js/x.js?q=</script>&r=<!--"}}
        html = script(json.dumps(imap), type="importmap").__render__(pretty=False)
        inner = html[len('<script type="importmap">') : -len("</script>")]
        self.assertEqual(json.loads(inner), imap)

    def test_no_bang_escape(self):
        # ``\!`` is not a JSON escape and is a SyntaxError in u-flag regexes.
        html = script("s = '<!--';").__render__(pretty=False)
        self.assertNotIn("\\!", html)
        self.assertIn("\\u003C!--", html)


class TestEscapableRawTextUnchanged(unittest.TestCase):
    def test_title_textarea_escape_fully(self):
        for tag in (title, textarea):
            with self.subTest(tag=tag.__name__):
                html = tag("a</%s><b>&" % tag.__name__).__render__(pretty=False)
                self.assertIn("&lt;/%s&gt;&lt;b&gt;&amp;" % tag.__name__, html)
                self.assertEqual(len(_end_tags(html, tag.__name__)), 1)


class TestRawStillWorks(unittest.TestCase):
    def test_raw_child_unescaped_but_guarded_inside_raw_text(self):
        # raw() skips HTML escaping; inside script/style the joined body is still
        # breakout-guarded, else raw("x='</scr") + user "ipt>..." closes the tag.
        self.assertEqual(
            script(raw("a < b && '<!--'")).__render__(pretty=False),
            "<script>a < b && '\\u003C!--'</script>",
        )
        html = script(raw("x='</scr"), "ipt><b>'").__render__(pretty=False)
        self.assertEqual(html, "<script>x='<\\/script><b>'</script>")
        self.assertEqual(div(raw("<b>x</b>")).__render__(pretty=False), "<div><b>x</b></div>")


class TestSyncAsync(unittest.TestCase):
    def test_sync_async_identical(self):
        trees = [
            script(JS),
            style(CSS),
            div(script("</script>x<!--y"), style("</style>z"), span("a<b")),
        ]
        for t in trees:
            for pretty in (False, True):
                with self.subTest(tree=type(t).__name__, pretty=pretty):
                    self.assertEqual(t.__render__(pretty=pretty), _async(t, pretty=pretty))

    def test_component_wrapping_script(self):
        class Boot(Component):
            def render(self):
                return script("window.ok = 1 < 2 && true;")

        b = Boot()
        self.assertEqual(
            b.__render__(pretty=False), "<script>window.ok = 1 < 2 && true;</script>"
        )
        self.assertEqual(b.__render__(pretty=False), _async(b, pretty=False))


class TestCspNonce(unittest.TestCase):
    def test_tree_stamp_keeps_body_verbatim(self):
        t = stamp_tree(div(script(JS), style(CSS)), nonce="N0NCE")
        html = t.__render__(pretty=False)
        self.assertIn(f'<script nonce="N0NCE">{JS}</script>', html)
        self.assertIn(f'<style nonce="N0NCE">{CSS}</style>', html)

    def test_string_html_passes_through_unstamped(self):
        # Since #31 stamp_nonce never rewrites HTML strings (no regex stamping).
        html = div(script('var t = "<script>";')).__render__(pretty=False)
        self.assertEqual(stamp_nonce([html], nonce="N0NCE"), [html])


class TestParseConsistency(unittest.TestCase):
    # String HTML is sanitized (ADR 0002): a fragment drops <style> and every
    # mode drops <script>, whatever ``escape`` says. Document mode is the
    # caller's keyword and keeps <style> text verbatim; the render-time
    # raw-text guard still applies to that element.

    def test_defhtml_style_verbatim_in_document_mode(self):
        for esc in (True, False):
            with self.subTest(escape=esc):
                html = "".join(
                    e.__render__(pretty=False)
                    for e in defHTML(
                        "<html><head><style>a > b{c:d}</style></head></html>",
                        escape=esc,
                        document=True,
                    )
                )
                self.assertIn("<style>a > b{c:d}</style>", html)
                fragment = "".join(
                    e.__render__(pretty=False)
                    for e in defHTML("<style>a > b{c:d}</style>", escape=esc)
                )
                self.assertEqual(fragment, "")

    def test_defhtml_drops_script_in_every_mode(self):
        src = '<script>if (a < b && c) { s = "<!--"; }</script>'
        for kw in ({"escape": False}, {"escape": True}, {"document": True}):
            with self.subTest(**kw):
                html = "".join(e.__render__(pretty=False) for e in defHTML(src, **kw))
                self.assertNotIn("script", html)

    def test_defhtml_untrusted_still_drops_script(self):
        html = "".join(e.__render__(pretty=False) for e in defHTML("<p>x</p><script>a<b</script>"))
        self.assertNotIn("script", html)

    def test_round_trip_stable(self):
        css = "a > b{c:d} p ~ q{color:red}"
        first = style(css).__render__(pretty=False)
        again = "".join(
            e.__render__(pretty=False) for e in defHTML(first, document=True)
        )
        self.assertEqual(again, first)


if __name__ == "__main__":
    unittest.main()
