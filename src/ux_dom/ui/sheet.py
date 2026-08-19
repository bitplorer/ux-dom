# Copyright (c) 2026 ux-dom
"""Sheet — Channel-first bottom/side panel (no Alpine).

Open via ux-behavior ``open("sheet", ...)``. Render with ``open=`` from session.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h2
from ux_dom.ui.tokens import cn, overlay, surface, type_scale

__all__ = ["Sheet"]


class Sheet(Component):
    def render(
        self,
        *,
        open: bool = False,
        title: str = "",
        body: Any = None,
        footer: Any = None,
        side: str = "bottom",
        className: str = "",
        **attrs: Any,
    ):
        if not open:
            return div(
                id=attrs.pop("id", None) or "overlay",
                **{
                    "data-open": "0",
                    "data-channel-id": attrs.pop("data-channel-id", "overlay"),
                },
                className="contents",
                **attrs,
            )

        kids: list[Any] = []
        if title:
            kids.append(h2(title, className=cn(type_scale["title"])))
        if body is not None:
            kids.append(div(body, className=cn("mt-3", type_scale["body"], "text-stone-300")))
        if footer is not None:
            kids.append(div(footer, className="mt-4 flex justify-end gap-2"))

        panel_pos = (
            overlay["sheet"]
            if side == "bottom"
            else "fixed inset-y-0 right-0 z-50 w-full max-w-md"
        )
        panel = div(
            *kids,
            role="dialog",
            **{"aria-modal": "true"},
            className=cn(surface["l2"], "p-6 shadow-lg", panel_pos, className),
        )
        return div(
            div(className=overlay["backdrop"]),
            panel,
            id=attrs.pop("id", None) or "overlay",
            **{
                "data-open": "1",
                "data-channel-id": attrs.pop("data-channel-id", "overlay"),
            },
            **attrs,
        )
