# Copyright (c) 2026 ux-dom
"""UI kit component: card — L1 operational surface.

Uses surface["l1"] + type_scale so Host cards inherit hierarchy
instead of flat local brown styles.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h3, p
from ux_dom.ui.tokens import cn, surface, type_scale, ink

__all__ = [
    "Card",
    "CardHeader",
    "CardTitle",
    "CardDescription",
    "CardContent",
    "CardFooter",
]


class Card(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children,
            className=cn(
                surface["l1"],
                "rounded-xl",
                className,
            ),
            **attrs,
        )


class CardHeader(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children,
            className=cn("flex flex-col space-y-1.5 p-5", className),
            **attrs,
        )


class CardTitle(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return h3(
            *children,
            className=cn(type_scale["title"], className),
            **attrs,
        )


class CardDescription(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return p(
            *children,
            className=cn(type_scale["caption"], ink["muted"], className),
            **attrs,
        )


class CardContent(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children,
            className=cn("p-5 pt-0", className),
            **attrs,
        )


class CardFooter(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children,
            className=cn("flex items-center gap-2 p-5 pt-0", className),
            **attrs,
        )
