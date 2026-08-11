"""Full MRO method/param consistency + behavioural integration."""

from __future__ import annotations

import asyncio
import concurrent.futures
import importlib
import inspect
import random
import sys
import tempfile
import textwrap
import unittest
import warnings
from pathlib import Path

from fastapi.testclient import TestClient

from ux_dom import Component, Document, Fragment, ReactiveComponent
from ux_dom.dom import div, span, button, attr
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.ext import Tags, StyleTags
from ux_dom.dom.src.parse_html import tokenize_html
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.web_io import HtmxEvents

SKIP = {
    "__init__",
    "__new__",
    "__init_subclass__",
    "__class_getitem__",
    "__dict__",
    "__weakref__",
    "__doc__",
    "__module__",
    "__annotations__",
    "__slots__",
    "__abstractmethods__",
    "_abc_impl",
}


def _unwrap(a):
    if isinstance(a, (classmethod, staticmethod)):
        return a.__func__
    if isinstance(a, property):
        return a.fget
    return a


def _param_compat(cs, ps):
    problems = []
    c_var = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in cs.parameters.values())
    for name, p in ps.parameters.items():
        if name in ("self", "cls"):
            continue
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name not in cs.parameters:
            if not c_var:
                problems.append(f"missing `{name}`")
        else:
            c = cs.parameters[name]
            if (
                c.default is inspect.Parameter.empty
                and p.default is not inspect.Parameter.empty
            ):
                problems.append(f"`{name}` required parent optional")
    return problems


class Card(Component):
    def render(self, title="Hi", n=0):
        return div(
            span(title, id=f"t{n}"),
            button("Go", id=f"b{n}"),
            id=f"c{n}",
            className="card",
        )


class Multi(Component):
    def render(self, n=0):
        return [div(f"A{n}", id=f"A{n}"), div(f"B{n}", id=f"B{n}")]


class Ctr(ReactiveComponent):
    def render(self, n=0):
        return div(f"n={n}", id="ctr")


class TestFullMroSignatures(unittest.TestCase):
    def test_all_overrides_param_compatible(self):
        root = Path(__file__).resolve().parents[2] / "src" / "ux_dom"
        issues = []
        seen = set()
        for path in root.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            rel = path.relative_to(root.parent)
            name = (
                ".".join(rel.parts[:-1])
                if rel.name == "__init__.py"
                else ".".join(rel.with_suffix("").parts)
            )
            if name.startswith("ux_dom.cli") or name.startswith("ux_dom.examples"):
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    mod = importlib.import_module(name)
            except Exception:
                continue
            for cls_name, cls in list(vars(mod).items()):
                if not isinstance(cls, type):
                    continue
                if not str(getattr(cls, "__module__", "")).startswith("ux_dom"):
                    continue
                if cls.__module__ != name or id(cls) in seen:
                    continue
                seen.add(id(cls))
                mro = [c for c in cls.__mro__[1:] if c is not object]
                for method, raw in list(cls.__dict__.items()):
                    if method in SKIP:
                        continue
                    cfn = _unwrap(raw)
                    if not callable(cfn) or isinstance(cfn, type):
                        continue
                    parent = praw = None
                    for base in mro:
                        if method in base.__dict__:
                            parent, praw = base, base.__dict__[method]
                            break
                    if parent is None:
                        continue
                    if isinstance(raw, property) != isinstance(praw, property):
                        issues.append(
                            f"{name}.{cls_name}.{method}: property/function kind vs {parent.__name__}"
                        )
                    pfn = _unwrap(praw)
                    if not callable(pfn) or isinstance(pfn, type):
                        continue
                    try:
                        cs, ps = inspect.signature(cfn), inspect.signature(pfn)
                    except (TypeError, ValueError):
                        continue
                    for pr in _param_compat(cs, ps):
                        issues.append(
                            f"{name}.{cls_name}.{method} vs {parent.__name__}: {pr}"
                        )
        self.assertEqual(issues, [], msg="\n".join(issues[:40]))


class TestSharedProtocolParams(unittest.TestCase):
    def test_get_matches_render_signatures(self):
        for cls in (dom_tag, Tags, Component):
            self.assertIn("tag", inspect.signature(cls.get).parameters)
            self.assertIn("tag", inspect.signature(cls.matches).parameters)
        # render family
        for cls in (
            dom_tag,
            Tags,
            Component,
            __import__(
                "ux_dom.dom.htmldocument", fromlist=["HtmlDocument"]
            ).HtmlDocument,
            ReactiveComponent,
        ):
            sig = inspect.signature(cls._render)
            self.assertIn("_seen", sig.parameters)

    def test_htmx_events_get_events_is_method(self):
        h = HtmxEvents()
        self.assertTrue(callable(h.get_events))
        self.assertEqual(h.get_events("hx-get"), {})
        self.assertIsInstance(h.hx_get_events, dict)

    def test_html_parser_param_names(self):
        from html.parser import HTMLParser
        from ux_dom.dom.src.parse_html import HtmlToAst

        for method in (
            "feed",
            "handle_starttag",
            "handle_endtag",
            "handle_charref",
            "handle_entityref",
            "unknown_decl",
        ):
            child = inspect.signature(getattr(HtmlToAst, method))
            parent = inspect.signature(getattr(HTMLParser, method))
            for name in parent.parameters:
                if name == "self":
                    continue
                self.assertIn(name, child.parameters, msg=f"{method} missing {name}")


class TestBehaviourIntegration(unittest.TestCase):
    def test_build_query_mutate_render_pipeline(self):
        with div(id="root", className="r") as root:
            c = Card(title="X", n=1)
            Multi(n=2)
            span("tail", id="tail")

        self.assertIn(Card, root)
        self.assertTrue(root.get(id="c1"))
        self.assertTrue(root.get(id="A2") and root.get(id="B2"))
        title = root.get(id="t1")[0]
        self.assertIn(title, c)
        self.assertFalse(c.matches(title))
        c["data-v"] = "1"
        self.assertEqual(c._entry.attributes.get("data-v"), "1")
        html = root.__render__(pretty=False)
        for token in ("X", "A2", "B2", "tail", "card"):
            self.assertIn(token, html)

        async def arender(el):
            return "".join([t async for t in el.__async_render__(pretty=False)])

        self.assertEqual(asyncio.run(arender(root)), html)

    def test_concurrent_sync_and_async_builds(self):
        def build_i(i):
            with div(id=f"r{i}") as r:
                Card(title=str(i), n=i)
            h = r.__render__(pretty=False)
            self.assertIn(f'id="c{i}"', h)
            return h

        with concurrent.futures.ThreadPoolExecutor(10) as ex:
            hs = list(ex.map(build_i, range(30)))
        self.assertEqual(len(hs), 30)

        async def abuild(i):
            async with div(id=f"ar{i}") as r:
                Card(title=f"a{i}", n=100 + i)
            return r.__render__(pretty=False)

        async def many():
            return await asyncio.gather(*[abuild(i) for i in range(30)])

        ahs = asyncio.run(many())
        for i, h in enumerate(ahs):
            self.assertIn(f'id="c{100 + i}"', h)

    def test_document_reactive_fragment(self):
        page = Document(ensure_csrf_token=False)(Card(title="Doc", n=9))
        self.assertIn("Doc", page.__render__())
        r = Ctr(n=0)
        r["data-x"] = "1"
        self.assertIn("ctr", r.__render__(pretty=False))
        f = Fragment(div("a"), span("b"))
        html = f.__render__(pretty=False)
        self.assertIn("a", html)
        self.assertIn("b", html)

    def test_dialect_layers(self):
        self.assertTrue(
            Tags.clean_attribute("x_on_click") == "@click"
            or Tags.clean_attribute("x_on_click").startswith("@")
        )
        self.assertFalse(StyleTags.clean_attribute("x_on_click").startswith("@"))

    def test_membership_triad(self):
        c = Card(n=5)
        child = c.get(id="t5")[0]
        self.assertTrue(c.matches(Card) and c.matches(div))
        self.assertFalse(c.matches(child))
        self.assertEqual(c.get(child), [child])
        self.assertIn(child, c)
        self.assertIn(span, c)

    def test_parse_html_roundtrip_piece(self):
        ast = tokenize_html('<div class="a"><p>hi</p></div>')
        self.assertIn("hi", str(ast))

    def test_http_app_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            rootp = Path(td)
            pkg = rootp / "intapp"
            (pkg / "app" / "items" / "[id]").mkdir(parents=True)
            for p in [
                pkg,
                pkg / "app",
                pkg / "app" / "items",
                pkg / "app" / "items" / "[id]",
            ]:
                (p / "__init__.py").write_text("")
            (pkg / "app" / "page.py").write_text(textwrap.dedent("""
                    from ux_dom.dom import Component, div, span, button
                    __all__ = ["Page", "Bump"]
                    class Page(Component):
                        routes = ["get"]
                        def render(self):
                            return div(span("pg"), button("b", hx_get="/x"), id="page")
                        @classmethod
                        def get(cls):
                            return cls()
                    class Bump(Component):
                        routes = ["get", "go"]
                        def render(self, n=0):
                            return div(f"n={n}", id="bump")
                        @classmethod
                        def get(cls):
                            return cls(n=0)
                        @classmethod
                        def go(cls):
                            return cls(n=1)
                    """))
            (pkg / "app" / "items" / "[id]" / "route.py").write_text(
                "def get(id: str):\n"
                "    from ux_dom.dom import div\n"
                "    return div(f'item-{id}')\n"
            )
            sys.path.insert(0, str(rootp))
            try:
                api = (
                    App(debug=False)
                    .use(FastAPIHost(title="int", debug=False))
                    .use(
                        DirectoryRouting(
                            package_dir=pkg, base_directory="app", prefix="/a"
                        )
                    )
                    .use(HtmxControl(middleware=True))
                    .build()
                )
                client = TestClient(api)
                self.assertIn("pg", client.get("/a/page/Page").text)
                self.assertIn("n=1", client.get("/a/page/Bump/go").text)
                self.assertIn("item-xyz", client.get("/a/items/xyz").text)
                paths = [
                    "/a/page/Page",
                    "/a/page/Bump",
                    "/a/page/Bump/go",
                    "/a/items/1",
                ]

                def hit(_):
                    return client.get(random.choice(paths)).status_code

                with concurrent.futures.ThreadPoolExecutor(12) as ex:
                    codes = list(ex.map(hit, range(80)))
                self.assertTrue(all(c == 200 for c in codes))
            finally:
                sys.path.remove(str(rootp))

    def test_clear_iadd_uniqueid(self):
        d = div(span("1"), span("2"))
        d.clear()
        self.assertEqual(len(d), 0)
        d += span("3")
        self.assertEqual(len(d.get(span)), 1)
        ids = [uniqueid() for _ in range(50)]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
