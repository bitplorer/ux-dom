# Copyright (c) 2026 ux-dom
"""Switch — checkbox with switch presentation classes."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import input_
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Switch"]


class Switch(Component):
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
        kwargs.setdefault("role", "switch")
        if checked:
            kwargs["checked"] = True
            kwargs["aria-checked"] = "true"
        else:
            kwargs["aria-checked"] = "false"
        if disabled:
            kwargs["disabled"] = True
        return input_(
            className=cn(
                "h-6 w-11 shrink-0 cursor-pointer appearance-none rounded-full",
                "bg-stone-700 transition-colors accent-emerald-500",
                "checked:bg-emerald-600",
                focus_ring,
                "disabled:cursor-not-allowed disabled:opacity-50",
                className,
            ),
            **kwargs,
        )
