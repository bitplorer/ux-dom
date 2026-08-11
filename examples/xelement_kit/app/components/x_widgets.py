"""Mixed kit widgets (short demos used by /wc, /alpine, /htmx).

For full Light / Shadow documentation see:

* ``light_dom.py`` + route ``/lightdom/LightDomDemo``
* ``shadow_dom.py`` + route ``/shadowdom/ShadowDomDemo``
* Library guide: ``docs/XELEMENT.md``

Contract reminder: ``x-tagname`` only · runtime ``x_element.js``.
"""
from __future__ import annotations

from dataclasses import dataclass

from ux_dom.dom import div, slot, span, template
from ux_dom.dom.htmlelement import AlpineComponent, CustomElement, WebComponent, XElement

__all__ = ["CounterX", "HelloCustom", "ShadowCard", "AlpineToggle"]


@dataclass(eq=False)
class CounterX(XElement):
    """Bare XElement with Alpine markup inside the template (light DOM clone)."""
    tag_name = "counter"

    def render(self, tag_name: str = "counter"):
        return template(
            div(
                span(
                    "Alpine state inside XElement definition",
                    className="block text-xs text-slate-500 mb-1",
                ),
                div(
                    span("n = ", className="opacity-70"),
                    span(className="font-bold text-xl", **{"x-text": "n"}),
                    className="flex items-center gap-1",
                ),
                **{"x-data": "{ n: 0 }"},
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class HelloCustom(CustomElement):
    """Light-DOM hello (same family as ``light_dom.HelloLight``)."""
    tag_name = "hello"

    def render(self, tag_name: str = "hello"):
        return template(
            div(
                "Hello from ",
                span("CustomElement", className="font-semibold text-sky-700"),
                " / ",
                span(f"x-{tag_name}", className="font-mono text-sm"),
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm",
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class ShadowCard(WebComponent):
    """Shadow card with default slot (see ``shadow_dom.ShellShadow``)."""
    tag_name = "shadow-card"

    def render(self, tag_name: str = "shadow-card"):
        return template(
            div(
                span(
                    "Shadow DOM card",
                    className="block text-xs uppercase tracking-wide text-slate-400 mb-2",
                ),
                slot(),
                className="p-3 rounded-xl bg-slate-900 text-slate-100",
            ),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )


@dataclass(eq=False)
class AlpineToggle(AlpineComponent):
    """Requires x-tagname + x-data (AlpineComponent checks both)."""
    tag_name = "toggle"

    def render(self, tag_name: str = "toggle"):
        return template(
            div(
                span(
                    className="font-mono font-bold",
                    **{
                        "x-text": "on ? 'ON' : 'OFF'",
                        "x-bind:class": "on ? 'text-emerald-600' : 'text-slate-400'",
                    },
                ),
                div("click to toggle", className="text-xs text-slate-500 mt-1"),
                className=(
                    "cursor-pointer select-none rounded-lg border "
                    "border-slate-200 bg-white px-4 py-3 shadow-sm"
                ),
                **{"x-data": "{ on: false }", "@click": "on = !on"},
            ),
            **{"x-tagname": tag_name},
        )
