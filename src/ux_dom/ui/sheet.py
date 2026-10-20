# Copyright (c) 2026 ux-dom
"""Sheet — Channel-first bottom/side panel (no Alpine).

Open via ux-behavior ``open("sheet", ...)``. Render with ``open=`` from session.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.ui.tokens import cn, dialog_panel, overlay, overlay_root, surface

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
            return overlay_root(attrs, open=False)

        panel_pos = (
            overlay["sheet"]
            if side == "bottom"
            else "fixed inset-y-0 right-0 z-50 w-full max-w-md"
        )
        panel = dialog_panel(
            title=title,
            body=body,
            footer=footer,
            className=cn(surface["l2"], "p-6 shadow-lg", panel_pos, className),
        )
        return overlay_root(attrs, div(className=overlay["backdrop"]), panel, open=True)
