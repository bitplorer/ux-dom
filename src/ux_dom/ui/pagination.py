# Copyright (c) 2026 ux-dom
"""Pagination — Channel-friendly page controls (data-channel-action optional)."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, span
from ux_dom.ui.tokens import cn, nav_button

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

        return div(
            nav_button(
                "Prev",
                action=select_action,
                args={"page": page - 1},
                disabled=page <= 1,
            ),
            span(f"{page} / {total_pages}", className="px-3 text-sm text-stone-400 tabular-nums"),
            nav_button(
                "Next",
                action=select_action,
                args={"page": page + 1},
                disabled=page >= total_pages,
            ),
            className=cn("flex items-center gap-2", className),
            **attrs,
        )
