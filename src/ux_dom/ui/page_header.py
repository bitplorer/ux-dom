# Copyright (c) 2026 ux-dom
"""PageHeader — pattern for desk section headers."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h1, p
from ux_dom.ui.tokens import cn, type_scale

__all__ = ["PageHeader"]


class PageHeader(Component):
    def render(
        self,
        title: str,
        description: str = "",
        actions: Any = None,
        *,
        className: str = "",
        **attrs: Any,
    ):
        left = [
            h1(title, className=cn(type_scale["display"])),
        ]
        if description:
            left.append(
                p(description, className=cn(type_scale["caption"], "mt-1"))
            )
        kids: list[Any] = [div(*left, className="space-y-1")]
        if actions is not None:
            kids.append(div(actions, className="flex items-center gap-2"))
        return div(
            *kids,
            className=cn(
                "flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between",
                className,
            ),
            **attrs,
        )
