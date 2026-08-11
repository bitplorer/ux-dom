# Copyright (c) 2026 ux-dom
"""Switch — Alpine-friendly toggle (no client framework required for static)."""

from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import button
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Switch"]


class Switch(Component):
    """Uses Alpine when x-data parent provides `on`; otherwise pure button attrs."""

    def render(
        self,
        *,
        checked: bool = False,
        className: str = "",
        **attrs: Any,
    ):
        # Prefer Alpine binding if caller passes x_bind or uses parent x-data
        return button(
            type="button",
            role="switch",
            **{"aria-checked": "true" if checked else "false"},
            className=cn(
                "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full",
                "border-2 border-transparent transition-colors",
                focus_ring,
                "bg-slate-900" if checked else "bg-slate-200",
                className,
            ),
            **attrs,
        )
