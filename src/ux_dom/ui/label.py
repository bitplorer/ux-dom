# Copyright (c) 2026 ux-dom
"""UI kit component: label.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Label` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import label
from ux_dom.ui.tokens import cn

__all__ = ["Label"]


class Label(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return label(
            *children,
            className=cn(
                "text-sm font-medium leading-none peer-disabled:cursor-not-allowed "
                "peer-disabled:opacity-70",
                className,
            ),
            **attrs,
        )
