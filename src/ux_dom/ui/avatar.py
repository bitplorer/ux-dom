# Copyright (c) 2026 ux-dom
"""UI kit component: avatar.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Avatar` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, img, span
from ux_dom.ui.tokens import cn

__all__ = ["Avatar", "AvatarImage", "AvatarFallback"]


class Avatar(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return div(
            *children,
            className=cn(
                "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full",
                className,
            ),
            **attrs,
        )


class AvatarImage(Component):
    def render(self, *, src: str, alt: str = "", className: str = "", **attrs: Any):
        return img(
            src=src,
            alt=alt,
            className=cn("aspect-square h-full w-full object-cover", className),
            **attrs,
        )


class AvatarFallback(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return span(
            *children,
            className=cn(
                "flex h-full w-full items-center justify-center rounded-full bg-slate-100 text-sm",
                className,
            ),
            **attrs,
        )
