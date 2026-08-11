# Copyright (c) 2026 ux-dom
"""Dialog — Alpine modal shell (optional HTMX body)."""

from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h2
from ux_dom.ui.button import Button
from ux_dom.ui.tokens import cn

__all__ = ["Dialog"]


class Dialog(Component):
    """
    ::

        Dialog(
            trigger=Button("Open"),
            title="Confirm",
            body=div("Are you sure?"),
            footer=Button("OK", variant="default"),
        )
    """

    def render(
        self,
        *,
        trigger: Any = None,
        title: str = "",
        body: Any = None,
        footer: Any = None,
        className: str = "",
        **attrs: Any,
    ):
        open_btn = trigger or Button("Open dialog", variant="outline")
        panel_kids: list[Any] = []
        if title:
            panel_kids.append(h2(title, className="text-lg font-semibold"))
        if body is not None:
            panel_kids.append(div(body, className="mt-2 text-sm text-slate-600"))
        if footer is not None:
            panel_kids.append(div(footer, className="mt-4 flex justify-end gap-2"))
        panel = div(
            *panel_kids,
            className=cn(
                "relative z-50 w-full max-w-md rounded-xl border border-slate-200",
                "bg-white p-6 shadow-lg",
                className,
            ),
        )
        # attrs applied to outer shell; do not let callers drop Alpine without intent
        outer = {"x-data": "{ open: false }"}
        outer.update(attrs)
        if "x-data" not in attrs and "x_data" not in attrs:
            outer["x-data"] = "{ open: false }"
        return div(
            div(open_btn, **{"@click": "open = true"}),
            div(
                div(
                    className="fixed inset-0 z-40 bg-black/40",
                    **{"@click": "open = false", "x-show": "open"},
                ),
                div(
                    panel,
                    className="fixed inset-0 z-50 flex items-center justify-center p-4",
                    **{"x-show": "open", "@keydown.escape.window": "open = false"},
                ),
                **{"x-show": "open", "x-cloak": True},
            ),
            **outer,
        )
