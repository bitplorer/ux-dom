"""HTMX partial + XElement hosts (auto definitions)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, button, div, h1, p, span

from app.components.x_widgets import HelloCustom
from app.document import page

__all__ = ["HtmxDemo", "Partial"]

_N = {"v": 0}


class HtmxDemo(Component):
    routes = ["get"]

    def render(self):
        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("HTMX + XElement", className="text-3xl font-bold mt-4 mb-2"),
            p(
                "Hosts only on the page and in partials — definitions auto-collected.",
                className="text-slate-600 mb-6",
            ),
            HelloCustom(),
            button(
                "Load partial",
                type="button",
                hx_get="/htmx/Partial",
                hx_target="#panel",
                hx_swap="innerHTML",
                className="rounded-lg bg-slate-900 text-white px-4 py-2 text-sm",
                id="load-btn",
            ),
            div(
                span("panel empty — click Load", className="text-slate-400 text-sm"),
                id="panel",
                className="mt-4 min-h-[4rem] rounded-xl border border-dashed border-slate-300 p-4",
            ),
            className="max-w-2xl mx-auto px-4 py-10",
            id="htmx-demo",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="HTMX · Kit")


class Partial(Component):
    routes = ["get"]

    def render(self):
        _N["v"] += 1
        return div(
            HelloCustom(),
            span(f"partial #{_N['v']}", className="block text-xs text-slate-500 mt-2"),
            id="partial-root",
            **{"data-partial": str(_N["v"])},
        )

    @classmethod
    def get(cls):
        return cls()
