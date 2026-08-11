"""Capability smoke: Component, Document, Slots-related patterns, render protocol."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from ux_dom import Component, Document
from ux_dom.dom import button, div, form, input_


class TestComponentPatterns(unittest.TestCase):
    def test_dataclass_component_like_sarrafa(self):
        @dataclass(eq=False)
        class Card(Component):
            title: str

            def __post_init__(self):
                super().__init__(title=self.title)

            def render(self, title):
                with div(className="card") as root:
                    div(title, className="title")
                return root

        html = Card(title="Gem").__render__(pretty=False)
        self.assertIn("Gem", html)
        self.assertIn("card", html)

    def test_render_protocol_for_channel(self):
        el = div("x")
        self.assertTrue(callable(getattr(el, "__render__", None)))
        out = el.__render__()
        self.assertIsInstance(out, str)

    def test_document_shell(self):
        doc = Document(ensure_csrf_token=False)
        page = doc(div("hello"), head=[], body=[])
        html = str(page)
        self.assertIn("hello", html)
        self.assertIn("<html", html.lower())

    def test_hx_partial_pattern(self):
        def view(hx_request: bool):
            body = div("partial", id="p")
            if hx_request:
                return body
            return Document(ensure_csrf_token=False)(body)

        self.assertNotIn("<html", view(True).__render__(pretty=False).lower())
        self.assertIn("<html", str(view(False)).lower())


if __name__ == "__main__":
    unittest.main()
