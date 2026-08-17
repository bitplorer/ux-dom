# Copyright (c) 2026 ux-dom
"""UI kit component: input — 44px target, operational border.

Matches Button target["md"] so form rows align cleanly on Host desks.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import input_
from ux_dom.ui.tokens import field_classes

__all__ = ["Input", "input_classes"]


def input_classes(*, className: str = "", invalid: bool = False) -> str:
    return field_classes(className=className, invalid=invalid)


class Input(Component):
    def render(
        self,
        *,
        type: str = "text",
        className: str = "",
        invalid: bool = False,
        **attrs: Any,
    ):
        return input_(
            type=type,
            className=input_classes(className=className, invalid=invalid),
            **attrs,
        )
