"""Auto custom-element definitions — host-first, registry SSoT."""

from __future__ import annotations

import unittest

from ux_dom import Document
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import (
    CustomElement,
    WebComponent,
    xelement_registry,
)


class Hello(CustomElement):
    tag_name = "hello"

    def render(self, tag_name: str = "hello"):
        return template(div("Hi", className="hello"), **{"x-tagname": tag_name})


class Badge(CustomElement):
    tag_name = "badge"

    def render(self, tag_name: str = "badge"):
        return template(div("★", className="badge"), **{"x-tagname": tag_name})


class Card(WebComponent):
    tag_name = "card"

    def render(self, tag_name: str = "card"):
        return template(
            div("card", className="card"),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )


class TestHostFirstOrganic(unittest.TestCase):
    def setUp(self):
        xelement_registry.clear()
        self.doc = Document(head=[], body=[], ensure_csrf_token=False)

    def test_construct_is_host_not_double_call(self):
        h = Hello()
        self.assertEqual(getattr(h, "tagname", None), "x-hello")
        html = str(self.doc(div(Hello(), Badge(), Card())))
        self.assertEqual(html.count('x-tagname="hello"'), 1)
        self.assertEqual(html.count('x-tagname="badge"'), 1)
        self.assertEqual(html.count('x-tagname="card"'), 1)
        self.assertIn("x-hello", html)
        self.assertIn("x-badge", html)

    def test_many_hosts_one_definition(self):
        html = str(self.doc(div(Hello(), Hello(), Hello())))
        self.assertEqual(html.count('x-tagname="hello"'), 1)
        self.assertGreaterEqual(html.count("<x-hello"), 3)

    def test_registry_single_source(self):
        Hello()
        Hello()
        d1 = Hello.definition()
        d2 = Hello.definition()
        self.assertIs(d1, d2)
        self.assertIs(xelement_registry.get(Hello), d1)

    def test_call_on_definition_still_host(self):
        """definition()() still works but is not required."""
        host = Hello.definition()()
        self.assertEqual(host.tagname, "x-hello")


if __name__ == "__main__":
    unittest.main()
