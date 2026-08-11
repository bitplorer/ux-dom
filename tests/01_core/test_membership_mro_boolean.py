"""Membership: own class/instance existence + subtree; __bool__ vs matches vs in."""

from __future__ import annotations

import asyncio
import unittest

from ux_dom import Component
from ux_dom.dom import div, span, button


async def _collect(el):
    parts = []
    async for t in el.__async_render__(pretty=False):
        parts.append(t)
    return "".join(parts)


class Card(Component):
    def render(self, title="t"):
        return div(title, id="card-root", className="card", data_role="c")


class Wrap(Component):
    def render(self):
        return div(Card(title="N"), id="wrap")


class TestOwnExistence(unittest.TestCase):
    """``in`` / ``matches`` cover the element itself, not only children."""

    def test_bool_is_object_existence_not_membership(self):
        empty = div()
        self.assertTrue(bool(empty))
        self.assertEqual(len(empty), 0)
        # class existence is separate from bool
        self.assertIn(div, empty)  # self is a div
        self.assertNotIn(span, empty)

    def test_matches_own_class_and_attrs(self):
        el = div("x", id="a")
        self.assertTrue(el.matches(div))
        self.assertTrue(el.matches("div"))
        self.assertFalse(el.matches(span))
        self.assertTrue(el.matches(div, id="a"))
        self.assertFalse(el.matches(div, id="b"))

    def test_matches_component_transparent_entry(self):
        c = Card(title="Hi")
        self.assertTrue(c.matches(Card))
        self.assertTrue(c.matches(div))
        self.assertTrue(c.matches(div, id="card-root"))
        self.assertFalse(c.matches(span))

    def test_contains_own_instance(self):
        el = div("x")
        self.assertIn(el, el)
        self.assertNotIn(el, div())
        c = Card()
        self.assertIn(c, c)
        self.assertIn(c._entry, c)

    def test_contains_own_class_name(self):
        self.assertIn(div, div())
        self.assertIn("div", div())
        self.assertNotIn(span, div())
        self.assertNotIn("span", div())


class TestSubtreeMembership(unittest.TestCase):
    def test_component_entry_findable_as_div(self):
        c = Card(title="Hi")
        root = div(c, span("sib"), id="root")
        found = root.get(div)
        self.assertTrue(any(x.attributes.get("id") == "card-root" for x in found))
        self.assertIn(div, root)
        self.assertIn(Card, root)
        self.assertIn(c, root)
        self.assertIn(c._entry, root)
        self.assertTrue(root.get(id="card-root"))
        self.assertTrue(root.get(div, id="card-root"))

    def test_nested_component_mro(self):
        outer = div(Wrap())
        self.assertTrue(outer.get(id="wrap"))
        self.assertTrue(outer.get(id="card-root"))
        self.assertTrue(outer.get(Card))
        self.assertGreaterEqual(len(outer.get(div)), 2)

    def test_component_eq_must_not_break_identity_lists(self):
        c = Card()
        self.assertTrue(c == c._entry)
        self.assertTrue(any(x is c._entry for x in div(c).get(div)))

    def test_attr_presence_empty_string(self):
        child = div()
        child["data-x"] = ""
        self.assertTrue(div(child).get(div, data_x=None))
        self.assertFalse(div(div()).get(div, data_x=None))

    def test_bool_attrs_render(self):
        html = div(hidden=True, disabled=False, open=None).__render__(pretty=False)
        self.assertIn("hidden", html)
        self.assertNotIn("disabled", html)
        self.assertIn("open", html)


class TestSyncAsyncPipelineParity(unittest.TestCase):
    def test_build_pairings_same_html(self):
        with div(id="s", className="box") as sroot:
            span("hello")
            button("go", hx_get="/x")

        async def abuild():
            async with div(id="s", className="box") as aroot:
                span("hello")
                button("go", hx_get="/x")
            return aroot

        aroot = asyncio.run(abuild())
        sync_html = sroot.__render__(pretty=False)
        self.assertEqual(sync_html, aroot.__render__(pretty=False))
        self.assertEqual(asyncio.run(_collect(sroot)), sync_html)
        self.assertEqual(asyncio.run(_collect(aroot)), sync_html)

    def test_component_sync_async_serialize(self):
        c = Card(title="Z")
        self.assertEqual(c.__render__(pretty=False), asyncio.run(_collect(c)))

    def test_tree_with_component_stream_stable(self):
        root = div(Card(title="A"), span("b"))
        a = root.__render__(pretty=False)
        self.assertEqual(asyncio.run(_collect(root)), a)
        self.assertEqual(root.__render__(pretty=False), a)


if __name__ == "__main__":
    unittest.main()
