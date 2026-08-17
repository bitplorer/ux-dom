# Copyright (c) 2026 ux-dom
"""Popover — Channel-first open flag (no Alpine).

Prefer Dialog/Sheet for modal work. Popover is for small anchored panels
when the Host passes open= from session.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn, surface

__all__ = ["Popover"]


class Popover(Component):
    def render(
        self,
        *children: Any,
        open: bool = False,
        className: str = "",
        **attrs: Any,
    ):
        if not open:
            return div(
                **{"data-open": "0"},
                className="contents",
                **attrs,
            )
        return div(
            *children,
            **{"data-open": "1", "role": "dialog"},
            className=cn(surface["l3"], "rounded-lg p-3 shadow-md", className),
            **attrs,
        )
