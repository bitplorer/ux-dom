"""Web Components — hosts only."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, h1, h2, p, span

from app.components.x_widgets import HelloCustom, ShadowCard
from app.document import page

__all__ = ["WcDemo"]


class WcDemo(Component):
    routes = ["get"]

    def render(self):
        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("Web Components", className="text-3xl font-bold mt-4 mb-2"),
            p(
                "HelloCustom() / ShadowCard(...) place hosts; definitions auto-emit.",
                className="text-slate-600 mb-6",
            ),
            h2("CustomElement (light DOM)", className="text-xl font-semibold mb-2"),
            HelloCustom(),
            h2("WebComponent (shadow DOM)", className="text-xl font-semibold mt-6 mb-2"),
            ShadowCard(span("Projected light content", className="text-sky-300")),
            className="max-w-2xl mx-auto px-4 py-10 space-y-3",
            id="wc",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Web Components · Kit")
