# Copyright (c) 2026 ux-dom
"""Button — shadcn-inspired variants (pure ux-dom + Tailwind)."""

from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import button as html_button
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Button", "button_classes"]

_VARIANTS = {
    "default": "bg-slate-900 text-white hover:bg-slate-800",
    "secondary": "bg-slate-100 text-slate-900 hover:bg-slate-200",
    "outline": "border border-slate-200 bg-white hover:bg-slate-50 text-slate-900",
    "ghost": "hover:bg-slate-100 text-slate-900",
    "destructive": "bg-red-600 text-white hover:bg-red-700",
    "link": "text-sky-600 underline-offset-4 hover:underline",
}

_SIZES = {
    "sm": "h-8 px-3 text-xs",
    "md": "h-10 px-4 text-sm",
    "lg": "h-11 px-6 text-base",
    "icon": "h-10 w-10",
}


def button_classes(
    *,
    variant: str = "default",
    size: str = "md",
    className: str = "",
    disabled: bool = False,
) -> str:
    return cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium",
        "transition-colors disabled:pointer-events-none disabled:opacity-50",
        focus_ring,
        "rounded-lg",
        _VARIANTS.get(variant, _VARIANTS["default"]),
        _SIZES.get(size, _SIZES["md"]),
        className,
        "opacity-50 cursor-not-allowed" if disabled else "",
    )


class Button(Component):
    """
    ::

        Button("Save", type="submit", variant="default")
        Button("Cancel", variant="outline", hx_get="/x", hx_target="#panel")
    """

    def render(
        self,
        *children: Any,
        variant: str = "default",
        size: str = "md",
        type: str = "button",
        disabled: bool = False,
        className: str = "",
        **attrs: Any,
    ):
        kwargs = dict(attrs)
        kwargs.setdefault("type", type)
        if disabled:
            kwargs["disabled"] = True
        return html_button(
            *children,
            className=button_classes(
                variant=variant, size=size, className=className, disabled=disabled
            ),
            **kwargs,
        )
