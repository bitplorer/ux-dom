# Copyright (c) 2026 ux-dom
"""UI kit component: checkbox.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Checkbox` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import input_
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Checkbox"]


class Checkbox(Component):
    def render(self, *, className: str = "", **attrs: Any):
        return input_(
            type="checkbox",
            className=cn(
                "h-4 w-4 rounded border border-slate-300 text-slate-900",
                focus_ring,
                className,
            ),
            **attrs,
        )
