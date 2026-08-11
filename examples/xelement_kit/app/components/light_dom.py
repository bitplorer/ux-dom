"""
Light DOM components (CustomElement)
====================================

Light DOM means the upgraded host's **children live in the page tree**:

* Global CSS applies (Tailwind classes work as usual).
* HTMX can target / swap inside the host easily.
* No style encapsulation — parent page styles affect the component.

Python base: ``ux_dom.dom.htmlelement.CustomElement``
Browser:     ``x_element.js`` clones ``<template x-tagname>`` into the host
             (no ``attachShadow``).

Pattern
-------
1. Define once: ``HelloLight("hello-light")``  → ``<template x-tagname="hello-light">``
2. Use host:    ``HelloLight("hello-light")()`` or raw ``<x-hello-light>``
3. Optional light children become extra nodes under the host after upgrade
   only if you put them in the host tag before upgrade; template body is the UI.

Load runtime in the document::

    script(src="/assets/js/x_element.js", defer=None)
"""
from __future__ import annotations

from dataclasses import dataclass

from ux_dom.dom import button, div, p, span, template
from ux_dom.dom.htmlelement import CustomElement

__all__ = [
    "HelloLight",
    "InfoBannerLight",
    "ActionCardLight",
]


@dataclass(eq=False)
class HelloLight(CustomElement):
    """Smallest useful light-DOM element.

    Definition HTML (conceptually)::

        <template x-tagname="hello-light">
          <div class="…">Hello from <strong>light DOM</strong></div>
        </template>

    Host usage::

        <x-hello-light></x-hello-light>
    """
    tag_name = "hello-light"

    def render(self, tag_name: str = "hello-light"):
        # CustomElement forbids shadowroot/shadowdom — only x-tagname.
        return template(
            div(
                span("Hello from ", className="text-slate-600"),
                span("light DOM", className="font-semibold text-sky-700"),
                span(" · CustomElement", className="text-xs text-slate-400 ml-1"),
                className=(
                    "rounded-lg border border-sky-200 bg-sky-50 "
                    "px-4 py-3 text-sm shadow-sm"
                ),
                **{"data-dom": "light"},
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class InfoBannerLight(CustomElement):
    """Composable light-DOM banner with title + body slots-as-structure.

    Because this is light DOM, you style with ordinary utility classes.
    Children passed to the host factory are *additional* light children
    (the template still provides the default chrome).
    """
    tag_name = "info-banner"

    def render(self, tag_name: str = "info-banner"):
        return template(
            div(
                p(
                    span("ℹ ", className="mr-1"),
                    span("Info", className="font-semibold", **{"data-part": "title"}),
                    className="text-sm text-slate-800 mb-1",
                ),
                p(
                    "This node is in the document light tree — inspect me in DevTools "
                    "under the host, not under #shadow-root.",
                    className="text-xs text-slate-600 leading-relaxed",
                    **{"data-part": "body"},
                ),
                className=(
                    "rounded-xl border border-amber-200 bg-amber-50 "
                    "px-4 py-3 shadow-sm"
                ),
                **{"data-dom": "light", "role": "status"},
            ),
            **{"x-tagname": tag_name},
        )


@dataclass(eq=False)
class ActionCardLight(CustomElement):
    """Interactive light-DOM card (plain button; no Shadow, no Alpine required)."""
    tag_name = "action-card"

    def render(self, tag_name: str = "action-card"):
        return template(
            div(
                p("Action card (light DOM)", className="font-medium text-slate-900"),
                p(
                    "Click counts stay in the page tree — HTMX can replace this host whole.",
                    className="text-xs text-slate-500 mt-1 mb-3",
                ),
                button(
                    "Click me",
                    type="button",
                    className=(
                        "rounded-md bg-slate-900 text-white text-xs "
                        "px-3 py-1.5 hover:bg-slate-800"
                    ),
                    # plain progressive enhancement; Alpine optional elsewhere
                    onclick="this.dataset.n=(+this.dataset.n||0)+1; this.textContent='Clicked '+this.dataset.n",
                    **{"data-n": "0"},
                ),
                className=(
                    "rounded-xl border border-slate-200 bg-white p-4 shadow-sm "
                    "max-w-sm"
                ),
                **{"data-dom": "light"},
            ),
            **{"x-tagname": tag_name},
        )
