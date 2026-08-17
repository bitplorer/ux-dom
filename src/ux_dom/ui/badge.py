# Copyright (c) 2026 ux-dom
"""Badge — operational variants on elevated tokens."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import span
from ux_dom.ui.tokens import cn

__all__ = ["Badge"]

_VARIANTS = {
    "default": "border-transparent bg-stone-100 text-stone-950",
    "secondary": "border-transparent bg-stone-800 text-stone-200",
    "outline": "text-stone-200 border-stone-600",
    "destructive": "border-transparent bg-red-600 text-white",
    "success": "border-transparent bg-emerald-600 text-white",
    "accent": "border-transparent bg-emerald-600/20 text-emerald-400",
}


class Badge(Component):
    def render(
        self,
        *children: Any,
        variant: str = "default",
        className: str = "",
        **attrs: Any,
    ):
        return span(
            *children,
            className=cn(
                "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold",
                "transition-colors",
                _VARIANTS.get(variant, _VARIANTS["default"]),
                className,
            ),
            **attrs,
        )
