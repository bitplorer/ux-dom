# Copyright (c) 2026 UX-DOM
"""Pluggable ``uxdom dashboard`` — no static path surface for extensions.

Plugins / panels carry **inline** CSS/JS via :class:`Asset`. You never pass
``/static/...`` URLs for day-1 DX.
"""

from __future__ import annotations

import html
import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

__all__ = [
    "Asset",
    "Panel",
    "register_panel",
    "unregister_panel",
    "clear_panels",
    "register_assets",
    "configure_dashboard",
    "run_dashboard",
    "write_dom_dashboard",
]


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


@dataclass(frozen=True)
class Asset:
    """Inline CSS/JS — not a file path."""

    kind: str
    content: str
    name: str = ""

    @staticmethod
    def css(content: str, *, name: str = "") -> "Asset":
        return Asset(kind="css", content=content, name=name)

    @staticmethod
    def js(content: str, *, name: str = "") -> "Asset":
        return Asset(kind="js", content=content, name=name)

    @staticmethod
    def ce(content: str, *, name: str = "") -> "Asset":
        return Asset(kind="ce", content=content, name=name or "ce")


@dataclass
class Panel:
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


_PANELS: dict[str, Panel] = {}
_ASSETS: list[Asset] = []
_LOCK = threading.RLock()
_BUILTINS = True


def configure_dashboard(*, builtins: bool | None = None) -> None:
    global _BUILTINS
    with _LOCK:
        if builtins is not None:
            _BUILTINS = bool(builtins)


def register_panel(panel: Panel, *, replace: bool = True) -> None:
    with _LOCK:
        if not replace and panel.id in _PANELS:
            raise ValueError(panel.id)
        _PANELS[panel.id] = panel


def unregister_panel(panel_id: str) -> bool:
    with _LOCK:
        return _PANELS.pop(panel_id, None) is not None


def clear_panels() -> None:
    with _LOCK:
        _PANELS.clear()
        _ASSETS.clear()


def register_assets(*assets: Asset) -> None:
    """Attach inline CSS/JS/CE definitions (no paths)."""
    with _LOCK:
        _ASSETS.extend(assets)


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


def _render_panel(p: Panel) -> str:
    span = " span-2" if p.span >= 2 else ""
    h = f'<section class="card{span}" data-panel-id="{_esc(p.id)}"><h2>{_esc(p.title)}</h2>'
    if p.kind == "svg":
        h += p.svg
    elif p.kind == "table":
        rows = "".join(
            f"<tr><th>{_esc(a)}</th><td><code>{_esc(b)}</code></td></tr>" for a, b in p.rows
        )
        h += f"<table>{rows}</table>"
    elif p.kind == "custom_element":
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
    panels: list[Panel] = []
    if _BUILTINS:
        rows = "".join(
            f"<tr><td>{_esc(x.get('name'))}</td><td>{_esc(x.get('p50_ms'))}</td>"
            f"<td><b>{_esc(x.get('p95_ms'))}</b></td><td>{_esc(x.get('p99_ms'))}</td></tr>"
            for x in lats
        )
        panels.append(
            Panel(
                id="builtin.latency",
                title="Latency",
                kind="html",
                order=10,
                span=2,
                html=_svg_bars(lats)
                + f"<table><tr><th>bench</th><th>p50</th><th>p95</th><th>p99</th></tr>{rows}</table>",
            )
        )
        panels.append(
            Panel(
                id="builtin.slot",
                title="Extension slot",
                kind="custom_element",
                order=900,
                span=2,
                tag="ux-dx-slot",
                attrs={"name": "ux-dom-main"},
            )
        )
    with _LOCK:
        panels.extend(_PANELS.values())
        assets = list(_ASSETS)
    panels.sort(key=lambda p: (p.order, p.id))
    cards = "\n".join(_render_panel(p) for p in panels)
    style_bits = []
    script_bits = []
    for a in assets:
        kind = a.kind.lower()
        if kind in ("css", "inline_css"):
            style_bits.append(f"<style data-dom-dx-asset=\"{_esc(a.name)}\">{a.content}</style>")
        else:
            script_bits.append(
                f"<script data-dom-dx-asset=\"{_esc(a.name)}\">\n{a.content}\n</script>"
            )
    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>uxdom DX Dashboard</title>
{''.join(style_bits)}
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
{''.join(script_bits)}
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
                "assets": [asdict(a) for a in assets],
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
