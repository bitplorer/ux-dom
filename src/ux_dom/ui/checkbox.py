# Copyright (c) 2026 ux-dom
"""Checkbox — operational focus, 44px hit area via label pairing."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import input_
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Checkbox"]


class Checkbox(Component):
    def render(
        self,
        *,
        className: str = "",
        checked: bool = False,
        disabled: bool = False,
        **attrs: Any,
    ):
        kwargs = dict(attrs)
        kwargs.setdefault("type", "checkbox")
        if checked:
            kwargs["checked"] = True
        if disabled:
            kwargs["disabled"] = True
        return input_(
            className=cn(
                "h-4 w-4 shrink-0 rounded border border-stone-600 bg-stone-950",
                "text-emerald-500 accent-emerald-500",
                focus_ring,
                "disabled:cursor-not-allowed disabled:opacity-50",
                className,
            ),
            **kwargs,
        )
