# Copyright (c) 2026 ux-dom
"""Command — palette shell. Open via ux-behavior ``open("command")``.

Markup only. Filtering/commit are Host Actions + preview, not client state.
"""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import div, input_, li, ol, p, span
from ux_dom.ui.tokens import (
    cn,
    field_classes,
    overlay,
    overlay_root,
    surface,
    type_scale,
)

__all__ = ["Command"]


class Command(Component):
    def render(
        self,
        *,
        open: bool = False,
        query: str = "",
        items: Sequence[tuple[str, str]] = (),
        placeholder: str = "Type a command…",
        className: str = "",
        **attrs: Any,
    ):
        """items: (id, label) pairs already filtered by Host/preview."""
        if not open:
            return overlay_root(attrs, open=False)

        rows = [
            li(
                span(label, className=type_scale["body"]),
                className=cn(
                    "cursor-default rounded-md px-3 py-2 hover:bg-stone-800",
                    type_scale["body"],
                ),
                **{"data-command-id": cid},
            )
            for cid, label in items
        ]
        panel = div(
            input_(
                type="search",
                name="q",
                value=query,
                placeholder=placeholder,
                className=field_classes(className="border-0 bg-transparent"),
                **{"aria-label": "Command search"},
            ),
            ol(*rows, className="mt-2 max-h-64 overflow-auto") if rows else p(
                "No results", className=cn(type_scale["caption"], "p-3")
            ),
            className=cn(surface["l2"], overlay["command"], "rounded-xl p-2", className),
        )
        return overlay_root(attrs, div(className=overlay["backdrop"]), panel, open=True)
