# Copyright (c) 2026 UX-DOM
"""``uxdom profile`` — first-class DX: p95 latency + flamegraph artifacts.

Writes under ``./reports/p95/`` (or ``--out``). Does not mutate app source.
Concurrency stays library-internal; this command only *measures* render cost.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def run_profile(
    *,
    out: Path | None = None,
    rounds: int = 60,
    warmup: int = 6,
    profile_rounds: int = 30,
    open_hint: bool = True,
) -> dict[str, Any]:
    """Run the standard ux-dom p95 suite; return latency report dict."""
    from ux_dom.concurrency import render_parallel
    from ux_dom.dom import div, span
    from ux_dom.profiling import run_suite

    out_dir = Path(out) if out else Path.cwd() / "reports" / "p95"
    trees = [
        div(*[span(str(j), id=f"s{i}-{j}") for j in range(20)], id=f"r{i}")
        for i in range(24)
    ]
    frozen = div(*[span(str(i)) for i in range(80)], id="frozen")

    def render_one():
        frozen.__render__(pretty=False)

    def render_many_seq():
        for t in trees:
            t.__render__(pretty=False)

    def render_many_par():
        render_parallel(trees, pretty=False)

    def build_tree():
        with div(id="b") as r:
            for i in range(30):
                span(str(i))
        return r.__render__(pretty=False)

    report = run_suite(
        [
            ("render_frozen_80", render_one),
            ("render_24x20_seq", render_many_seq),
            ("render_24x20_internal_par", render_many_par),
            ("build_and_render_30", build_tree),
        ],
        out_dir=out_dir,
        title="ux-dom p95 suite",
        rounds=rounds,
        warmup=warmup,
        profile_rounds=profile_rounds,
    )
    report["out_dir"] = str(out_dir.resolve())
    report["artifacts"] = {
        "html": str((out_dir / "report.html").resolve()),
        "latency_json": str((out_dir / "latency.json").resolve()),
        "speedscope": str((out_dir / "profile.speedscope.json").resolve()),
        "cprofile": str((out_dir / "cprofile.txt").resolve()),
    }
    if open_hint:
        report["flamegraph_hint"] = (
            "Open profile.speedscope.json at https://www.speedscope.app "
            "for an interactive flamegraph."
        )
    return report


def format_profile_report(report: dict[str, Any]) -> str:
    lines = [
        "uxdom profile",
        "=" * 40,
        "Brand lines",
        "  PyPI / pip : ux-dom",
        "  import     : ux_dom",
        "  CLI        : uxdom",
        "-" * 40,
        "p95 latency (ms)",
    ]
    for lat in report.get("latencies") or []:
        lines.append(
            f"  {lat['name']:<28} p50={lat['p50_ms']:<8} "
            f"p95={lat['p95_ms']:<8} p99={lat['p99_ms']}"
        )
    arts = report.get("artifacts") or {}
    lines.append("-" * 40)
    lines.append(f"out: {report.get('out_dir', '')}")
    for k in ("html", "latency_json", "speedscope", "cprofile"):
        if arts.get(k):
            lines.append(f"  {k}: {arts[k]}")
    if report.get("flamegraph_hint"):
        lines.append(report["flamegraph_hint"])
    lines.append("=" * 40)
    lines.append("OK — profiling complete (app source untouched)")
    return "\n".join(lines)
