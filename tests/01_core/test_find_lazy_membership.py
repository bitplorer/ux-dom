"""Lazy tree find — membership must not materialize full get() lists."""

from __future__ import annotations

import unittest

from ux_dom.dom import div, span
from ux_dom.dom.src.component import Component
from ux_dom.dom.src.dom_tag import dom_tag


class TestLazyFind(unittest.TestCase):
    def test_find_is_generator(self):
        root = div(span("a"), span("b"), span("c", id="last"))
        it = root._find(span)
        self.assertFalse(isinstance(it, list))
        first = next(it)
        self.assertIsInstance(first, span)
        # remaining still iterable
        rest = list(it)
        self.assertEqual(len(rest), 2)

    def test_get_materializes_list(self):
        root = div(span("a"), span("b"))
        got = root.get(span)
        self.assertIsInstance(got, list)
        self.assertEqual(len(got), 2)

    def test_contains_short_circuits(self):
        """Deep tree: membership stops without listing every match."""
        # Build: many spans; target is early
        kids = [span(f"s{i}", id=f"id{i}") for i in range(200)]
        root = div(*kids)
        target = kids[0]

        calls = {"n": 0}
        orig = dom_tag.get

        def counting_get(self, tag=None, **kwargs):
            calls["n"] += 1
            return orig(self, tag, **kwargs)

        dom_tag.get = counting_get  # type: ignore
        try:
            self.assertTrue(target in root)
            # Must not use get() for membership anymore
            self.assertEqual(calls["n"], 0)
        finally:
            dom_tag.get = orig  # type: ignore

    def test_contains_false_no_get(self):
        root = div(span("only"))
        other = span("other")
        calls = {"n": 0}
        orig = dom_tag.get

        def counting_get(self, tag=None, **kwargs):
            calls["n"] += 1
            return orig(self, tag, **kwargs)

        dom_tag.get = counting_get  # type: ignore
        try:
            self.assertFalse(other in root)
            self.assertEqual(calls["n"], 0)
        finally:
            dom_tag.get = orig  # type: ignore

    def test_find_first_class_match(self):
        root = div(div(span("deep")))
        hit = next(root._find(span), None)
        self.assertIsNotNone(hit)
        self.assertIn("span", type(hit).__name__.lower())

    def test_component_contains_child(self):
        class Card(Component):
            def render(self):
                return div(span("title", id="t"), span("body"))

        c = Card()
        title = c.get(id="t")[0]
        self.assertTrue(title in c)
        self.assertTrue(span in c)
        self.assertFalse(span("nope") in c)


if __name__ == "__main__":
    unittest.main()
