# Copyright (c) 2026 ux-dom
"""DropdownMenu — server-rendered menu when open=True (Channel-first).

Use ux-behavior ``select`` / ``open`` for open state. No Alpine.
"""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import div, li, span, ul
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.ui.tokens import cn, surface, type_scale

__all__ = ["DropdownMenu"]


def _menuitem(item: Any) -> Any:
    """``role="menuitem"`` goes on the focusable element (WAI-ARIA menu pattern)."""
    if isinstance(item, dom_tag):
        if not item.attributes.get("role"):
            item.set_attribute("role", "menuitem")
        return item
    return span(item, role="menuitem", tabindex="-1")


class DropdownMenu(Component):
    def render(
        self,
        items: Sequence[Any] = (),
        *,
        open: bool = False,
        className: str = "",
        **attrs: Any,
    ):
        if not open:
            return div(**{"data-open": "0"}, className="contents", **attrs)
        kids = [
            li(
                _menuitem(item),
                role="none",
                className=cn("rounded-md px-3 py-2 hover:bg-stone-800", type_scale["body"]),
            )
            for item in items
        ]
        return div(
            ul(*kids, role="menu", className="min-w-[10rem] py-1"),
            **{"data-open": "1"},
            className=cn(surface["l3"], "rounded-lg shadow-md", className),
            **attrs,
        )
