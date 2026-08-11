"""Two-phase model: build render vs serialize — no buried double-build."""

from __future__ import annotations

import asyncio
import unittest

from ux_dom import Document
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement, xelement_registry
from ux_dom.dom.htmldocument import HtmlDocument
from ux_dom.dom.src.component import Component


class TestRenderPhases(unittest.TestCase):
    def test_component_render_once_on_init_not_on_str(self):
        n = {"r": 0}

        class P(Component):
            def render(self, *a, **k):
                n["r"] += 1
                return div("x")

        p = P()
        self.assertEqual(n["r"], 1)
        str(p)
        str(p)
        self.assertEqual(n["r"], 1)

    def test_document_shell_render_once(self):
        n = {"r": 0}
        orig = HtmlDocument.render

        def wrapped(self, *a, **k):
            n["r"] += 1
            return orig(self, *a, **k)

        HtmlDocument.render = wrapped  # type: ignore
        try:
            tree = Document(ensure_csrf_token=False)(div("a"))
            self.assertEqual(n["r"], 1)
            str(tree)
            str(tree)
            self.assertEqual(n["r"], 1)
        finally:
            HtmlDocument.render = orig  # type: ignore

    def test_pre_render_once_per_sync_serialize(self):
        n = {"p": 0}
        orig = HtmlDocument.__pre_render__

        def wrapped(self, *a, **k):
            n["p"] += 1
            return orig(self, *a, **k)

        HtmlDocument.__pre_render__ = wrapped  # type: ignore
        try:
            tree = Document(ensure_csrf_token=False)(div("a"))
            self.assertEqual(n["p"], 0)
            str(tree)
            self.assertEqual(n["p"], 1)
            str(tree)
            self.assertEqual(n["p"], 2)  # once per serialize call, not double per call
        finally:
            HtmlDocument.__pre_render__ = orig  # type: ignore

    def test_pre_render_once_per_async_compact_and_pretty(self):
        n = {"p": 0}
        orig = HtmlDocument.__pre_render__

        def wrapped(self, *a, **k):
            n["p"] += 1
            return orig(self, *a, **k)

        HtmlDocument.__pre_render__ = wrapped  # type: ignore
        try:
            tree = Document(ensure_csrf_token=False)(div("a"))

            async def compact():
                return "".join([t async for t in tree.__async_render__(pretty=False)])

            async def pretty():
                return "".join([t async for t in tree.__async_render__(pretty=True)])

            asyncio.run(compact())
            self.assertEqual(n["p"], 1, "compact stream must pre_render once")
            asyncio.run(pretty())
            self.assertEqual(
                n["p"], 2, "pretty stream must pre_render once more, not +2"
            )
        finally:
            HtmlDocument.__pre_render__ = orig  # type: ignore

    def test_xelement_definition_render_once_for_many_hosts(self):
        xelement_registry.clear()
        n = {"r": 0}

        class Hello(CustomElement):
            tag_name = "hello"

            def render(self, tag_name: str = "hello"):
                n["r"] += 1
                return template(div("Hi"), **{"x-tagname": tag_name})

        hosts = [Hello(), Hello(), Hello()]
        self.assertEqual(n["r"], 1)
        html = str(Document(ensure_csrf_token=False)(div(*hosts)))
        self.assertEqual(n["r"], 1)
        self.assertEqual(html.count('x-tagname="hello"'), 1)


if __name__ == "__main__":
    unittest.main()
