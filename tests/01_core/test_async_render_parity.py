"""Sync ``__render__`` is the reference: ``__async_render__`` must match it.

Also locks two small DOM defects found by the same audit (#59):
``previousSibling`` of a first child, and ``body=`` asset inference.
"""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
import unittest
from dataclasses import dataclass

import ux_dom.dom
from ux_dom import Document, ReactiveComponent
from ux_dom.dom import (
    CSS,
    CSSClass,
    CSSId,
    Keyframes,
    br,
    div,
    li,
    p,
    pre,
    span,
    style,
    ul,
    wbr,
)
from ux_dom.dom.htmldocument import HtmlDocument
from ux_dom.dom.src.ext import StyleTags, Tags


def _arender(node, **kw) -> str:
    async def run():
        return "".join([t async for t in node.__async_render__(**kw)])

    return asyncio.run(run())


class btn(CSSClass):
    pass


class main(CSSId):
    pass


class fade(Keyframes):
    pass


class body_(CSS):
    pass


@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(span(str(count)), id="counter")


def _mutated_counter():
    c = Counter(count=1)
    c.count = 7  # state changed after construction: refresh happens in _render
    return c


def _mutated_counter_child():
    c = Counter(count=1)
    root = div(c)
    c.count = 7
    return root


# One fresh-tree factory per class that overrides a serialize hook. The guard
# test below fails when a new override appears without a parity case here.
PARITY_CASES = {
    StyleTags: [lambda: style(body_(margin=0))],
    CSSClass: [lambda: style(btn(color="red"))],
    CSSId: [lambda: style(main(color="red"))],
    Keyframes: [lambda: style(fade(from_={"opacity": 0}, to={"opacity": 1}))],
    ReactiveComponent: [_mutated_counter, _mutated_counter_child],
    HtmlDocument: [
        lambda: Document(ensure_csrf_token=False)(
            div("a"), style(btn(color="red")), _mutated_counter()
        )
    ],
}


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


class TestAsyncRenderParity(unittest.TestCase):
    def assert_parity(self, make):
        for pretty in (False, True):
            with self.subTest(pretty=pretty):
                self.assertEqual(
                    _arender(make(), pretty=pretty), make().__render__(pretty=pretty)
                )

    def test_css_class_in_style(self):
        self.assertEqual(
            _arender(style(btn(color="red")), pretty=False),
            "<style>.btn{color:red;}</style>",
        )
        for make in PARITY_CASES[CSSClass]:
            self.assert_parity(make)

    def test_css_id_and_keyframes_in_style(self):
        for make in PARITY_CASES[CSSId] + PARITY_CASES[Keyframes]:
            self.assert_parity(make)

    def test_reactive_mutated_after_construction(self):
        self.assertIn("<span>7</span>", _arender(_mutated_counter(), pretty=False))
        self.assertIn(
            "<span>7</span>", _arender(_mutated_counter_child(), pretty=False)
        )
        for make in PARITY_CASES[ReactiveComponent]:
            self.assert_parity(make)

    def test_non_pretty_root_keeps_children_compact(self):
        # pre/style/br/wbr are not pretty: sync never reflows their subtree, and
        # whitespace inside <pre> is content.
        for tag in (pre, style, br, wbr):
            with self.subTest(tag=tag.__name__):
                make = lambda: tag(div(p("x"), ul(li("a"))))  # noqa: E731
                self.assertNotIn("\n", _arender(make(), pretty=True))
                self.assert_parity(make)

    def test_document_compact_does_not_call_render(self):
        # Mirrors test_pretty_stream's pin: a plain Document stays on the fast
        # walker (pre_render once, no _render for the page or its plain children).
        doc = Document(ensure_csrf_token=False)(div(span("a"), span("b")))
        calls = {"n": 0}
        orig = Tags._render

        def counting(self, sb, *a, **k):
            calls["n"] += 1
            return orig(self, sb, *a, **k)

        Tags._render = counting  # type: ignore
        try:
            html = _arender(doc, pretty=False)
        finally:
            Tags._render = orig  # type: ignore
        self.assertEqual(calls["n"], 0)
        self.assertEqual(html, doc.__render__(pretty=False))

    def test_every_serialize_hook_override_has_parity_case(self):
        for mod in pkgutil.walk_packages(ux_dom.dom.__path__, "ux_dom.dom."):
            importlib.import_module(mod.name)
        hooks = {name for name in vars(Tags) if name.startswith("_render")}
        overriding = {
            cls
            for cls in _all_subclasses(Tags)
            if cls.__module__.startswith("ux_dom.")
            and any(h in vars(cls) for h in hooks)
        }
        missing = sorted(c.__qualname__ for c in overriding - set(PARITY_CASES))
        self.assertEqual(missing, [], "add a PARITY_CASES entry for each")
        for cls in sorted(overriding, key=lambda c: c.__qualname__):
            for make in PARITY_CASES[cls]:
                with self.subTest(cls=cls.__qualname__):
                    self.assert_parity(make)


class TestPreviousSibling(unittest.TestCase):
    def test_first_child_has_no_previous_sibling(self):
        first, last = span("a"), span("b")
        div(first, last)
        self.assertIsNone(first.previousSibling)
        self.assertIs(last.previousSibling, first)
        self.assertIs(first.nextSibling, last)
        self.assertIsNone(last.nextSibling)


class TestBodyAssetInference(unittest.TestCase):
    def render(self, **kw):
        doc = Document(ensure_csrf_token=False)(div("x"), **kw)
        return doc.__render__(pretty=False)

    def test_body_meta_dict_is_meta(self):
        html = self.render(body=[{"name": "theme-color", "content": "#000"}])
        self.assertIn('<meta content="#000" name="theme-color">', html)
        self.assertNotIn("<script content=", html)

    def test_body_uppercase_css_is_link(self):
        html = self.render(body=["/css/APP.CSS"])
        self.assertIn('<link href="/css/APP.CSS" rel="stylesheet">', html)
        self.assertNotIn('<script src="/css/APP.CSS"', html)

    def test_body_explicit_link_tag_wins(self):
        html = self.render(
            body=[
                {"tag": "link", "href": "/a.css", "name": "x"},
                {"tag": "css", "href": "/b.css", "charset": "utf-8"},
                {"tag": "link", "src": "/c.css"},
            ]
        )
        self.assertIn('<link href="/a.css" name="x" rel="stylesheet">', html)
        self.assertIn('<link charset="utf-8" href="/b.css" rel="stylesheet">', html)
        self.assertIn('<link rel="stylesheet" src="/c.css">', html)
        self.assertNotIn('<meta charset="utf-8" href', html)

    def test_body_defaults_unchanged(self):
        html = self.render(body=["/js/app.js", "/app", "/a.css", {"href": "/b.css"}])
        self.assertIn('<script src="/js/app.js"></script>', html)
        self.assertIn('<script src="/app"></script>', html)
        self.assertIn('<link href="/a.css" rel="stylesheet">', html)
        self.assertIn('<link href="/b.css" rel="stylesheet">', html)


if __name__ == "__main__":
    unittest.main()
