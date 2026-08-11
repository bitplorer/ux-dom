"""Streaming HTML page (also available as compact stream on /api/stream)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div, h1, p, span

from app.components.layout import Shell
from app.document import page

__all__ = ["StreamDemo"]


class StreamDemo(Component):
    routes = ["get"]

    def render(self):
        return Shell(
            h1("Streaming HTML", className="text-3xl font-bold mb-2"),
            p(
                "This page is a normal Document. A compact stream endpoint is at ",
                span("/api/stream", className="font-mono text-sm"),
                " using ux_dom StreamingResponse.",
                className="text-slate-600 mb-4",
            ),
            div(
                p("Open /api/stream in another tab to see progressive HTML bytes."),
                className="card",
            ),
            active="stream",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Stream · Showcase")
