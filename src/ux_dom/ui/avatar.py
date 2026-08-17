# Copyright (c) 2026 ux-dom
"""Avatar — image + fallback initials."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, img, span
from ux_dom.ui.tokens import cn, surface

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
                "flex h-full w-full items-center justify-center rounded-full text-sm",
                surface["l1"],
                className,
            ),
            **attrs,
        )
