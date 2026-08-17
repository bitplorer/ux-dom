# Copyright (c) 2026 ux-dom
"""StatusStrip — pattern for desk status chips + message."""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import div, span
from ux_dom.ui.badge import Badge
from ux_dom.ui.tokens import cn, type_scale

__all__ = ["StatusStrip"]


class StatusStrip(Component):
    def render(
        self,
        *,
        items: Sequence[tuple[str, str]] = (),
        message: str = "",
        className: str = "",
        **attrs: Any,
    ):
        """items: (label, badge_variant) pairs."""
        chips = [Badge(label, variant=variant) for label, variant in items]
        kids: list[Any] = [div(*chips, className="flex flex-wrap items-center gap-2")]
        if message:
            kids.append(span(message, className=cn(type_scale["caption"], "ml-auto")))
        return div(
            *kids,
            className=cn(
                "flex flex-wrap items-center gap-3 rounded-lg border border-stone-800 px-3 py-2",
                className,
            ),
            **attrs,
        )
