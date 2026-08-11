# Copyright (c) 2026 ux-dom
"""UI kit component: alert.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Alert` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h5, p
from ux_dom.ui.tokens import cn

__all__ = ["Alert", "AlertTitle", "AlertDescription"]

_VARIANTS = {
    "default": "bg-white text-slate-950 border-slate-200",
    "destructive": "border-red-200 text-red-900 bg-red-50",
    "success": "border-emerald-200 text-emerald-900 bg-emerald-50",
    "warning": "border-amber-200 text-amber-900 bg-amber-50",
}


class Alert(Component):
    def render(
        self,
        *children: Any,
        variant: str = "default",
        className: str = "",
        **attrs: Any,
    ):
        return div(
            *children,
            role="alert",
            className=cn(
                "relative w-full rounded-lg border px-4 py-3 text-sm",
                _VARIANTS.get(variant, _VARIANTS["default"]),
                className,
            ),
            **attrs,
        )


class AlertTitle(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return h5(
            *children,
            className=cn("mb-1 font-medium leading-none tracking-tight", className),
            **attrs,
        )


class AlertDescription(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return p(*children, className=cn("text-sm opacity-90", className), **attrs)
