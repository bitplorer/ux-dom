# Copyright (c) 2026 ux-dom
"""Button — operational variants (pure ux-dom + Tailwind).

Defaults raised to min-h-11 (44px) and semantic accents so Host desks
no longer need local size hacks.
"""

from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import button as html_button
from ux_dom.ui.tokens import cn, focus_ring, target

__all__ = ["Button", "button_classes"]

_VARIANTS = {
    "default": "bg-stone-100 text-stone-950 hover:bg-white",
    "secondary": "bg-stone-800 text-stone-100 hover:bg-stone-700 border border-stone-700",
    "outline": "border border-stone-600 bg-transparent text-stone-100 hover:bg-stone-800/80",
    "ghost": "hover:bg-stone-800/70 text-stone-200",
    "destructive": "bg-red-600 text-white hover:bg-red-500",
    "accent": "bg-emerald-600 text-white hover:bg-emerald-500",
    "link": "text-emerald-400 underline-offset-4 hover:underline",
}

_SIZES = {
    "sm": target["sm"],
    "md": target["md"],      # 44px default
    "lg": target["lg"],
    "icon": target["icon"],
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
        Button("Hold", variant="accent", size="md")
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
