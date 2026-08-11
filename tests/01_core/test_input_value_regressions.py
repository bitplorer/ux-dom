"""Form input value plumbing (CharInput/TextInput and related regressions)."""
from __future__ import annotations

import unittest
import warnings
from dataclasses import dataclass

from ux_dom import Component, Fragment, ReactiveComponent
from ux_dom.dom import div, span
from ux_dom.dom.src.html_string import defHTML
from ux_dom.elements.chars import CharInput, TextInput


class TestFragmentUniqueId(unittest.TestCase):
    def test_id_only_on_first_child(self):
        f = Fragment(div("a"), div("b"), id="same", className="c")
        html = f.__render__(pretty=False)
        self.assertEqual(html.count('id="same"'), 1)
        self.assertEqual(html.count("class="), 2)  # both get class
        self.assertIn(">a<", html)
        self.assertIn(">b<", html)

    def test_single_child_keeps_id(self):
        f = Fragment(div("only"), id="one")
        self.assertIn('id="one"', f.__render__(pretty=False))


class TestCharInputValue(unittest.TestCase):
    def test_char_input_value(self):
        html = CharInput(name="q", type="text", placeholder="", value="v1").__render__(
            pretty=False
        )
        self.assertIn('value="v1"', html)

    def test_text_input_value(self):
        html = TextInput(name="q", placeholder="ph", value="v2").__render__(pretty=False)
        self.assertIn('value="v2"', html)
        self.assertIn('name="q"', html)

    def test_value_escaped(self):
        html = TextInput(
            name="q", placeholder="p", value='"><script>x</script>'
        ).__render__(pretty=False)
        self.assertNotIn("<script>", html)


class TestDefHTMLStillSafe(unittest.TestCase):
    def test_img_onerror(self):
        nodes = defHTML('<img src=x onerror=alert(1)>', escape=True)
        html = "".join(n.__render__(pretty=False) for n in nodes)
        self.assertNotIn("onerror", html.lower())


class TestReactiveStillOk(unittest.TestCase):
    def test_multi_and_parent(self):
        @dataclass(eq=False)
        class M(ReactiveComponent):
            n: int = 0

            def render(self, n=0):
                return [span(str(n)), span("z")]

        m = M(1)
        root = div(m, id="r")
        m.n = 4
        html = root.__render__(pretty=False)
        self.assertIn(">4<", html)
        self.assertIs(m.parent, root)


if __name__ == "__main__":
    unittest.main()
