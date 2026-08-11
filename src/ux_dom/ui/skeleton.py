# Copyright (c) 2026 ux-dom
"""UI kit component: skeleton.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Skeleton` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn

__all__ = ["Skeleton"]


class Skeleton(Component):
    def render(self, *, className: str = "", **attrs: Any):
        return div(
            className=cn("animate-pulse rounded-md bg-slate-200", className),
            **attrs,
        )
