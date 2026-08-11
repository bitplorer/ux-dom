"""E2E: concurrency policy opt-in/opt-out with sensible defaults (ux-dom)."""

from __future__ import annotations

import asyncio
import os
import unittest

from ux_dom.concurrency import (
    build_parallel,
    configure_concurrency,
    get_concurrency_settings,
    render_async_gather,
    render_parallel,
    reset_concurrency_settings,
    should_parallelize,
)
from ux_dom.dom import div, span


class TestPolicyDefaultsAndOptOut(unittest.TestCase):
    def tearDown(self):
        reset_concurrency_settings()

    def test_defaults_parallel_on(self):
        reset_concurrency_settings()
        s = get_concurrency_settings()
        self.assertTrue(s.parallel_enabled)
        self.assertTrue(s.tree_locks_enabled)
        self.assertEqual(s.min_items_for_parallel, 2)
        self.assertTrue(should_parallelize(10))
        self.assertFalse(should_parallelize(1))

    def test_opt_out_global_sequential_same_html(self):
        roots = [div(span(str(i)), id=f"r{i}") for i in range(12)]
        expected = [r.__render__(pretty=False) for r in roots]
        configure_concurrency(parallel_enabled=False)
        self.assertFalse(should_parallelize(12))
        got = render_parallel(roots)
        self.assertEqual(got, expected)
        # build too
        def card(i):
            with div(id=f"c{i}") as r:
                span(str(i))
            return r

        roots2 = build_parallel(card, list(range(8)))
        self.assertEqual(len(roots2), 8)

    def test_per_call_opt_out(self):
        roots = [div(span(str(i)), id=f"x{i}") for i in range(10)]
        expected = [r.__render__(pretty=False) for r in roots]
        # global on, call-level off
        configure_concurrency(parallel_enabled=True)
        got = render_parallel(roots, parallel=False)
        self.assertEqual(got, expected)

    def test_per_call_opt_in_when_global_off(self):
        roots = [div(span(str(i)), id=f"y{i}") for i in range(10)]
        expected = [r.__render__(pretty=False) for r in roots]
        configure_concurrency(parallel_enabled=False)
        got = render_parallel(roots, parallel=True, max_workers=4)
        self.assertEqual(got, expected)

    def test_max_workers_one_forces_sequential(self):
        configure_concurrency(parallel_enabled=True, max_workers=1)
        self.assertFalse(should_parallelize(20))
        roots = [div(span("a"), id=f"m{i}") for i in range(5)]
        got = render_parallel(roots)
        self.assertEqual(len(got), 5)

    def test_min_items_threshold(self):
        configure_concurrency(min_items_for_parallel=5)
        self.assertFalse(should_parallelize(4))
        self.assertTrue(should_parallelize(5))

    def test_async_gather_respects_opt_out(self):
        roots = [div(span(f"a{i}"), id=f"ag{i}") for i in range(8)]
        expected = [r.__render__(pretty=False) for r in roots]
        configure_concurrency(parallel_enabled=False)

        async def run():
            return await render_async_gather(roots)

        self.assertEqual(asyncio.run(run()), expected)

    def test_env_parallel_false(self):
        os.environ["UX_DOM_PARALLEL"] = "0"
        try:
            s = reset_concurrency_settings()
            self.assertFalse(s.parallel_enabled)
            self.assertFalse(should_parallelize(10))
        finally:
            os.environ.pop("UX_DOM_PARALLEL", None)
            reset_concurrency_settings()

    def test_env_max_workers(self):
        os.environ["UX_DOM_MAX_WORKERS"] = "3"
        try:
            s = reset_concurrency_settings()
            self.assertEqual(s.max_workers, 3)
        finally:
            os.environ.pop("UX_DOM_MAX_WORKERS", None)
            reset_concurrency_settings()


class TestUsagePatternUnchanged(unittest.TestCase):
    def tearDown(self):
        reset_concurrency_settings()

    def test_render_parallel_no_kwargs_still_works(self):
        roots = [div(span("ok"), id=f"u{i}") for i in range(6)]
        htmls = render_parallel(roots)  # no policy kwargs
        self.assertEqual(len(htmls), 6)
        self.assertTrue(all("ok" in h for h in htmls))


if __name__ == "__main__":
    unittest.main()
