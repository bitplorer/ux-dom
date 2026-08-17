# Copyright (c) 2026 ux-dom
"""Separator — surface border."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn

__all__ = ["Separator"]


class Separator(Component):
    def render(
        self,
        *,
        orientation: str = "horizontal",
        className: str = "",
        **attrs: Any,
    ):
        if orientation == "vertical":
            return div(
                role="separator",
                **{"aria-orientation": "vertical"},
                className=cn("h-full w-px shrink-0 bg-stone-700", className),
                **attrs,
            )
        return div(
            role="separator",
            className=cn("h-px w-full shrink-0 bg-stone-700", className),
            **attrs,
        )
