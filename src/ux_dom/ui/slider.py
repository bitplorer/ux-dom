# Copyright (c) 2026 ux-dom
"""Slider — native range, operational tokens. No client runtime."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, input_, span
from ux_dom.ui.tokens import cn, focus_ring, ink

__all__ = ["Slider", "slider_classes"]


def slider_classes(*, className: str = "", disabled: bool = False) -> str:
    return cn(
        "h-2 w-full cursor-pointer appearance-none rounded-full bg-stone-700",
        "accent-emerald-500",
        focus_ring,
        "disabled:cursor-not-allowed disabled:opacity-50" if disabled else "",
        className,
    )


class Slider(Component):
    def render(
        self,
        *,
        min: int | float = 0,
        max: int | float = 100,
        value: int | float | None = None,
        step: int | float = 1,
        name: str | None = None,
        disabled: bool = False,
        show_value: bool = False,
        className: str = "",
        **attrs: Any,
    ):
        kwargs = dict(attrs)
        kwargs.setdefault("min", min)
        kwargs.setdefault("max", max)
        kwargs.setdefault("step", step)
        if value is not None:
            kwargs.setdefault("value", value)
        if name is not None:
            kwargs.setdefault("name", name)
        if disabled:
            kwargs["disabled"] = True
        kwargs.setdefault("aria-valuemin", str(min))
        kwargs.setdefault("aria-valuemax", str(max))
        if value is not None:
            kwargs.setdefault("aria-valuenow", str(value))

        control = input_(
            type="range",
            className=slider_classes(className=className, disabled=disabled),
            **kwargs,
        )
        if not show_value:
            return control
        label = "" if value is None else str(value)
        return div(
            control,
            span(label, className=cn("ml-3 text-sm tabular-nums", ink["muted"])),
            className="flex items-center gap-2",
        )
