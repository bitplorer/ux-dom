# Copyright (c) 2026 ux-dom
"""Dialog — Channel-first overlay panel (no Alpine by default).

Open/close is a render argument (`open=`). Author macros live in
ux-behavior (`open` / `close`) or the Host — this module only *renders*
markup. It must not import ux_behavior / ux_app or construct Ops.

::

    # Action side — in ux-behavior / Host, not here
    # return open("dialog", key="lot", lot_id=lot_id)

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
from ux_dom.dom import div
from ux_dom.ui.tokens import cn, dialog_panel, overlay, overlay_id, overlay_root, surface

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
        if not open:
            return overlay_root(attrs, open=False)

        panel = dialog_panel(
            root_id=overlay_id(attrs),
            title=title,
            body=body,
            footer=footer,
            className=cn(
                surface["l2"],
                "relative z-50 w-full max-w-md rounded-xl p-6",
                className,
            ),
        )
        return overlay_root(
            attrs,
            div(className=overlay["backdrop"], **{"data-overlay-backdrop": "1"}),
            div(panel, className=overlay["modal"]),
            open=True,
        )
