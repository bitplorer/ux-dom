"""Chaos / edge tests for HTML and attribute parsing."""

from __future__ import annotations

import concurrent.futures
import random
import unittest

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.src.parse_html import Attribute, tokenize_html, _normalize_attrs


class TestHtmlParseChaos(unittest.TestCase):
    def test_tokenize_variants(self):
        for s in (
            "",
            "text",
            "<div></div>",
            "<div><p>x</p></div>",
            "<!--c-->",
            "<img src=x>",
            "<div class='a b'>hi</div>",
            "<script>if (a < b) {}</script>",
            "<div>" + "x" * 5000 + "</div>",
            "<<<<>>>>",
            "<input checked id=i>",
        ):
            root = tokenize_html(s)
            self.assertIsNotNone(str(root))

    def test_none_and_non_str(self):
        self.assertEqual(str(tokenize_html(None)), "")
        self.assertEqual(defHTML(None), [])
        els = defHTML(42)
        self.assertTrue(els or els == [])

    def test_defhtml_roundtrip_and_custom(self):
        els = defHTML("<div id='a'><span>z</span></div>")
        self.assertEqual(len(els), 1)
        self.assertIn("z", els[0].__render__(pretty=False))
        custom = defHTML("<my-x foo='1'>q</my-x>")
        self.assertIn("q", custom[0].__render__(pretty=False))

    def test_component_string_parse(self):
        class C(Component):
            def render(self, html="<div>ok</div>"):
                return html

        self.assertIn("hello", C(html="<div>hello</div>").__render__(pretty=False))

    def test_concurrent_parse(self):
        def work(i):
            tokenize_html(f"<div><p>{i}</p></div>")
            defHTML(f"<ul><li>{i}</li></ul>")
            return True

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            self.assertTrue(all(ex.map(work, range(40))))

    def test_html_bombs(self):
        def bomb(_):
            parts = []
            for _ in range(20):
                t = random.choice(["div", "span", "img", "br", "p"])
                parts.append(f"<{t}>")
                if random.random() > 0.5:
                    parts.append("a&<>")
                if random.random() > 0.5:
                    parts.append(f"</{t}>")
            s = "".join(parts)
            tokenize_html(s)
            defHTML(s)
            return True

        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            self.assertTrue(all(ex.map(bomb, range(30))))


class TestAttributeParse(unittest.TestCase):
    def test_normalize_and_classes(self):
        self.assertEqual(
            _normalize_attrs([("class", None), ("id", "x")]),
            {"class": "", "id": "x"},
        )
        self.assertEqual(Attribute({}).classes, [])
        self.assertEqual(Attribute({"class": None}).classes, [])
        s = str(Attribute({"checked": True, "disabled": False, "id": "a"}))
        self.assertIn("checked", s)
        self.assertNotIn("disabled", s)
        self.assertIn('id="a"', s)

    def test_ux_dom_attr_dialects(self):
        h = div(
            hx_get="/x",
            hx_on_click="f()",
            x_on_click="g()",
            ws_send=True,
            sse_connect="/s",
            data_channel_id="R1",
            class_="a",
        ).__render__(pretty=False)
        for tok in (
            "hx-get",
            "hx-on:click",
            "@click",
            "ws-send",
            "sse-connect",
            "data-channel-id",
            'class="a"',
        ):
            self.assertIn(tok, h)


if __name__ == "__main__":
    unittest.main()
