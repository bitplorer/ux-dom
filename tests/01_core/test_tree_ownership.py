"""Tree ownership: single parent, remove/delitem clear parent, no double-add."""

from __future__ import annotations

import sys
import unittest

from ux_dom.dom import div, span
from ux_dom.dom.src.html_string import (
    _dynamic_element_registry,
    create_dynamic_element,
    defHTML,
)


class TestTreeOwnership(unittest.TestCase):
    def test_remove_clears_parent(self):
        a, b = div(id="a"), span("x", id="b")
        a.add(b)
        self.assertIs(b.parent, a)
        a.remove(b)
        self.assertIsNone(b.parent)
        self.assertNotIn(b, a.children)

    def test_reparent_moves_between_trees(self):
        p1, p2 = div(id="p1"), div(id="p2")
        ch = span("m", id="m")
        p1.add(ch)
        p2.add(ch)
        self.assertIs(ch.parent, p2)
        self.assertNotIn(ch, p1.children)
        self.assertIn(ch, p2.children)

    def test_double_add_same_node_is_idempotent(self):
        d = div()
        s = span("s")
        d.add(s)
        d.add(s)
        self.assertEqual(d.children.count(s), 1)

    def test_delitem_clears_parent(self):
        d = div(span("a"), span("b"))
        child = d.children[0]
        del d[0]
        self.assertIsNone(child.parent)

    def test_clear_clears_parents(self):
        d = div(span("1"), span("2"))
        kids = list(d.children)
        d.clear()
        self.assertTrue(all(k.parent is None for k in kids))

    def test_setitem_replaces_child_parent(self):
        d = div(span("old", id="old"), span("keep"))
        old = d.children[0]
        new = span("new", id="new")
        d[0] = new
        self.assertIsNone(old.parent)
        self.assertIs(new.parent, d)
        self.assertIs(d.children[0], new)

    def test_setitem_reparents_from_other_tree(self):
        p1, p2 = div(id="p1"), div(id="p2")
        ch = span("m")
        p1.add(ch)
        p2.add(span("slot"))
        p2[0] = ch
        self.assertIs(ch.parent, p2)
        self.assertNotIn(ch, p1.children)


class TestDynamicElementRegistry(unittest.TestCase):
    def test_no_main_pollution_and_reuse(self):
        before = set(dir(sys.modules["__main__"]))
        defHTML("<latent-widget-xyz>q</latent-widget-xyz>")
        after = set(dir(sys.modules["__main__"]))
        leaked = [n for n in (after - before) if "Latent" in n or "Widget" in n]
        self.assertEqual(leaked, [])
        a = create_dynamic_element("latent-widget-xyz")
        b = create_dynamic_element("latent-widget-xyz")
        self.assertIs(a, b)
        self.assertIn("latent-widget-xyz", _dynamic_element_registry)


if __name__ == "__main__":
    unittest.main()
