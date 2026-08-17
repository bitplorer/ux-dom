# Copyright (c) 2026 ux-dom
"""Dialog — Channel-first overlay panel (no Alpine by default).

Open/close is driven by session cells set from ux-app macros
(open_overlay / close_overlay). This module only *renders* markup.
It must not import ux_app or construct Ops.

::

    # Action side — in ux-app / Host, not here
    # return open_overlay("dialog", key="lot", lot_id=lot_id)

    # Render side
    Dialog(
        open=world.kv.get("ui.overlay.open"),
        title="Lot",
        body=...,
        footer=live_button("Close", action="ui.close"),
    )
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div, h2
from ux_dom.ui.tokens import cn, overlay, surface, type_scale

__all__ = ["Dialog"]


class Dialog(Component):
    """Server-rendered dialog panel. Authority for open lives on Channel."""

    def render(
        self,
        *,
        open: bool = False,
        title: str = "",
        body: Any = None,
        footer: Any = None,
        className: str = "",
        **attrs: Any,
    ):
        # Alpine ``trigger=`` is retired. Channel-first open is a render arg.
        attrs.pop("trigger", None)
        data_open = "1" if open else "0"
        title_id = "dialog-title"
        panel_kids: list[Any] = []
        if title:
            panel_kids.append(
                h2(title, id=title_id, className=cn(type_scale["title"]))
            )
        if body is not None:
            panel_kids.append(
                div(body, className=cn("mt-2", type_scale["body"], "text-stone-300"))
            )
        if footer is not None:
            panel_kids.append(
                div(footer, className="mt-4 flex justify-end gap-2")
            )

        labelled = {"aria-labelledby": title_id} if title else {}
        panel = div(
            *panel_kids,
            role="dialog",
            **{"aria-modal": "true", "tabindex": "-1"},
            **labelled,
            className=cn(
                surface["l2"],
                "relative z-50 w-full max-w-md rounded-xl p-6",
                className,
            ),
        )

        # Closed cell: empty morph target, no client open state
        if not open:
            return div(
                id=attrs.pop("id", None) or "overlay",
                **{"data-open": "0", "data-channel-id": attrs.pop("data-channel-id", "overlay")},
                className="contents",
                **attrs,
            )

        return div(
            div(className=overlay["backdrop"], **{"data-overlay-backdrop": "1"}),
            div(panel, className=overlay["modal"]),
            id=attrs.pop("id", None) or "overlay",
            **{
                "data-open": data_open,
                "data-channel-id": attrs.pop("data-channel-id", "overlay"),
            },
            **attrs,
        )
