# Copyright (c) 2026 ux-dom
"""Skeleton — loading placeholder on L1 surface language."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn

__all__ = ["Skeleton"]


class Skeleton(Component):
    def render(self, *, className: str = "", **attrs: Any):
        return div(
            className=cn(
                "animate-pulse rounded-md bg-stone-800",
                className,
            ),
            **attrs,
        )
