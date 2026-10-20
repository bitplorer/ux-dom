# Copyright (c) 2026 ux-dom
"""Textarea — operational border, matches Input ink."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import textarea as html_textarea
from ux_dom.ui.tokens import field_classes

__all__ = ["Textarea", "textarea_classes"]


def textarea_classes(*, className: str = "", invalid: bool = False) -> str:
    return field_classes(className=className, invalid=invalid, height="min-h-[5rem]")


class Textarea(Component):
    def render(
        self,
        *children: Any,
        className: str = "",
        invalid: bool = False,
        **attrs: Any,
    ):
        return html_textarea(
            *children,
            className=textarea_classes(className=className, invalid=invalid),
            **attrs,
        )
