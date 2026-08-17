# Copyright (c) 2026 ux-dom
"""Select — matches Input height (min-h-11)."""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import option, select as html_select
from ux_dom.ui.tokens import cn, field_classes

__all__ = ["Select"]


class Select(Component):
    def render(
        self,
        *,
        options: Sequence[tuple[str, str]] = (),
        value: str | None = None,
        className: str = "",
        invalid: bool = False,
        **attrs: Any,
    ):
        kids = [
            option(label, value=val, selected=(value is not None and val == value))
            for val, label in options
        ]
        return html_select(
            *kids,
            className=field_classes(className=className, invalid=invalid),
            **attrs,
        )
