"""Library-consistent membership pattern for Component + plain tags."""

from __future__ import annotations

import unittest

from ux_dom import Component
from ux_dom.dom import div, span, button


class Card(Component):
    def render(self, title="Hi"):
        return div(
            span(title, id="title"),
            button("Go", id="btn"),
            id="card-root",
            className="card",
        )


class TestMembershipContract(unittest.TestCase):
    def setUp(self):
        self.c = Card(title="Hi")
        self.entry = self.c._entry
        self.title = self.c.get(id="title")[0]
        self.btn = self.c.get(id="btn")[0]
        self.stranger = span("nope", id="stranger")

    # ----- matches: own only -----
    def test_matches_own_class_and_entry_type(self):
        c = self.c
        self.assertTrue(c.matches(Card))
        self.assertTrue(c.matches(div))
        self.assertFalse(c.matches(span))
        self.assertFalse(c.matches(button))

    def test_matches_own_instance_not_children(self):
        c, title, btn, entry = self.c, self.title, self.btn, self.entry
        self.assertTrue(c.matches(c))
        self.assertTrue(c.matches(entry))
        self.assertFalse(c.matches(title))
        self.assertFalse(c.matches(btn))
        self.assertFalse(c.matches(self.stranger))
        # child answers for itself
        self.assertTrue(title.matches(span))
        self.assertTrue(title.matches(title))
        self.assertFalse(title.matches(c))

    def test_matches_attrs_own_only(self):
        self.assertTrue(self.c.matches(div, id="card-root"))
        self.assertFalse(self.c.matches(span, id="title"))  # not on own/entry

    # ----- get: own + subtree -----
    def test_get_class_includes_entry_and_descendants(self):
        c = self.c
        self.assertTrue(any(x is c for x in c.get(Card)))
        self.assertTrue(any(x is c._entry for x in c.get(div)))
        spans = c.get(span)
        self.assertTrue(any(x is self.title for x in spans))
        self.assertTrue(any(x is self.btn for x in c.get(button)))

    def test_get_instance_child_and_stranger(self):
        self.assertEqual(self.c.get(self.title), [self.title])
        self.assertEqual(self.c.get(self.btn), [self.btn])
        self.assertEqual(self.c.get(self.entry), [self.entry])
        self.assertEqual(self.c.get(self.c), [self.c])
        self.assertEqual(self.c.get(self.stranger), [])

    def test_get_by_id(self):
        self.assertEqual(self.c.get(id="title")[0], self.title)
        self.assertEqual(self.c.get(id="card-root")[0], self.entry)

    # ----- in: existence shortcut -----
    def test_contains_equivalent_to_get_nonempty(self):
        c = self.c
        for item in (Card, div, span, button, c, c._entry, self.title, self.btn):
            self.assertEqual(item in c, len(c.get(item)) > 0, msg=repr(item))
        self.assertNotIn(self.stranger, c)
        self.assertEqual(self.stranger in c, len(c.get(self.stranger)) > 0)

    def test_recipe_card_get_child_vs_matches_child(self):
        """The clarifying rule users ask about."""
        c, child = self.c, self.title
        # "is this element under the card?" → get / in
        self.assertEqual(c.get(child), [child])
        self.assertIn(child, c)
        # "is this element the card itself (or its root)?" → matches
        self.assertFalse(c.matches(child))
        self.assertTrue(c.matches(c._entry))

    def test_matches_instance_respects_attrs(self):
        self.assertTrue(self.c.matches(self.entry, id="card-root"))
        self.assertFalse(self.c.matches(self.entry, id="nope"))

    def test_plain_div_same_rules(self):
        root = div(span("a", id="a"), id="r")
        child = root.get(id="a")[0]
        self.assertTrue(root.matches(div))
        self.assertFalse(root.matches(span))
        self.assertFalse(root.matches(child))
        self.assertEqual(root.get(child), [child])
        self.assertIn(child, root)
        self.assertIn(span, root)
        self.assertIn(root, root)


if __name__ == "__main__":
    unittest.main()
