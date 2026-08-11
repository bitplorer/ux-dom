"""Full Light DOM (CustomElement) gallery — hosts only."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, code, div, h1, h2, li, ol, p, pre, span, ul

from app.components.light_dom import ActionCardLight, HelloLight, InfoBannerLight
from app.document import page

__all__ = ["LightDomDemo"]


class LightDomDemo(Component):
    """Hosts only — definitions come from the class registry automatically."""

    routes = ["get"]

    def render(self):
        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("Light DOM · CustomElement", className="text-3xl font-bold mt-4 mb-2"),
            p(
                "Construct the class to place a host: ",
                code("HelloLight()"),
                " — no ",
                code("Definition()()"),
                " double call. One definition per class (registry).",
                className="text-slate-600 mb-6 text-sm",
            ),
            h2("Hosts", className="text-xl font-semibold mb-3"),
            div(
                HelloLight(),
                InfoBannerLight(),
                ActionCardLight(),
                HelloLight(),  # second host — still one definition
                className="space-y-3",
            ),
            h2("Mental model", className="text-xl font-semibold mt-8 mb-2"),
            pre(
                "class HelloLight(CustomElement):\n"
                '    tag_name = "hello-light"\n'
                "    def render(self, tag_name=...):\n"
                "        return template(..., **{\"x-tagname\": tag_name})\n\n"
                "HelloLight()   # host <x-hello-light>\n"
                "# Document auto-emits one <template x-tagname=hello-light>",
                className="text-xs bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto",
            ),
            className="max-w-2xl mx-auto px-4 py-10",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Light DOM · XElement Kit")
