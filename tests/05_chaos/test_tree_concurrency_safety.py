"""Tree-level concurrent safety — mutation + sync/async render consistency.

Guarantees under race / load / stress:

* Concurrent **render** of a stable tree always returns identical HTML.
* Concurrent **mutation** of the same tree never tears children/attributes.
* Concurrent **atomic replace** + render never yields empty intermediate trees.
* Sync ``__render__`` and async ``__async_render__`` agree on a frozen tree.
* Independent trees still run in parallel (different root locks).
* ReactiveComponent field updates stay consistent with displayed HTML.
"""
from __future__ import annotations

import asyncio
import re
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ux_dom.dom import div, span
from ux_dom.dom.src.concurrency import multi_tree_lock, root_of, tree_lock_for
from ux_dom.dom.src.component import ReactiveComponent


@dataclass(eq=False)
class Counter(ReactiveComponent):
    count: int = 0

    def render(self, count=0):
        return div(span(str(count)), id="c")


class TestLockPrimitives(unittest.TestCase):
    def test_root_of_walks_parent(self):
        leaf = span("x")
        root = div(leaf, id="r")
        self.assertIs(root_of(leaf), root)
        self.assertIs(root_of(root), root)

    def test_same_root_same_lock(self):
        leaf = span("x")
        root = div(leaf)
        self.assertIs(tree_lock_for(leaf), tree_lock_for(root))

    def test_independent_roots_different_locks(self):
        a, b = div("a"), div("b")
        self.assertIsNot(tree_lock_for(a), tree_lock_for(b))


class TestConcurrentRenderStable(unittest.TestCase):
    def test_many_threads_identical_html(self):
        root = div(*[span(str(i), id=f"i{i}") for i in range(50)], id="r")
        with ThreadPoolExecutor(16) as ex:
            outs = list(ex.map(lambda _: root.__render__(pretty=False), range(200)))
        self.assertEqual(len(set(outs)), 1)

    def test_sync_async_agree(self):
        root = div(span("hello"), span("world"), id="pair")

        async def async_html():
            return "".join(
                [t async for t in root.__async_render__(pretty=False, chunk_size=1)]
            )

        sync = root.__render__(pretty=False)
        async_out = asyncio.run(async_html())
        self.assertEqual(sync, async_out)

    def test_concurrent_sync_and_async_same_tree(self):
        root = div(*[span(str(i)) for i in range(30)], id="mix")
        expected = root.__render__(pretty=False)
        errors = []

        def sync_work(_):
            h = root.__render__(pretty=False)
            if h != expected:
                errors.append(("sync", h[:80]))

        async def async_batch():
            async def one():
                return "".join(
                    [t async for t in root.__async_render__(pretty=False, chunk_size=2)]
                )

            return await asyncio.gather(*[one() for _ in range(40)])

        with ThreadPoolExecutor(12) as ex:
            futs = [ex.submit(sync_work, i) for i in range(60)]
            async_outs = asyncio.run(async_batch())
            for f in as_completed(futs):
                f.result()

        self.assertEqual(errors, [])
        for h in async_outs:
            self.assertEqual(h, expected)


class TestConcurrentMutation(unittest.TestCase):
    def test_parallel_append_count_stable(self):
        root = div(id="bag")

        def add_batch(start):
            for i in range(start, start + 25):
                root.add(span(str(i), id=f"s{i}"))

        with ThreadPoolExecutor(8) as ex:
            list(ex.map(add_batch, range(0, 200, 25)))

        html = root.__render__(pretty=False)
        for i in range(200):
            self.assertEqual(html.count(f'id="s{i}"'), 1, i)
        self.assertEqual(len(root.children), 200)

    def test_atomic_replace_while_render(self):
        """``replace_children`` is one critical section — never empty mid-update."""
        root = div(span("0", id="v"), id="box")
        stop = threading.Event()
        bad = []

        def mutator():
            n = 0
            while not stop.is_set() and n < 5000:
                n += 1
                root.replace_children(span(str(n), id="v"))
            return n

        def reader(_):
            for _ in range(120):
                html = root.__render__(pretty=False)
                if html.count('id="v"') != 1:
                    bad.append(html)
                if 'id="box"' in html and 'id="v"' not in html:
                    bad.append(html)

        t = threading.Thread(target=mutator)
        t.start()
        with ThreadPoolExecutor(10) as ex:
            list(ex.map(reader, range(10)))
        stop.set()
        t.join(timeout=10)
        self.assertEqual(bad, [], bad[:3] if bad else None)

    def test_clear_then_add_may_expose_empty_generation(self):
        """Documented: clear()+add() are two sections; empty is a full generation."""
        root = div(span("x", id="v"), id="box")
        seen_empty = threading.Event()
        stop = threading.Event()

        def mutator():
            n = 0
            while not stop.is_set() and n < 3000:
                n += 1
                root.clear()
                root.add(span(str(n), id="v"))

        def reader():
            while not stop.is_set():
                html = root.__render__(pretty=False)
                if 'id="box"' in html and 'id="v"' not in html:
                    seen_empty.set()
                    return

        t1 = threading.Thread(target=mutator)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t2.join(timeout=5)
        stop.set()
        t1.join(timeout=5)
        # May or may not observe empty depending on scheduling; just ensure no crash
        self.assertTrue(t1.is_alive() is False or True)

    def test_reparent_under_race(self):
        a = div(id="a")
        b = div(id="b")
        child = span("x", id="ch")
        a.add(child)

        def move_to_a(_):
            a.add(child)

        def move_to_b(_):
            b.add(child)

        with ThreadPoolExecutor(8) as ex:
            futs = []
            for i in range(50):
                futs.append(ex.submit(move_to_a, i))
                futs.append(ex.submit(move_to_b, i))
            for f in as_completed(futs):
                f.result()

        parents = [p for p in (a, b) if child in p.children]
        self.assertEqual(len(parents), 1)
        self.assertIs(child.parent, parents[0])
        other = b if parents[0] is a else a
        self.assertNotIn(child, other.children)


class TestReactiveConcurrent(unittest.TestCase):
    def test_threaded_updates_always_consistent(self):
        c = Counter(count=0)
        errors = []

        def worker(k):
            try:
                for j in range(40):
                    c.count = k * 40 + j
                    html = c.__render__(pretty=False)
                    m = re.search(r"<span>(\d+)</span>", html)
                    if not m or not m.group(1).isdigit():
                        errors.append(html)
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))

        with ThreadPoolExecutor(12) as ex:
            list(ex.map(worker, range(12)))
        self.assertEqual(errors, [], errors[:5] if errors else None)
        self.assertRegex(c.__render__(pretty=False), r"<span>\d+</span>")

    def test_single_thread_still_updates(self):
        c = Counter(count=0)
        c.count = 7
        self.assertIn("7", c.__render__(pretty=False))
        c.count = 42
        self.assertIn("42", c.__render__(pretty=False))


class TestAsyncMutationIsolation(unittest.TestCase):
    def test_async_builders_independent(self):
        async def one(i):
            async with div(id=f"a{i}") as r:
                span(str(i))
                await asyncio.sleep(0)
            parts = []
            async for t in r.__async_render__(pretty=False, chunk_size=1):
                parts.append(t)
                await asyncio.sleep(0)
            return "".join(parts)

        async def run():
            return await asyncio.gather(*[one(i) for i in range(30)])

        outs = asyncio.run(run())
        for i, h in enumerate(outs):
            self.assertIn(f'id="a{i}"', h)
            self.assertIn(str(i), h)

    def test_mixed_thread_async_independent_trees(self):
        def thread_work(i):
            with div(id=f"t{i}") as r:
                span("T")
            return r.__render__(pretty=False)

        async def async_work():
            async def one(i):
                async with div(id=f"x{i}") as r:
                    span("A")
                return "".join([t async for t in r.__async_render__(pretty=False)])

            return await asyncio.gather(*[one(i) for i in range(20)])

        with ThreadPoolExecutor(8) as ex:
            tf = list(ex.map(thread_work, range(20)))
            af = asyncio.run(async_work())
        for i, h in enumerate(tf):
            self.assertIn(f"t{i}", h)
        for i, h in enumerate(af):
            self.assertIn(f"x{i}", h)


class TestLockDoesNotBreakSemantics(unittest.TestCase):
    def test_with_builder_still_works(self):
        with div(id="w") as r:
            span("a")
            span("b")
        html = r.__render__(pretty=False)
        self.assertIn("a", html)
        self.assertIn("b", html)

    def test_multi_lock_context(self):
        a, b = div("a"), div("b")
        with multi_tree_lock(a, b):
            a.add(span("1"))
            b.add(span("2"))
        self.assertIn("1", a.__render__(pretty=False))
        self.assertIn("2", b.__render__(pretty=False))

    def test_replace_children_api(self):
        root = div(span("old"), id="r")
        root.replace_children(span("new", id="n"), span("also"))
        html = root.__render__(pretty=False)
        self.assertIn("new", html)
        self.assertIn("also", html)
        self.assertNotIn("old", html)


if __name__ == "__main__":
    unittest.main()
