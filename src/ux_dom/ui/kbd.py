# Copyright (c) 2026 ux-dom
"""Kbd — keyboard key presentation."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import kbd as html_kbd
from ux_dom.ui.tokens import cn, surface

__all__ = ["Kbd"]


class Kbd(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return html_kbd(
            *children,
            className=cn(
                "pointer-events-none inline-flex h-5 select-none items-center gap-1",
                "rounded border border-stone-700 px-1.5 font-mono text-[10px] font-medium",
                surface["l1"],
                "text-stone-300",
                className,
            ),
            **attrs,
        )
