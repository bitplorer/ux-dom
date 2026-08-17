# Copyright (c) 2026 ux-dom
"""RadioGroup — native radios with operational styling."""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import div, input_, label, span
from ux_dom.ui.tokens import cn, focus_ring, type_scale

__all__ = ["RadioGroup"]


class RadioGroup(Component):
    def render(
        self,
        *,
        name: str,
        options: Sequence[tuple[str, str]] = (),
        value: str | None = None,
        className: str = "",
        **attrs: Any,
    ):
        kids: list[Any] = []
        for val, lab in options:
            rid = f"{name}-{val}"
            kids.append(
                label(
                    input_(
                        type="radio",
                        name=name,
                        value=val,
                        id=rid,
                        **({"checked": True} if value == val else {}),
                        className=cn(
                            "h-4 w-4 border-stone-600 bg-stone-950 accent-emerald-500",
                            focus_ring,
                        ),
                    ),
                    span(lab, className=cn("ml-2", type_scale["body"])),
                    className="flex items-center",
                    **{"for": rid},
                )
            )
        return div(
            *kids,
            role="radiogroup",
            className=cn("flex flex-col gap-2", className),
            **attrs,
        )
