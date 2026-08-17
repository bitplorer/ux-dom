# Copyright (c) 2026 ux-dom
"""Breadcrumb — server-rendered trail."""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import a, li, nav, ol, span
from ux_dom.ui.tokens import cn, ink, type_scale

__all__ = ["Breadcrumb"]


class Breadcrumb(Component):
    """
    items: sequence of (label, href|None). Last item is current (no link).
    """

    def render(
        self,
        items: Sequence[tuple[str, str | None]] = (),
        *,
        className: str = "",
        **attrs: Any,
    ):
        kids: list[Any] = []
        n = len(items)
        for i, (label, href) in enumerate(items):
            if i > 0:
                kids.append(
                    li(
                        span("/", className=cn("mx-2", ink["faint"])),
                        **{"aria-hidden": "true"},
                    )
                )
            if href and i < n - 1:
                kids.append(
                    li(a(label, href=href, className=cn(type_scale["caption"], "hover:text-stone-100")))
                )
            else:
                kids.append(
                    li(
                        span(label, className=cn(type_scale["caption"], "text-stone-200")),
                        **({"aria-current": "page"} if i == n - 1 else {}),
                    )
                )
        return nav(
            ol(*kids, className="flex flex-wrap items-center"),
            **{"aria-label": "Breadcrumb"},
            className=cn(className) if className else None,
            **attrs,
        )
