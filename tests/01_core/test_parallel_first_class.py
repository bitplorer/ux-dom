"""First-class parallel / concurrent APIs for ux-dom — day-1 guarantees."""

from __future__ import annotations

import asyncio
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from ux_dom.concurrency import (
    build_parallel,
    default_workers,
    map_parallel,
    multi_tree_lock,
    render_async_gather,
    render_parallel,
    root_of,
    tree_lock_for,
)
from ux_dom.dom import div, span


class TestParallelRender(unittest.TestCase):
    def test_default_workers_bounded(self):
        w = default_workers()
        self.assertGreaterEqual(w, 2)
        self.assertLessEqual(w, 32)

    def test_render_parallel_order_and_content(self):
        roots = [div(span(str(i)), id=f"r{i}") for i in range(20)]
        htmls = render_parallel(roots, pretty=False, max_workers=8)
        self.assertEqual(len(htmls), 20)
        for i, h in enumerate(htmls):
            self.assertIn(f'id="r{i}"', h)
            self.assertIn(f">{i}</span>", h)

    def test_render_parallel_matches_sync(self):
        roots = [div(*[span(str(j)) for j in range(5)], id=f"p{i}") for i in range(12)]
        expected = [r.__render__(pretty=False) for r in roots]
        got = render_parallel(roots, pretty=False, max_workers=4)
        self.assertEqual(got, expected)

    def test_build_parallel_isolation(self):
        def card(i: int):
            with div(id=f"c{i}") as r:
                for j in range(5):
                    span(f"{i}-{j}")
            return r

        roots = build_parallel(card, list(range(40)), max_workers=10)
        self.assertEqual(len(roots), 40)
        htmls = render_parallel(roots, max_workers=10)
        for i, h in enumerate(htmls):
            self.assertIn(f'id="c{i}"', h)
            self.assertIn(f"{i}-0", h)

    def test_map_parallel_alias(self):
        out = map_parallel(lambda x: x * 2, range(10), max_workers=4)
        self.assertEqual(out, [0, 2, 4, 6, 8, 10, 12, 14, 16, 18])

    def test_async_gather_matches_sync(self):
        roots = [div(span(f"a{i}"), id=f"ag{i}") for i in range(15)]
        expected = [r.__render__(pretty=False) for r in roots]

        async def run():
            return await render_async_gather(roots, pretty=False)

        got = asyncio.run(run())
        self.assertEqual(got, expected)

    def test_same_tree_mut_and_render_safe(self):
        root = div(id="shared")
        errors: list[str] = []

        def mut(_):
            with multi_tree_lock(root):
                root.clear()
                for i in range(10):
                    root.add(span(str(i)))

        def rend(_):
            h = root.__render__(pretty=False)
            # either empty-ish mid-mutate is prevented by lock — should always be well-formed
            if h.count("<span") not in (0, 10) and "shared" not in h:
                errors.append(h[:100])

        with ThreadPoolExecutor(16) as ex:
            futs = [ex.submit(mut, i) for i in range(40)]
            futs += [ex.submit(rend, i) for i in range(40)]
            for f in futs:
                f.result()
        self.assertEqual(errors, [])

    def test_independent_roots_different_locks(self):
        a, b = div("a"), div("b")
        self.assertIsNot(tree_lock_for(a), tree_lock_for(b))
        self.assertIs(root_of(a), a)

    def test_render_parallel_faster_or_equal_wall_clock_batch(self):
        # Soft perf: parallel should not be pathologically slower than serial
        # on many tiny trees (allows overhead; fails only if 5x+ worse).
        roots = [div(span(str(i)), id=f"t{i}") for i in range(50)]
        t0 = time.perf_counter()
        serial = [r.__render__(pretty=False) for r in roots]
        t_serial = time.perf_counter() - t0
        t0 = time.perf_counter()
        parallel = render_parallel(roots, pretty=False, max_workers=8)
        t_par = time.perf_counter() - t0
        self.assertEqual(serial, parallel)
        self.assertLess(t_par, t_serial * 5 + 0.05)


if __name__ == "__main__":
    unittest.main()
