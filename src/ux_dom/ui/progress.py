# Copyright (c) 2026 ux-dom
"""Progress — server-rendered bar (value 0–100)."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn

__all__ = ["Progress"]


class Progress(Component):
    def render(
        self,
        *,
        value: float = 0,
        max: float = 100,
        className: str = "",
        **attrs: Any,
    ):
        pct = 0.0 if max <= 0 else __import__("builtins").max(
            0.0, min(100.0, (float(value) / float(max)) * 100.0)
        )
        return div(
            div(
                className="h-full rounded-full bg-emerald-500 transition-all",
                style=f"width: {pct:.1f}%",
            ),
            role="progressbar",
            **{
                "aria-valuemin": "0",
                "aria-valuemax": str(max),
                "aria-valuenow": str(value),
            },
            className=cn("relative h-2 w-full overflow-hidden rounded-full bg-stone-800", className),
            **attrs,
        )
