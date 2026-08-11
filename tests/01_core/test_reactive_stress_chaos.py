"""ReactiveComponent — stress, chaos, pentest, load, edge cases."""

from __future__ import annotations

import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from ux_dom import ReactiveComponent
from ux_dom.dom import div, span


@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(span(str(count)), id="counter")

    def increment(self):
        self.count += 1


@dataclass(eq=False)
class MultiRoot(ReactiveComponent):
    n: int = 0

    def render(self, n=0):
        return [span(str(n), id="a"), span(str(n + 1), id="b")]


@dataclass(eq=False)
class Boom(ReactiveComponent):
    n: int = 0

    def render(self, n=0):
        if n >= 99:
            raise RuntimeError("render boom")
        return div(str(n), id="boom")


@dataclass(eq=False)
class XssBox(ReactiveComponent):
    text: str = ""

    def render(self, text=""):
        return div(text, id="xss")


@dataclass(eq=False)
class ListBox(ReactiveComponent):
    items: list = field(default_factory=list)

    def render(self, items=None):
        items = items if items is not None else []
        return div(*[span(str(x)) for x in items], id="list")


@dataclass(eq=False)
class NestedOuter(ReactiveComponent):
    v: int = 0

    def render(self, v=0):
        return div(NestedInner(v=v), id="outer")


@dataclass(eq=False)
class NestedInner(ReactiveComponent):
    v: int = 0

    def render(self, v=0):
        return span(str(v), id="inner")


class TestReactiveMultiRoot(unittest.TestCase):
    def test_multi_root_initial_and_rerender(self):
        m = MultiRoot(n=1)
        self.assertIs(m._entry, m)
        html = m.__render__(pretty=False)
        self.assertIn(">1<", html)
        self.assertIn(">2<", html)
        m.n = 5
        html2 = m.__render__(pretty=False)
        self.assertIn(">5<", html2)
        self.assertIn(">6<", html2)
        self.assertIs(m._entry, m)
        self.assertFalse(isinstance(m._entry, list))

    def test_multi_root_parent_slot(self):
        m = MultiRoot(n=0)
        root = div(m, id="root")
        m.n = 3
        html = root.__render__(pretty=False)
        self.assertIn('id="root"', html)
        self.assertIn(">3<", html)
        self.assertIs(m.parent, root)


class TestReactiveFailClosed(unittest.TestCase):
    def test_render_exception_keeps_previous_tree(self):
        b = Boom(n=1)
        html_before = b.__render__(pretty=False)
        self.assertIn(">1<", html_before)
        b.n = 99
        with self.assertRaises(RuntimeError):
            b.__render__(pretty=False)
        self.assertIsNotNone(getattr(b, "_entry", None))
        # state must roll back with the tree (no silent desync)
        self.assertEqual(b.n, 1)
        try:
            html_after = b.__render__(pretty=False)
        except Exception as e:
            self.fail("component unusable after failed render: %r" % (e,))
        self.assertIn(">1<", html_after)

    def test_render_exception_parent_preserved(self):
        b = Boom(n=0)
        root = div(b, id="root")
        b.n = 99
        with self.assertRaises(RuntimeError):
            root.__render__(pretty=False)
        b.n = 2
        html = root.__render__(pretty=False)
        self.assertIn('id="root"', html)
        self.assertIn(">2<", html)


class TestReactivePentestXSS(unittest.TestCase):
    def test_script_escaped(self):
        payload = "<script>alert(1)</script>"
        box = XssBox(text=payload)
        html = box.__render__(pretty=False)
        self.assertNotIn("<script>", html)  # must be escaped
        self.assertTrue("script" in html and "alert" in html and "<script>" not in html)

    def test_attr_injection_in_text_not_raw(self):
        payload = '"><img src=x onerror=alert(1)>'
        box = XssBox(text=payload)
        html = box.__render__(pretty=False)
        self.assertNotIn("<img", html)
        self.assertTrue(("<" in html) or ("&" + "quot;" in html) or ("&#" in html))

    def test_many_evil_payloads(self):
        payloads = [
            "<svg/onload=alert(1)>",
            "javascript:alert(1)",
            "{{7*7}}",
            "${7*7}",
            "\x00null",
            "a" * 5000,
            "' OR '1'='1",
        ]
        for pld in payloads:
            box = XssBox(text=pld)
            html = box.__render__(pretty=False)
            self.assertTrue(html.startswith("<div"), pld[:40])


class TestReactiveMutableState(unittest.TestCase):
    def test_list_append_triggers_rerender(self):
        box = ListBox(items=[1])
        self.assertEqual(box.__render__(pretty=False).count("<span>"), 1)
        box.items.append(2)
        html = box.__render__(pretty=False)
        self.assertEqual(html.count("<span>"), 2)
        self.assertIn(">2<", html)

    def test_list_reassign(self):
        box = ListBox(items=[1])
        box.items = [9, 8, 7]
        html = box.__render__(pretty=False)
        self.assertEqual(html.count("<span>"), 3)


class TestReactiveParentAndExtras(unittest.TestCase):
    def test_parent_survives_hundred_updates(self):
        c = Counter(count=0)
        root = div(c, id="root")
        for i in range(100):
            c.count = i
            root.__render__(pretty=False)
        self.assertIs(c.parent, root)
        self.assertIn(">99<", root.__render__(pretty=False))

    def test_extra_child_on_entry_preserved(self):
        c = Counter(count=1)
        c._entry.add(span("extra", id="ex"))
        c.count = 2
        html = c.__render__(pretty=False)
        self.assertIn(">2<", html)
        self.assertIn('id="ex"', html)


class TestReactiveNested(unittest.TestCase):
    def test_nested_outer_updates_inner_value(self):
        o = NestedOuter(v=1)
        self.assertIn(">1<", o.__render__(pretty=False))
        o.v = 7
        html = o.__render__(pretty=False)
        self.assertIn('id="outer"', html)
        self.assertIn(">7<", html)


class TestReactiveLoadConcurrency(unittest.TestCase):
    def test_threaded_increments_no_crash(self):
        c = Counter(count=0)
        errors = []

        def worker(k):
            try:
                for j in range(50):
                    c.count = k * 50 + j
                    c.__render__(pretty=False)
            except Exception as e:
                errors.append(repr(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [], errors[:3] if errors else None)
        self.assertIn("<div", c.__render__(pretty=False))

    def test_pool_load(self):
        c = Counter(count=0)

        def one(i):
            c.count = i
            c.__render__(pretty=False)
            return True

        with ThreadPoolExecutor(max_workers=16) as ex:
            futs = [ex.submit(one, i) for i in range(200)]
            for f in as_completed(futs):
                self.assertTrue(f.result())


class TestReactiveReentrancyAndEdges(unittest.TestCase):
    def test_none_to_value(self):
        @dataclass(eq=False)
        class N(ReactiveComponent):
            text = None  # type: ignore

            def render(self, text=None):
                return div(text if text is not None else "empty", id="n")

        # use proper optional field
        @dataclass(eq=False)
        class N2(ReactiveComponent):
            text: object = None

            def render(self, text=None):
                return div(text if text is not None else "empty", id="n")

        n = N2()
        self.assertIn("empty", n.__render__(pretty=False))
        n.text = "hi"
        self.assertIn("hi", n.__render__(pretty=False))

    def test_zero_and_false_states(self):
        @dataclass(eq=False)
        class Z(ReactiveComponent):
            n: int = 1
            flag: bool = True

            def render(self, n=1, flag=True):
                return div(str(n), str(flag), id="z")

        z = Z()
        z.n = 0
        z.flag = False
        html = z.__render__(pretty=False)
        self.assertIn("0", html)
        self.assertIn("False", html)

    def test_to_dict_excludes_dom_internals(self):
        c = Counter(count=3)
        d = c.to_dict()
        self.assertEqual(d.get("count"), 3)
        self.assertNotIn("children", d)
        self.assertNotIn("parent", d)

    def test_str_and_render_agree(self):
        c = Counter(count=4)
        c.count = 5
        self.assertIn("5", str(c))
        self.assertIn("5", c.__render__(pretty=False))

    def test_set_attribute_does_not_drop_state(self):
        c = Counter(count=2)
        c.set_attribute("class", "x")
        html = c.__render__(pretty=False)
        self.assertIn("2", html)
        c.count = 8
        html = c.__render__(pretty=False)
        self.assertIn("8", html)


class TestReactiveChaosStorm(unittest.TestCase):
    def test_alternating_good_bad_renders(self):
        b = Boom(n=0)
        root = div(b, id="r")
        for i in range(30):
            if i % 5 == 4:
                b.n = 99
                with self.assertRaises(RuntimeError):
                    root.__render__(pretty=False)
                b.n = i
            else:
                b.n = i
                html = root.__render__(pretty=False)
                self.assertIn(">%d<" % i, html)
        self.assertIs(b.parent, root)

    def test_rapid_identity_flip(self):
        c = Counter(count=0)
        for i in range(500):
            c.count = i % 7
        html = c.__render__(pretty=False)
        self.assertIn(">%d<" % c.count, html)


if __name__ == "__main__":
    unittest.main()
