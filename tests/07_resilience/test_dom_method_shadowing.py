"""DOM method shadowing: user method names must not hijack library internals.

* Regression: a Component with an action named ``add`` still adopts children
  from ``with`` blocks, constructor args and ``+=`` (internals call ``_add``).
* Seal: ``get`` / ``matches`` cannot be redefined on a ``dom_tag`` subclass.
* Absence lock: internal-only mutators exist only under their ``_`` names.
"""
from __future__ import annotations

import unittest

from ux_dom import Component, Fragment, ReactiveComponent
from ux_dom.dom import div, li, span, ul
from ux_dom.dom.src.dom_tag import dom_tag


def action(fn):
    """Stand-in for ``ux_channel``'s ``@action`` (marks and returns the method)."""
    fn._ux_region_action = {"refresh": True}
    return fn


class Cart(Component):
    def render(self):
        return ul(id="lines")

    @action
    def add(self, sku, qty=1):
        self.added = (sku, qty)
        return "action-ran"


class TestCartAddRegression(unittest.TestCase):
    def test_with_block_adopts_child(self):
        with Cart() as c:
            li("one")
        html = c.__render__(pretty=False)
        self.assertIn("<li>one</li>", html)
        self.assertFalse(hasattr(c, "added"), "action must not run during attach")

    def test_nested_with_and_iadd(self):
        with div() as d:
            with Cart() as c:
                li("a")
        c += li("b")
        html = d.__render__(pretty=False)
        self.assertIn('<ul id="lines"><li>a</li><li>b</li></ul>', html)
        self.assertFalse(hasattr(c, "added"))

    def test_user_add_is_still_callable(self):
        c = Cart()
        self.assertEqual(c.add("board", qty=2), "action-ran")
        self.assertEqual(c.added, ("board", 2))
        self.assertEqual(len(c._entry.children), 0)

    def test_fragment_and_reactive_with_add_method(self):
        class Group(Fragment):
            def add(self, *a):
                raise AssertionError("user add must not be used for attach")

        g = Group(div("x"), span("y"), className="g")
        self.assertIn('class="g"', g.__render__(pretty=False))

        class Counter(ReactiveComponent):
            def render(self, n=0):
                return div(f"n={n}", id="c")

            def add(self, *a):
                raise AssertionError("user add must not be used for attach")

        with Counter(n=1) as k:
            span("tail")
        self.assertIn("<span>tail</span>", k.__render__(pretty=False))

    def test_public_add_still_attaches_by_default(self):
        d = div()
        d.add(span("z"))
        self.assertEqual(d.__render__(pretty=False), "<div><span>z</span></div>")


class TestSealedQueryApi(unittest.TestCase):
    def _assert_rejected(self, name, body):
        with self.assertRaisesRegex(TypeError, f"defines '{name}'"):
            type("Bad", (Component,), {"render": lambda self: div(), name: body})

    def test_get_instance_method_rejected(self):
        self._assert_rejected("get", lambda self, *a, **k: [])

    def test_get_classmethod_rejected(self):
        self._assert_rejected("get", classmethod(lambda cls: "page"))

    def test_matches_rejected(self):
        self._assert_rejected("matches", lambda self, *a, **k: True)
        self._assert_rejected("matches", staticmethod(lambda: True))

    def test_plain_dom_tag_subclass_rejected(self):
        with self.assertRaises(TypeError):

            class T(dom_tag):
                def get(self):
                    return 1

    def test_queries_unchanged(self):
        class Card(Component):
            def render(self):
                return div(span("t", id="title"), id="card")

        c = Card()
        self.assertEqual(c.get(Card), [c])
        self.assertIs(c.get(div)[0], c._entry)
        self.assertEqual(len(c.get(id="title")), 1)
        self.assertTrue(c.matches(div, id="card"))
        self.assertIn(span, c)
        self.assertEqual(div(c).get(Card), [c])


OLD_INTERNAL = (
    "clear",
    "remove",
    "set_attribute",
    "delete_attribute",
    "setdocument",
    "replace_children",
)


class TestOldInternalNamesAbsent(unittest.TestCase):
    def test_public_names_gone_private_present(self):
        from ux_dom.alpinejs.dataset import DataSet
        from ux_dom.dom.src.component import MergeClassAttribute

        for cls in (dom_tag, Component, Fragment, ReactiveComponent,
                    MergeClassAttribute, DataSet, div):
            for name in OLD_INTERNAL:
                with self.subTest(cls=cls.__name__, name=name):
                    self.assertFalse(
                        any(name in vars(k) for k in cls.__mro__),
                        f"{cls.__name__}.{name} must not exist (use _{name})",
                    )
                    self.assertTrue(callable(getattr(cls, f"_{name}")))

    def test_item_syntax_still_works(self):
        d = div(span("a"))
        d["data-x"] = "1"
        d[0] = span("b")
        self.assertEqual(d.__render__(pretty=False), '<div data-x="1"><span>b</span></div>')
        del d["data-x"]
        del d[0]
        self.assertEqual(d.__render__(pretty=False), "<div></div>")

    def test_add_is_thin_alias(self):
        self.assertTrue(callable(dom_tag._add))
        self.assertIn("_add", dom_tag.add.__code__.co_names)


if __name__ == "__main__":
    unittest.main()
