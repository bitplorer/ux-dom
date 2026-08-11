"""Systematic p95 + flamegraph artifacts for ux-dom (maintainer-facing)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ux_dom.concurrency import render_parallel
from ux_dom.dom import div, span
from ux_dom.profiling import measure_latency, run_suite

REPORTS = Path(__file__).resolve().parents[2] / "reports" / "p95_test"


class TestP95Profiling(unittest.TestCase):
    def test_latency_report_shape(self):
        root = div(*[span(str(i)) for i in range(40)], id="t")

        def op():
            root.__render__(pretty=False)

        r = measure_latency(op, name="render", rounds=40, warmup=5)
        self.assertEqual(r.name, "render")
        self.assertEqual(r.n, 40)
        self.assertGreaterEqual(r.p95_ms, r.p50_ms)
        self.assertGreaterEqual(r.p99_ms, r.p95_ms)
        self.assertGreaterEqual(r.max_ms, r.p95_ms)

    def test_suite_writes_flamegraph_artifacts(self):
        trees = [
            div(*[span(str(j)) for j in range(10)], id=f"r{i}") for i in range(12)
        ]
        frozen = div(*[span(str(i)) for i in range(50)], id="f")

        report = run_suite(
            [
                ("render_one", lambda: frozen.__render__(pretty=False)),
                ("render_par", lambda: render_parallel(trees, pretty=False)),
            ],
            out_dir=REPORTS,
            title="ux-dom p95 test",
            rounds=30,
            warmup=3,
            profile_rounds=15,
        )
        self.assertTrue((REPORTS / "latency.json").is_file())
        self.assertTrue((REPORTS / "cprofile.txt").is_file())
        self.assertTrue((REPORTS / "profile.speedscope.json").is_file())
        self.assertTrue((REPORTS / "report.html").is_file())
        # speedscope schema marker
        ss = json.loads((REPORTS / "profile.speedscope.json").read_text())
        self.assertIn("shared", ss)
        self.assertIn("profiles", ss)
        self.assertEqual(len(report["latencies"]), 2)
        # soft absolute bound: tiny trees must stay under 50ms p95 on CI
        for lat in report["latencies"]:
            self.assertLess(lat["p95_ms"], 50.0, msg=lat)

    def test_users_need_not_configure_parallel(self):
        # Day-1 path: only __render__ — no concurrency imports required
        html = div(span("ok"), id="u").__render__(pretty=False)
        self.assertIn("ok", html)


if __name__ == "__main__":
    unittest.main()
