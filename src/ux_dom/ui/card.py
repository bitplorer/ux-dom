# Copyright (c) 2026 ux-dom
"""UI kit component: card.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Card` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h3, p
from ux_dom.ui.tokens import cn

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
                "rounded-xl border border-slate-200 bg-white text-slate-950 shadow-sm",
                className,
            ),
            **attrs,
        )


class CardHeader(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children, className=cn("flex flex-col space-y-1.5 p-6", className), **attrs
        )


class CardTitle(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return h3(
            *children,
            className=cn(
                "text-lg font-semibold leading-none tracking-tight", className
            ),
            **attrs,
        )


class CardDescription(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return p(*children, className=cn("text-sm text-slate-500", className), **attrs)


class CardContent(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(*children, className=cn("p-6 pt-0", className), **attrs)


class CardFooter(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children,
            className=cn("flex items-center p-6 pt-0", className),
            **attrs,
        )
