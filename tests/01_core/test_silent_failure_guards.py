"""Fail-closed behaviour: sanitize, Fragment JSON, multi-root, XSS guards."""
from __future__ import annotations

import unittest
import warnings
from dataclasses import dataclass

from ux_dom import Component, Fragment, ReactiveComponent
from ux_dom.dom import div, span
from ux_dom.dom.src.html_string import defHTML


class TestFragmentXDataFailClosed(unittest.TestCase):
    def test_valid_x_data_merge(self):
        f = Fragment(div(**{"x-data": "{'a': 1}"}), **{"x-data": "{'b': 2}"})
        html = f.__render__(pretty=False)
        self.assertIn("a", html)
        self.assertIn("b", html)

    def test_invalid_fragment_x_data_does_not_crash(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            f = Fragment(div(**{"x-data": "{'a': 1}"}), **{"x-data": "NOT_JSON"})
            html = f.__render__(pretty=False)
        self.assertIn("x-data", html)
        # child value kept
        self.assertIn("a", html)

    def test_invalid_child_x_data_does_not_crash(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            f = Fragment(div(**{"x-data": "NOPE"}), **{"x-data": "{'b': 2}"})
            html = f.__render__(pretty=False)
        self.assertTrue(isinstance(html, str))


class TestDefHTMLEscapeSanitizes(unittest.TestCase):
    def test_script_stripped_when_escape_true(self):
        nodes = defHTML('<script>alert(1)</script><p>ok</p>', escape=True)
        html = "".join(n.__render__(pretty=False) for n in nodes)
        self.assertNotIn("<script>", html)
        self.assertIn("<p>", html)
        self.assertIn("ok", html)

    def test_script_kept_when_escape_false(self):
        nodes = defHTML("<script>alert(1)</script>", escape=False)
        html = "".join(n.__render__(pretty=False) for n in nodes)
        self.assertIn("<script>", html)

    def test_onclick_stripped_when_escape_true(self):
        nodes = defHTML('<div onclick="alert(1)">x</div>', escape=True)
        html = "".join(n.__render__(pretty=False) for n in nodes)
        self.assertNotIn("onclick", html.lower())
        self.assertIn(">x<", html)

    def test_javascript_href_stripped(self):
        nodes = defHTML('<a href="javascript:alert(1)">x</a>', escape=True)
        html = "".join(n.__render__(pretty=False) for n in nodes)
        self.assertNotIn("javascript:", html.lower())


class TestComponentMarkdownXSS(unittest.TestCase):
    def test_markdown_script_not_executable_when_escape(self):
        @dataclass(eq=False)
        class MD(Component):
            string_is_markdown = True
            escape_string = True

            def render(self):
                return "<script>alert(1)</script>\n\n# Hi"

        html = MD().__render__(pretty=False)
        self.assertNotIn("<script>", html)
        self.assertIn("Hi", html)


class TestComponentMultiRootStable(unittest.TestCase):
    def test_multi_root_entry_is_self(self):
        @dataclass(eq=False)
        class M(Component):
            def render(self):
                return [span("a"), span("b")]

        m = M()
        self.assertIs(m._entry, m)
        self.assertIn("a", m.__render__(pretty=False))
        self.assertIn("b", m.__render__(pretty=False))


class TestReactiveStillGood(unittest.TestCase):
    def test_multi_root_reactive(self):
        @dataclass(eq=False)
        class M(ReactiveComponent):
            n: int = 0

            def render(self, n=0):
                return [span(str(n)), span("z")]

        m = M(1)
        m.n = 2
        html = m.__render__(pretty=False)
        self.assertIn(">2<", html)
        self.assertIs(m._entry, m)


if __name__ == "__main__":
    unittest.main()
