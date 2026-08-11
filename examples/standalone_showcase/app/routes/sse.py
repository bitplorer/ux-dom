"""SSE demo page (stream endpoint lives on app.main)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div, h1, p

from app.components.layout import Shell
from app.document import page

__all__ = ["SseDemo"]


class SseDemo(Component):
    routes = ["get"]

    def render(self):
        return Shell(
            h1("Live SSE", className="text-3xl font-bold mb-2"),
            p(
                "HTMX SSE extension connects to /api/sse and swaps each message "
                "into the card below (you should see tick #0, #1, … every second).",
                className="text-slate-600 mb-4",
            ),
            div(
                "waiting for ticks…",
                id="tick",
                # hx-ext + sse-* require htmx-ext-sse loaded via HtmxControl(sse=True)
                hx_ext="sse",
                sse_connect="/api/sse",
                sse_swap="message",
                className="card font-mono text-sky-700 min-h-[3rem] p-4",
            ),
            active="sse",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="SSE · Showcase")
