"""Full Shadow DOM (WebComponent) gallery — hosts only."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, code, div, h1, h2, p, pre, span

from app.components.shadow_dom import CalloutShadow, ProfileCardShadow, ShellShadow
from app.document import page

__all__ = ["ShadowDomDemo"]


class ShadowDomDemo(Component):
    routes = ["get"]

    def render(self):
        shell_host = ShellShadow(
            span("Projected light child", className="text-sky-300")
        )
        profile_host = ProfileCardShadow(
            span("Ada Lovelace", **{"slot": "title"}),
            p("Mathematician · First programmer (notes on Babbage's engine)."),
        )
        callout_host = CalloutShadow(
            span("Slot body stays in light DOM; chrome stays in shadow.")
        )

        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("Shadow DOM · WebComponent", className="text-3xl font-bold mt-4 mb-2"),
            p(
                "Construct ",
                code("ShellShadow(...)"),
                " — hosts only; definitions auto-collected.",
                className="text-slate-600 mb-6 text-sm",
            ),
            h2("Hosts", className="text-xl font-semibold mb-3"),
            div(shell_host, profile_host, callout_host, className="space-y-4"),
            h2("Mental model", className="text-xl font-semibold mt-8 mb-2"),
            pre(
                'class ShellShadow(WebComponent):\n'
                '    tag_name = "shell-shadow"\n'
                "    def render(...): return template(..., shadowroot=...)\n\n"
                "ShellShadow(span('light child'))  # host only",
                className="text-xs bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto",
            ),
            className="max-w-2xl mx-auto px-4 py-10",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Shadow DOM · XElement Kit")
