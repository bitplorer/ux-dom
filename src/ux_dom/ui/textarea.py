# Copyright (c) 2026 ux-dom
"""Textarea — operational border, matches Input ink."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import textarea as html_textarea
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Textarea", "textarea_classes"]


def textarea_classes(*, className: str = "", invalid: bool = False) -> str:
    return cn(
        "flex min-h-[5rem] w-full rounded-lg border bg-stone-950/60 px-3 py-2 text-sm text-stone-100",
        "placeholder:text-stone-500 disabled:cursor-not-allowed disabled:opacity-50",
        focus_ring,
        "border-red-500/80" if invalid else "border-stone-700",
        className,
    )


class Textarea(Component):
    def render(
        self,
        *children: Any,
        className: str = "",
        invalid: bool = False,
        **attrs: Any,
    ):
        return html_textarea(
            *children,
            className=textarea_classes(className=className, invalid=invalid),
            **attrs,
        )
