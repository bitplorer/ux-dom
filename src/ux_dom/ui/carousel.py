# Copyright (c) 2026 ux-dom
"""Carousel — Channel-first slide index (no Alpine).

Active index comes from the server (ux-behavior ``select``). Renders one slide.
``default=`` is accepted as an alias for ``index=`` (historical name).
"""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import button, div, span
from ux_dom.ui.tokens import cn, focus_ring, surface, type_scale

__all__ = ["Carousel"]


class Carousel(Component):
    """
    ::

        Carousel(slides=[div("One"), div("Two")], label="Highlights", index=0)
        Carousel(slides=[])  # empty state

    Index is a render argument — not client state. Advance via ux-behavior ``select``.
    """

    def render(
        self,
        slides: Sequence[Any] = (),
        *,
        index: int = 0,
        default: int | None = None,
        label: str = "Carousel",
        empty: Any = None,
        select_action: str | None = None,
        className: str = "",
        **attrs: Any,
    ):
        items = list(slides)
        if not items:
            empty_body = empty if empty is not None else span(
                "No slides",
                className=cn(type_scale["caption"]),
            )
            return div(
                empty_body,
                role="region",
                **{"aria-label": label, "data-carousel": "empty"},
                className=cn(
                    "flex min-h-[8rem] items-center justify-center rounded-xl p-6 text-center",
                    surface["l1"],
                    className,
                ),
                **attrs,
            )

        n = len(items)
        start = index if default is None else default
        idx = max(0, min(int(start), n - 1))
        body = items[idx]

        def nav_btn(visible: str, aria: str, target_idx: int, *, disabled: bool):
            ba: dict[str, Any] = {"type": "button", "aria-label": aria}
            if select_action and not disabled:
                ba["data-channel-action"] = select_action
                ba["data-args"] = f'{{"index":"{target_idx}"}}'
            if disabled:
                ba["disabled"] = True
            return button(
                visible,
                className=cn(
                    "min-h-9 rounded-md border border-stone-700 px-3 text-sm",
                    focus_ring,
                    "disabled:opacity-40",
                ),
                **ba,
            )

        return div(
            div(body, className="min-h-[8rem]"),
            div(
                nav_btn("Prev", "Previous slide", idx - 1, disabled=idx <= 0),
                div(f"{idx + 1} / {n}", className=cn("px-3", type_scale["caption"])),
                nav_btn("Next", "Next slide", idx + 1, disabled=idx >= n - 1),
                className="mt-3 flex items-center justify-center gap-2",
            ),
            role="region",
            **{
                "aria-label": label,
                "aria-roledescription": "carousel",
                "data-carousel": "channel",
            },
            className=cn(surface["l1"], "rounded-xl p-4", className),
            **attrs,
        )
