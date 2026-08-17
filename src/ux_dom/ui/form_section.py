# Copyright (c) 2026 ux-dom
"""FormSection — pattern for labeled field groups."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h3, p
from ux_dom.ui.tokens import cn, type_scale

__all__ = ["FormSection"]


class FormSection(Component):
    def render(
        self,
        *children: Any,
        title: str = "",
        description: str = "",
        className: str = "",
        **attrs: Any,
    ):
        head: list[Any] = []
        if title:
            head.append(h3(title, className=cn(type_scale["subtitle"])))
        if description:
            head.append(p(description, className=cn(type_scale["caption"], "mt-1")))
        return div(
            div(*head, className="mb-3") if head else None,
            div(*children, className="space-y-3"),
            className=cn(className) if className else None,
            **attrs,
        )
