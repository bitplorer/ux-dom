# Copyright (c) 2026 ux-dom
"""Pagination — Channel-friendly page controls (data-channel-action optional)."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import button, div, span
from ux_dom.ui.tokens import cn, focus_ring, target

__all__ = ["Pagination"]


class Pagination(Component):
    def render(
        self,
        *,
        page: int = 1,
        total_pages: int = 1,
        select_action: str | None = None,
        className: str = "",
        **attrs: Any,
    ):
        page = max(1, min(page, max(1, total_pages)))

        def page_btn(label: str, p: int, *, disabled: bool = False):
            ba: dict[str, Any] = {"type": "button"}
            if select_action and not disabled:
                ba["data-channel-action"] = select_action
                ba["data-args"] = f'{{"page":"{p}"}}'
            if disabled:
                ba["disabled"] = True
            return button(
                label,
                className=cn(
                    target["sm"],
                    "rounded-md border border-stone-700 px-3",
                    focus_ring,
                    "disabled:opacity-40",
                    "bg-stone-900 text-stone-100 hover:bg-stone-800",
                ),
                **ba,
            )

        return div(
            page_btn("Prev", page - 1, disabled=page <= 1),
            span(f"{page} / {total_pages}", className="px-3 text-sm text-stone-400 tabular-nums"),
            page_btn("Next", page + 1, disabled=page >= total_pages),
            className=cn("flex items-center gap-2", className),
            **attrs,
        )
