# Copyright (c) 2026 ux-dom
"""Carousel — Alpine local chrome. Empty state required. No authority kv."""

from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import button, div, span
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Carousel"]


class Carousel(Component):
    """
    ::

        Carousel(slides=[div("One"), div("Two")], label="Highlights")
        Carousel(slides=[])  # empty state

    Local index is Alpine-only. Server authority uses stamp_region + live_button.
    """

    def render(
        self,
        slides: Sequence[Any] = (),
        *,
        default: int = 0,
        label: str = "Carousel",
        empty: Any = None,
        className: str = "",
        **attrs: Any,
    ):
        items = list(slides)
        if not items:
            empty_body = empty if empty is not None else span(
                "No slides",
                className="text-sm text-slate-500",
            )
            return div(
                empty_body,
                role="region",
                **{"aria-label": label, "data-carousel": "empty"},
                className=cn(
                    "flex min-h-[8rem] items-center justify-center rounded-xl",
                    "border border-dashed border-slate-200 bg-slate-50 px-6 py-10",
                    className,
                ),
                **attrs,
            )

        n = len(items)
        start = default if 0 <= int(default) < n else 0
        track = []
        dots = []
        for i, slide in enumerate(items):
            track.append(
                div(
                    slide,
                    **{"x-show": f"i === {i}"},
                    className="w-full",
                )
            )
            dots.append(
                button(
                    span(str(i + 1), className="sr-only"),
                    type="button",
                    **{
                        "@click": f"i = {i}",
                        ":class": (
                            f"i === {i} ? 'bg-slate-900' : 'bg-slate-300 hover:bg-slate-400'"
                        ),
                    },
                    className=cn(
                        "h-2.5 w-2.5 rounded-full transition-colors",
                        focus_ring,
                    ),
                    **{"aria-label": f"Go to slide {i + 1}"},
                )
            )

        prev = button(
            "‹",
            type="button",
            **{"@click": "i = (i - 1 + n) % n", "aria-label": "Previous slide"},
            className=cn(
                "inline-flex h-10 w-10 items-center justify-center rounded-full",
                "border border-slate-200 bg-white text-lg text-slate-700",
                "hover:bg-slate-50",
                focus_ring,
            ),
        )
        nxt = button(
            "›",
            type="button",
            **{"@click": "i = (i + 1) % n", "aria-label": "Next slide"},
            className=cn(
                "inline-flex h-10 w-10 items-center justify-center rounded-full",
                "border border-slate-200 bg-white text-lg text-slate-700",
                "hover:bg-slate-50",
                focus_ring,
            ),
        )

        outer = {"x-data": f"{{ i: {start}, n: {n} }}", "data-carousel": "alpine"}
        outer.update(attrs)
        return div(
            div(
                prev,
                div(*track, className="min-h-[8rem] flex-1"),
                nxt,
                className="flex items-center gap-3",
            ),
            div(*dots, className="mt-3 flex justify-center gap-2"),
            role="region",
            **{"aria-roledescription": "carousel", "aria-label": label},
            className=cn("rounded-xl border border-slate-200 bg-white p-4", className),
            **outer,
        )
