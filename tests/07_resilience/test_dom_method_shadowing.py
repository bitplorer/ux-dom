"""DOM method shadowing: user method names must not hijack library internals.

* Regression: a Component with an action named ``add`` still adopts children
  from ``with`` blocks, constructor args and ``+=`` (internals call ``_add``).
* Seal: ``get`` / ``matches`` cannot be redefined on a ``dom_tag`` subclass.
* Absence lock: internal mutators exist only under their ``_`` names; the old
  public names are free for user methods (e.g. a ``remove`` action).
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

    def test_classmethod_add_does_not_swallow_with_children(self):
        # #49 review lock: once Component.__getattribute__ was removed, a
        # ``@classmethod add`` shadowed the instance API and ``with Hello():
        # span()`` silently dropped the span. Internals must call ``_add``.
        class Hello(Component):
            def render(self):
                return div(id="hello")

            @classmethod
            def add(cls, *a, **k):
                return "classmethod-ran"

        with Hello() as h:
            span("child")
        self.assertEqual(
            h.__render__(pretty=False), '<div id="hello"><span>child</span></div>'
        )
        h += span("iadd")
        self.assertIn("<span>child</span><span>iadd</span>", h.__render__(pretty=False))
        self.assertEqual(Hello.add(), "classmethod-ran")

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

    def test_mixin_earlier_in_mro_rejected(self):
        # Review lock (#51): the seal must resolve each name through the MRO,
        # not only the class's own __dict__.
        class RouteMixin:
            @classmethod
            def get(cls, *a, **k):
                return "page"

            def matches(self, *a, **k):
                return "hijacked"

        with self.assertRaisesRegex(TypeError, "RouteMixin.*'get'|'get'.*RouteMixin"):

            class Page(RouteMixin, Component):
                def render(self):
                    return div(span("x", id="x"))

        class OnlyMatches:
            matches = 0

        with self.assertRaisesRegex(TypeError, "'matches'"):
            type("P2", (OnlyMatches, div), {})

    def test_mixin_later_in_mro_is_harmless(self):
        class Tail:
            def get(self, *a, **k):
                return "never reached"

        class Ok(div, Tail):
            pass

        self.assertEqual(Ok(span(id="a")).get(id="a")[0].attributes["id"], "a")

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

    def test_old_public_names_are_free_for_user_methods(self):
        # Coordinator decision (#51): DOM internals use the ``_`` hooks, so
        # ``remove`` / ``clear`` / ... are free for user methods and actions
        # and never touch DOM building.
        class TodoList(Component):
            def render(self):
                return ul(id="todos")

            @action
            def remove(self, item_id):
                self.removed = item_id
                return "removed"

            def clear(self):
                self.cleared = True
                return "cleared"

            def set_attribute(self, key, value):
                raise AssertionError("library must not call the old name")

        with TodoList() as t:
            li("a")
            li("b")
        t += li("c")
        self.assertEqual(
            t.__render__(pretty=False),
            '<ul id="todos"><li>a</li><li>b</li><li>c</li></ul>',
        )
        self.assertEqual(t.remove(7), "removed")
        self.assertEqual(t.removed, 7)
        self.assertEqual(t.clear(), "cleared")
        self.assertTrue(t.cleared)
        self.assertEqual(len(t._entry.children), 3)

        class Mixin:
            def replace_children(self, *a):
                return "mine"

        class Box(Mixin, div):
            pass

        b = Box(span("x"))
        self.assertEqual(b.replace_children(), "mine")
        self.assertIn("<span>x</span>", b.__render__(pretty=False))

    def test_underscore_hooks_are_the_extension_point(self):
        calls = []

        class Upper(div):
            def _set_attribute(self, key, value):
                calls.append(key)
                super()._set_attribute(key, str(value).upper())

            def _add(self, *args):
                calls.append("add")
                return super()._add(*args)

        u = Upper("a", title="x")
        with u:
            span("b")
        u += span("c")
        html = u.__render__(pretty=False)
        self.assertIn('title="X"', html)
        self.assertIn("a<span>b</span><span>c</span>", html)
        self.assertIn("title", calls)
        self.assertGreaterEqual(calls.count("add"), 3)

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
