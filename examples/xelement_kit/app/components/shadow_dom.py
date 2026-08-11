"""
Shadow DOM components (WebComponent)
====================================

Shadow DOM means the upgraded host gets an **isolated tree** via
``attachShadow``:

* Internal markup lives under ``#shadow-root`` (open or closed).
* Page CSS does **not** pierce in (unless ``::part`` / inherited props).
* Light-DOM children of the host **project** into ``<slot>`` elements.

Python base: ``ux_dom.dom.htmlelement.WebComponent``
Browser:     ``x_element.js`` reads ``shadowroot`` / ``shadowdom`` and
             attaches a shadow root, then clones the template into it.

Pattern
-------
1. Definition must include ``shadowroot="true"|"open"`` or ``shadowdom="…"``.
2. Put ``<slot>`` / ``<slot name="…">`` where light children should appear.
3. Host usage::

       <x-profile-card>
         <span slot="title">Ada</span>
         <p>Body copy projects into the default slot.</p>
       </x-profile-card>

Load runtime::

    script(src="/assets/js/x_element.js", defer=None)
"""
from __future__ import annotations

from dataclasses import dataclass

from ux_dom.dom import div, p, slot, span, template
from ux_dom.dom.htmlelement import WebComponent

__all__ = [
    "ShellShadow",
    "ProfileCardShadow",
    "CalloutShadow",
]


@dataclass(eq=False)
class ShellShadow(WebComponent):
    """Minimal shadow shell with a single default slot.

    Definition conceptually::

        <template x-tagname="shell-shadow" shadowroot="true">
          <div>
            <span>Shadow chrome</span>
            <slot></slot>
          </div>
        </template>
    """
    tag_name = "shell-shadow"

    def render(self, tag_name: str = "shell-shadow"):
        # shadowroot="true" → open mode in x_element.js
        return template(
            div(
                span(
                    "Shadow chrome",
                    className="block text-[10px] uppercase tracking-wider text-slate-400 mb-2",
                    **{"data-part": "chrome"},
                ),
                # Default slot: light children of <x-shell-shadow> appear here.
                slot(),
                className="rounded-xl bg-slate-900 text-slate-100 p-4 text-sm",
                **{"data-dom": "shadow"},
            ),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )


@dataclass(eq=False)
class ProfileCardShadow(WebComponent):
    """Named slots example (title + default body).

    Host::

        <x-profile-card>
          <span slot="title">Grace Hopper</span>
          <p>Rear Admiral · Compiler pioneer</p>
        </x-profile-card>
    """
    tag_name = "profile-card"

    def render(self, tag_name: str = "profile-card"):
        return template(
            div(
                div(
                    # Named slot for title
                    slot(name="title"),
                    className="text-base font-semibold text-white mb-1",
                    **{"data-part": "title"},
                ),
                div(
                    slot(),  # default slot = body
                    className="text-xs text-slate-300 leading-relaxed",
                    **{"data-part": "body"},
                ),
                className=(
                    "rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 "
                    "border border-slate-700 p-5 shadow-lg max-w-sm"
                ),
                **{"data-dom": "shadow"},
            ),
            **{"x-tagname": tag_name, "shadowroot": "true"},
        )


@dataclass(eq=False)
class CalloutShadow(WebComponent):
    """Shadow callout with optional closed-mode documentation.

    Uses ``shadowdom="open"`` (synonym path) so authors see both attributes
    are accepted by :class:`WebComponent` / ``x_element.js``.
    """
    tag_name = "callout-shadow"

    def render(self, tag_name: str = "callout-shadow"):
        return template(
            div(
                p(
                    "Encapsulated callout",
                    className="font-semibold text-emerald-300 text-sm mb-1",
                ),
                p(
                    "Inner styles live in the shadow tree. Project details via the slot.",
                    className="text-xs text-slate-400 mb-2",
                ),
                div(
                    slot(),
                    className="text-sm text-slate-100 border-t border-slate-700 pt-2",
                ),
                className="rounded-xl bg-slate-950 border border-emerald-900/50 p-4",
                **{"data-dom": "shadow"},
            ),
            # shadowdom synonym (same effect as shadowroot for open mode)
            **{"x-tagname": tag_name, "shadowdom": "open"},
        )
