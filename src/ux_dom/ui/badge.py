# Copyright (c) 2026 ux-dom
"""UI kit component: badge.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Badge` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import span
from ux_dom.ui.tokens import cn

__all__ = ["Badge"]

_VARIANTS = {
    "default": "border-transparent bg-slate-900 text-slate-50",
    "secondary": "border-transparent bg-slate-100 text-slate-900",
    "outline": "text-slate-950 border-slate-200",
    "destructive": "border-transparent bg-red-600 text-white",
    "success": "border-transparent bg-emerald-600 text-white",
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
                "inline-flex items-center rounded-md border px-2.5 py-0.1 text-xs font-semibold",
                "transition-colors",
                _VARIANTS.get(variant, _VARIANTS["default"]),
                className,
            ),
            **attrs,
        )
