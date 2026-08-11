# Copyright (c) 2026 ux-dom
"""UI kit component: separator.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Separator` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn

__all__ = ["Separator"]


class Separator(Component):
    def render(
        self, *, orientation: str = "horizontal", className: str = "", **attrs: Any
    ):
        if orientation == "vertical":
            cls = "h-full w-px bg-slate-200"
        else:
            cls = "h-px w-full bg-slate-200"
        return div(
            role="separator",
            className=cn("shrink-0", cls, className),
            **attrs,
        )
