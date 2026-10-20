# Copyright (c) 2026 UX-DOM
"""``uxdom dashboard`` — p95 latency report rendered as one self-contained page."""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "run_dashboard",
    "write_dom_dashboard",
]


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


@dataclass
class _Panel:
    id: str
    title: str
    kind: str = "html"
    order: int = 100
    html: str = ""
    svg: str = ""
    rows: list[tuple[str, Any]] = field(default_factory=list)
    tag: str = ""
    attrs: dict[str, str] = field(default_factory=dict)
    props: dict[str, Any] = field(default_factory=dict)
    span: int = 1


def _svg_bars(latencies: list[dict], *, width: int = 640, height: int = 220) -> str:
    if not latencies:
        return f'<svg viewBox="0 0 {width} {height}"><text x="16" y="40" fill="#94a3b8">No data</text></svg>'
    max_p95 = max(float(x.get("p95_ms") or 0) for x in latencies) or 1.0
    n = len(latencies)
    pad_l, pad_r, pad_t, pad_b = 48, 16, 24, 56
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    gap = 12
    bar_w = max(8, (plot_w - gap * (n - 1)) / n)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" font-family="system-ui,sans-serif">'
        f'<rect width="{width}" height="{height}" fill="#0f172a" rx="12"/>'
    ]
    for i, lat in enumerate(latencies):
        p95 = float(lat.get("p95_ms") or 0)
        h = (p95 / max_p95) * plot_h
        x = pad_l + i * (bar_w + gap)
        y = pad_t + plot_h - h
        name = str(lat.get("name") or "")
        short = name if len(name) <= 16 else name[:14] + "…"
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(h,1):.1f}" '
            f'fill="#38bdf8" rx="4"/><text x="{x + bar_w/2:.1f}" y="{height-24}" '
            f'fill="#cbd5e1" font-size="10" text-anchor="middle">{_esc(short)}</text>'
            f'<text x="{x + bar_w/2:.1f}" y="{height-10}" fill="#7dd3fc" font-size="10" '
            f'text-anchor="middle">{p95:.2f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _render_panel(p: _Panel) -> str:
    span = " span-2" if p.span >= 2 else ""
    h = f'<section class="card{span}" data-panel-id="{_esc(p.id)}"><h2>{_esc(p.title)}</h2>'
    if p.kind == "custom_element":
        tag = "".join(c for c in (p.tag or "ux-dx-slot") if c.isalnum() or c in "-")
        attrs = " ".join(f'{_esc(k)}="{_esc(v)}"' for k, v in p.attrs.items())
        h += f'<{tag} data-dom-dx-panel="{_esc(p.id)}" {attrs}></{tag}>'
    else:
        h += p.html
    return h + "</section>"


def write_dom_dashboard(out_dir: Path, report: dict[str, Any]) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lats = list(report.get("latencies") or [])
    rows = "".join(
        f"<tr><td>{_esc(x.get('name'))}</td><td>{_esc(x.get('p50_ms'))}</td>"
        f"<td><b>{_esc(x.get('p95_ms'))}</b></td><td>{_esc(x.get('p99_ms'))}</td></tr>"
        for x in lats
    )
    panels = [
        _Panel(
            id="builtin.latency",
            title="Latency",
            kind="html",
            order=10,
            span=2,
            html=_svg_bars(lats)
            + f"<table><tr><th>bench</th><th>p50</th><th>p95</th><th>p99</th></tr>{rows}</table>",
        ),
        _Panel(
            id="builtin.slot",
            title="Extension slot",
            kind="custom_element",
            order=900,
            span=2,
            tag="ux-dx-slot",
            attrs={"name": "ux-dom-main"},
        ),
    ]
    cards = "\n".join(_render_panel(p) for p in panels)
    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>uxdom DX Dashboard</title>

<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#020617;color:#e2e8f0}}
main{{max-width:960px;margin:0 auto;padding:1.5rem;display:grid;gap:1rem}}
.card{{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:1rem}}
.card.span-2{{grid-column:1/-1}}
.muted{{color:#94a3b8}}
.pill{{display:inline-block;background:#1e293b;border-radius:999px;padding:.15rem .6rem;font-size:.75rem;margin-right:.35rem}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
td,th{{padding:.4rem;border-bottom:1px solid #1e293b;text-align:left}}
</style></head><body data-dom-dx-dashboard="ux-dom">
<main id="ux-dx-root">
<h1>ux-dom DX Dashboard</h1>
<p class="muted">Pluggable shell — inline Asset CSS/JS only (no static paths).</p>
<div>
<span class="pill">PyPI ux-dom</span>
<span class="pill">import ux_dom</span>
<span class="pill">CLI uxdom</span>
</div>
{cards}
<p class="muted">Companion: <code>uxchannel dashboard</code>.</p>
</main>

</body></html>
"""
    path = out_dir / "dashboard.html"
    path.write_text(html_doc, encoding="utf-8")
    (out_dir / "dashboard.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "brand": {"pypi": "ux-dom", "import": "ux_dom", "cli": "uxdom"},
                "latencies": lats,
                "panels": [asdict(p) for p in panels],
                "assets": [],
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run_dashboard(
    *,
    out: Path | None = None,
    rounds: int = 40,
    warmup: int = 4,
    profile_rounds: int = 15,
) -> dict[str, Any]:
    from ux_dom.cli.profile import run_profile

    out_dir = Path(out) if out else Path.cwd() / "reports" / "dx"
    report = run_profile(
        out=out_dir / "p95",
        rounds=rounds,
        warmup=warmup,
        profile_rounds=profile_rounds,
    )
    path = write_dom_dashboard(out_dir, report)
    report["dashboard_html"] = str(path.resolve())
    return report
