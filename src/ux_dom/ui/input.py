# Copyright (c) 2026 ux-dom
"""UI kit component: input.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Input` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import input_
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Input", "input_classes"]


def input_classes(*, className: str = "", invalid: bool = False) -> str:
    return cn(
        "flex h-10 w-full rounded-lg border bg-white px-3 py-2 text-sm",
        "placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-50",
        focus_ring,
        "border-red-500" if invalid else "border-slate-200",
        className,
    )


class Input(Component):
    def render(
        self,
        *,
        type: str = "text",
        className: str = "",
        invalid: bool = False,
        **attrs: Any,
    ):
        return input_(
            type=type,
            className=input_classes(className=className, invalid=invalid),
            **attrs,
        )
