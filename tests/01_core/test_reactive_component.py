"""ReactiveComponent — natural dataclass API + re-render semantics."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from ux_dom import ReactiveComponent
from ux_dom.dom import div, span


@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(span(str(count)), id="counter")

    def increment(self):
        self.count += 1


class TestReactiveNaturalAPI(unittest.TestCase):
    def test_initial_render(self):
        c = Counter(count=3)
        html = c.__render__(pretty=False)
        self.assertIn("3", html)
        self.assertIn('id="counter"', html)

    def test_field_mutation_rerenders(self):
        c = Counter(count=0)
        c.increment()
        c.increment()
        self.assertEqual(c.count, 2)
        self.assertIn("2", c.__render__(pretty=False))

    def test_str_triggers_state_check(self):
        c = Counter(count=1)
        c.count = 9
        self.assertIn("9", str(c))

    def test_constructor_kwargs_in_states(self):
        c = Counter(count=1)
        st = c._get_states()
        self.assertEqual(st.get("count"), 1)


class TestReactiveLegacyPostInit(unittest.TestCase):
    def test_post_init_super_pattern(self):
        from ux_dom.dom import p

        @dataclass(eq=False)
        class StateElement(ReactiveComponent):
            a: int

            def __post_init__(self):
                super(StateElement, self).__init__(a=self.a)

            def render(self, a):  # type: ignore[override]
                return p(a=a)

        el = StateElement(a=2)
        self.assertEqual(el.to_dict()["a"], 2)
        el.a += 1
        self.assertIn('a="3"', el.__render__(pretty=False))


class TestReactiveParentPreserved(unittest.TestCase):
    def test_child_mutation_keeps_parent_slot(self):
        c = Counter(count=1)
        root = div(c, id="root")
        self.assertIs(c.parent, root)
        c.increment()
        html = root.__render__(pretty=False)
        self.assertIn("2", html)
        self.assertIn('id="root"', html)


if __name__ == "__main__":
    unittest.main()
