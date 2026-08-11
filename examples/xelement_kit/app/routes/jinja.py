"""Jinja tag DSL demo — server-side expansion (orthogonal to XElement)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, code, div, h1, h2, li, p, pre, raw, ul
from ux_dom.dom.src.jinjatags import For, Var

from app.document import page

__all__ = ["JinjaDemo"]


class JinjaDemo(Component):
    routes = ["get"]

    def render(self):
        # Unexpanded Jinja source tree (for display)
        source_tree = For("item in items", li(Var("item"), className="py-0.5"))
        source_html = str(source_tree)

        # Expanded with context via Jinja render
        expanded = source_tree(items=["Alpha", "Beta", "Gamma"])
        expanded_html = str(expanded)

        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("Jinja DSL", className="text-3xl font-bold mt-4 mb-2"),
            p(
                "Server-side templates via ",
                code("ux_dom.dom.src.jinjatags"),
                " — not the browser XElement path.",
                className="text-slate-600 text-sm mb-6",
            ),
            h2("1. Python → Jinja source", className="text-lg font-semibold mb-2"),
            pre(
                source_html,
                className="text-xs bg-slate-900 text-slate-100 rounded-lg p-4 mb-4 overflow-x-auto",
                id="jinja-source",
            ),
            h2("2. Expanded with context", className="text-lg font-semibold mb-2"),
            pre(
                expanded_html,
                className="text-xs bg-emerald-950 text-emerald-100 rounded-lg p-4 overflow-x-auto",
                id="jinja-expanded",
            ),
            p(
                "API: ",
                code("For"),
                ", ",
                code("If"),
                ", ",
                code("Block"),
                ", ",
                code("Var"),
                ", ",
                code("render_jinja"),
                ", ",
                code("JinjaElement"),
                className="text-xs text-slate-500 mt-6",
            ),
            className="max-w-2xl mx-auto px-4 py-10",
            id="jinja-demo",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Jinja · Kit")
