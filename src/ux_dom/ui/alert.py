# Copyright (c) 2026 ux-dom
"""Alert — surface-aware callout."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h5, p
from ux_dom.ui.tokens import cn, status, type_scale

__all__ = ["Alert", "AlertTitle", "AlertDescription"]

_VARIANTS = {
    "default": status["neutral"],
    "destructive": status["danger"],
    "warning": status["warning"],
    "success": status["success"],
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
            className=cn(type_scale["subtitle"], "mb-1", className),
            **attrs,
        )


class AlertDescription(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return p(
            *children,
            className=cn(type_scale["body"], "opacity-90", className),
            **attrs,
        )
