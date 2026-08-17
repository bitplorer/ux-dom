# Copyright (c) 2026 ux-dom
"""EmptyState — pattern for zero-data regions."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, p
from ux_dom.ui.tokens import cn, type_scale

__all__ = ["EmptyState"]


class EmptyState(Component):
    def render(
        self,
        title: str = "Nothing here",
        description: str = "",
        action: Any = None,
        *,
        className: str = "",
        **attrs: Any,
    ):
        kids: list[Any] = [
            p(title, className=cn(type_scale["title"], "text-stone-200")),
        ]
        if description:
            kids.append(
                p(description, className=cn(type_scale["caption"], "mt-1"))
            )
        if action is not None:
            kids.append(div(action, className="mt-4"))
        return div(
            *kids,
            className=cn(
                "flex flex-col items-center justify-center rounded-xl border border-dashed",
                "border-stone-700 px-6 py-12 text-center",
                className,
            ),
            **attrs,
        )
