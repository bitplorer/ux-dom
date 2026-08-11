"""Slots gallery — hosts only."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, code, div, h1, h2, li, p, span, ul
from ux_dom.dom import slot as html_slot
from ux_dom.dom import template
from ux_dom.dom.htmlelement import WebComponent
from ux_dom.slots import Slots

from app.document import page

__all__ = ["SlotsDemo"]


class NamedPanel(WebComponent):
    tag_name = "named-panel"

    def render(self, tag_name: str = "named-panel"):
        return template(
            div(
                div(
                    html_slot(name="header"),
                    className="text-sm font-semibold text-white mb-2",
                ),
                div(html_slot(), className="text-xs text-slate-300"),
                className="rounded-xl bg-slate-900 p-4 border border-slate-700",
            ),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )


class SlotsDemo(Component):
    routes = ["get"]

    def render(self):
        panel_host = NamedPanel(
            span("Header via slot=header", **{"slot": "header"}),
            span("Default slot body copy."),
        )

        slots_def = Slots(
            tag_name="multi-slot",
            slot_names=["left", "right"],
            classes={"multi-slot": "flex gap-3 p-3 bg-slate-100 rounded-xl"},
        )
        slots_host = slots_def(
            span("L", **{"slot": "left"}, className="bg-white px-2 rounded"),
            span("R", **{"slot": "right"}, className="bg-white px-2 rounded"),
        )

        return div(
            a("← Home", href="/index/Index", className="text-sm text-sky-600"),
            h1("Slots", className="text-3xl font-bold mt-4 mb-2"),
            p(
                code("NamedPanel(...)"),
                " places a host; definition is registry SSoT — no hidden list.",
                className="text-slate-600 text-sm mb-6",
            ),
            h2("Named + default slot (WebComponent)", className="text-lg font-semibold mb-2"),
            panel_host,
            h2("Slots helper (multi named)", className="text-lg font-semibold mt-8 mb-2"),
            slots_host,
            h2("Rules", className="text-lg font-semibold mt-8 mb-2"),
            ul(
                li("Construct the class → host. No ClassName()()."),
                li("Slots project for shadow hosts (WebComponent)."),
                li("Load x_element.js via document.use(XElement runtime)."),
                className="list-disc pl-6 text-sm text-slate-700 space-y-1",
            ),
            className="max-w-2xl mx-auto px-4 py-10",
            id="slots-demo",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Slots · Kit")
