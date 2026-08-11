# Copyright (c) 2026 ux-dom
"""UI kit component: textarea.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Textarea` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import textarea
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Textarea"]


class Textarea(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return textarea(
            *children,
            className=cn(
                "flex min-h-[80px] w-full rounded-lg border border-slate-200 bg-white",
                "px-3 py-2 text-sm placeholder:text-slate-400",
                focus_ring,
                className,
            ),
            **attrs,
        )
