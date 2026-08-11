"""Builtin/dunder behaviour consistency along MRO (dom_tag, Component, Element)."""

from __future__ import annotations

import asyncio
import copy
import importlib
import inspect
import unittest
import warnings
from pathlib import Path

from ux_dom import Component, Document, Fragment, ReactiveComponent
from ux_dom.dom import div, span, button
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.parse_html import Element, tokenize_html

BUILTINS = {
    "__bool__",
    "__len__",
    "__iter__",
    "__contains__",
    "__eq__",
    "__hash__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__enter__",
    "__exit__",
    "__aenter__",
    "__aexit__",
    "__iadd__",
}


def _unwrap(a):
    if isinstance(a, (classmethod, staticmethod)):
        return a.__func__
    return a


def _compat(cs, ps):
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
    def render(self, title="Hi"):
        return div(
            span(title, id="title"),
            button("Go", id="btn"),
            id="card",
        )


class Ctr(ReactiveComponent):
    def render(self, n=0):
        return div(f"n={n}", id="ctr")


class TestBuiltinSignaturesAlongMro(unittest.TestCase):
    def test_builtin_overrides_compatible(self):
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
                    if method not in BUILTINS:
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
                    pfn = _unwrap(praw)
                    if not callable(pfn) or isinstance(pfn, type):
                        continue
                    try:
                        cs, ps = inspect.signature(cfn), inspect.signature(pfn)
                    except (TypeError, ValueError):
                        continue
                    for pr in _compat(cs, ps):
                        issues.append(
                            f"{name}.{cls_name}.{method} vs {parent.__name__}: {pr}"
                        )
        self.assertEqual(issues, [], msg="\n".join(issues))

    def test_element_mutable_sequence_param_names(self):
        self.assertIn("value", inspect.signature(Element.__setitem__).parameters)
        self.assertIn("value", inspect.signature(Element.insert).parameters)


class TestDomTagBuiltinBehaviour(unittest.TestCase):
    def test_bool_len_iter_contains(self):
        empty = div()
        self.assertTrue(bool(empty))
        self.assertEqual(len(empty), 0)
        self.assertEqual(list(empty), [])
        self.assertIn(div, empty)
        self.assertNotIn(span, empty)

        tree = div(span("a"), span("b"))
        self.assertEqual(len(tree), 2)
        self.assertEqual(sum(1 for _ in tree), 2)
        self.assertIn(span, tree)

    def test_getitem_setitem_iadd(self):
        tree = div(span("a"))
        tree[0] = span("z")
        self.assertIn("z", tree.__render__(pretty=False))
        d = div()
        d += "hello"
        self.assertIn("hello", d.__render__(pretty=False))

    def test_context_managers(self):
        with div(id="s") as root:
            span("in")
        self.assertIn("in", root.__render__(pretty=False))

        async def aw():
            async with div(id="a") as r:
                span("ay")
            return r

        r = asyncio.run(aw())
        self.assertIn("ay", r.__render__(pretty=False))

    def test_plain_eq_is_identity(self):
        a, b = div(id="x"), div(id="x")
        self.assertIsNot(a, b)
        self.assertFalse(a == b)
        self.assertIsInstance(hash(a), int)


class TestComponentBuiltinBehaviour(unittest.TestCase):
    def test_transparent_len_iter_contains(self):
        c = Card()
        self.assertTrue(bool(c))
        self.assertEqual(len(c), 2)
        self.assertEqual(len(list(c)), 2)
        title = c.get(id="title")[0]
        self.assertIn(title, c)
        self.assertFalse(c.matches(title))
        self.assertIn(div, c)
        self.assertIn(span, c)

    def test_eq_hash_entry_contract(self):
        c = Card()
        self.assertTrue(c == c._entry)
        self.assertIsNot(c, c._entry)
        self.assertNotEqual(hash(c), hash(c._entry))
        # set uses hash then eq — entry must not resolve as member of {card}
        self.assertNotIn(c._entry, {c})

    def test_getitem_setitem_delitem_redirect(self):
        c = Card()
        self.assertEqual(c["id"], "card")
        c["data-t"] = "1"
        self.assertEqual(c._entry.attributes.get("data-t"), "1")
        del c["data-t"]
        self.assertNotIn("data-t", c._entry.attributes)

    def test_reactive_inherits_contract(self):
        r = Ctr(n=1)
        self.assertTrue(bool(r))
        self.assertTrue(r == r._entry)
        self.assertNotEqual(hash(r), hash(r._entry))
        r["data-x"] = "x"
        self.assertIn("ctr", r.__render__(pretty=False))

    def test_fragment_and_document(self):
        f = Fragment(div("a"), span("b"))
        html = f.__render__(pretty=False)
        self.assertIn("a", html)
        self.assertIn("b", html)
        page = Document(ensure_csrf_token=False)(div("x"))
        self.assertTrue(bool(page))
        self.assertIn("x", page.__render__())

    def test_deepcopy_card(self):
        c = Card()
        c2 = copy.deepcopy(c)
        self.assertIn("Hi", c2.__render__(pretty=False))


class TestElementSequence(unittest.TestCase):
    def test_tokenize_children(self):
        root = tokenize_html('<div class="n"><p>t</p><p>u</p></div>')
        el = root[0]
        self.assertEqual(len(el), 2)
        child = el[0]
        el[0] = child
        self.assertIs(el[0], child)


if __name__ == "__main__":
    unittest.main()
