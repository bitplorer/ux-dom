# Copyright (c) 2026 ux-dom
"""DatePicker — native type=date. No Litepicker injection.

Uses elevated field_classes (44px) so date rows align with Input / Select.
Keeps live states: invalid, disabled, empty, min/max, required.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import input_
from ux_dom.ui.tokens import field_classes

__all__ = ["DatePicker"]


class DatePicker(Component):
    """
    ::

        DatePicker(name="due", value="2026-08-16")
        DatePicker(name="due", disabled=True)
        DatePicker(name="due", invalid=True)

    Native ``type=date``. Optional Litepicker is a declared Document plugin
    (Phase 2) — this component never injects it.
    """

    def render(
        self,
        *,
        name: str | None = None,
        value: str = "",
        min: str | None = None,
        max: str | None = None,
        disabled: bool = False,
        invalid: bool = False,
        required: bool = False,
        className: str = "",
        **attrs: Any,
    ):
        kwargs = dict(attrs)
        kwargs.setdefault("type", "date")
        if name is not None:
            kwargs.setdefault("name", name)
        if value:
            kwargs.setdefault("value", value)
        if min is not None:
            kwargs.setdefault("min", min)
        if max is not None:
            kwargs.setdefault("max", max)
        if disabled:
            kwargs["disabled"] = True
        if required:
            kwargs["required"] = True
        if invalid:
            kwargs.setdefault("aria-invalid", "true")
        kwargs.setdefault("data-datepicker", "native")
        if not value:
            kwargs.setdefault("data-empty", "true")

        return input_(
            className=field_classes(className=className, invalid=invalid),
            **kwargs,
        )
