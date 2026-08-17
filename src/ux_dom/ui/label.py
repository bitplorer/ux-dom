# Copyright (c) 2026 ux-dom
"""Label — type_scale label role."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import label as html_label
from ux_dom.ui.tokens import cn, type_scale

__all__ = ["Label"]


class Label(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return html_label(
            *children,
            className=cn(
                type_scale["label"],
                "peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
                className,
            ),
            **attrs,
        )
