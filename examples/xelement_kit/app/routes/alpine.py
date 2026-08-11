"""Alpine.js + AlpineComponent — hosts only."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, h1, h2, p

from app.components.x_widgets import AlpineToggle, CounterX
from app.document import page

__all__ = ["AlpineDemo"]


class AlpineDemo(Component):
    routes = ["get"]

    def render(self):
        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("Alpine + XElement", className="text-3xl font-bold mt-4 mb-2"),
            p(
                "Construct Alpine components as hosts; definitions are registry SSoT.",
                className="text-slate-600 mb-6",
            ),
            h2("x-counter", className="text-lg font-semibold"),
            CounterX(),
            h2("x-toggle", className="text-lg font-semibold mt-6"),
            AlpineToggle(),
            className="max-w-2xl mx-auto px-4 py-10 space-y-3",
            id="alpine",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Alpine · Kit")
