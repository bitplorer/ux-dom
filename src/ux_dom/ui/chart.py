# Copyright (c) 2026 ux-dom
"""Chart — SVG sparkline / bars. No Chart.js. Empty/disabled states required."""

from __future__ import annotations

from html import escape as html_escape
from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import div, raw, span
from ux_dom.ui.tokens import cn, ink, surface

__all__ = ["Chart"]


def _nums(series: Sequence[Any]) -> list[float]:
    out: list[float] = []
    for item in series:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            continue
    return out


def _spark_points(vals: list[float], *, w: int, h: int, pad: int = 4) -> str:
    if not vals:
        return ""
    lo = min(vals)
    hi = max(vals)
    span_v = hi - lo or 1.0
    inner_w = max(w - pad * 2, 1)
    inner_h = max(h - pad * 2, 1)
    n = len(vals)
    pts: list[str] = []
    for i, v in enumerate(vals):
        x = pad + (inner_w * i / (n - 1 if n > 1 else 1))
        y = pad + inner_h - ((v - lo) / span_v) * inner_h
        pts.append(f"{x:.2f},{y:.2f}")
    return " ".join(pts)


class Chart(Component):
    """
    ::

        Chart(series=[3, 5, 4, 8, 6], kind="sparkline")
        Chart(series=[2, 7, 4], kind="bar")
        Chart(series=[])  # empty
    """

    def render(
        self,
        series: Sequence[Any] = (),
        *,
        kind: str = "sparkline",
        width: int = 320,
        height: int = 96,
        label: str = "Chart",
        empty: Any = None,
        className: str = "",
        **attrs: Any,
    ):
        vals = _nums(series)
        if not vals:
            empty_body = empty if empty is not None else span(
                "No data",
                className=cn("text-sm", ink["muted"]),
            )
            return div(
                empty_body,
                role="img",
                **{"aria-label": f"{label} (empty)", "data-chart": "empty"},
                className=cn(
                    "flex items-center justify-center rounded-xl border border-dashed",
                    "border-stone-700 bg-stone-900/40",
                    className,
                ),
                **{"style": f"width:{width}px;height:{height}px"},
                **attrs,
            )

        safe_label = html_escape(str(label), quote=True)
        if kind == "bar":
            mx = max(vals) or 1.0
            gap = 4
            bw = max((width - gap * (len(vals) + 1)) / len(vals), 2)
            bars = []
            for i, v in enumerate(vals):
                bh = max((v / mx) * (height - 8), 1)
                x = gap + i * (bw + gap)
                y = height - bh - 4
                bars.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" height="{bh:.2f}" '
                    f'rx="2" fill="currentColor"/>'
                )
            inner = "".join(bars)
            kind_token = "bar"
        else:
            pts = _spark_points(vals, w=width, h=height)
            inner = (
                f'<polyline fill="none" stroke="currentColor" stroke-width="2" '
                f'stroke-linejoin="round" stroke-linecap="round" points="{pts}"/>'
            )
            kind_token = "sparkline"

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{safe_label}" '
            f'data-chart="{kind_token}" class="text-stone-100">{inner}</svg>'
        )
        return div(
            raw(svg),
            className=cn(
                "overflow-hidden rounded-xl border p-2",
                surface["l1"],
                className,
            ),
            **{"data-chart-shell": kind_token},
            **attrs,
        )
