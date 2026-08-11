# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Typed form elements: enums. Optional higher-level inputs over HTML tags."""
import typing as T
from enum import Enum, IntEnum

from valio import (
    EnumValidator,
    IntegerEnumValidator,
    StringEnumValidator,
    StringValidator,
)

from ux_dom.dom.src import component
from ux_dom.dom.src.htmltags import option, select

__all__ = ["EnumLabel", "EnumInput", "IntegerEnumInput", "CharEnumInput"]


class EnumLabel(component.Component):
    label = StringValidator(logger=False, debug=True)

    def render(self, label, *args, **kwargs):
        self.label = label
        return self.html_tags.label(self.label, *args, **kwargs)


class EnumInput(component.Component):
    options: Enum = EnumValidator(logger=False, debug=True)

    def render(self, *args, options, **kwargs):
        self.options = options
        return select(
            (
                option(opt.value, value=str(opt.value).capitalize())
                if len(opt.value) == 1
                else option(opt.value[0], value=str(opt.value[1]))
            )
            for opt in options
        )


class IntegerEnumInput(component.Component):
    options: IntEnum = IntegerEnumValidator(logger=False, debug=True)

    def render(self, *args, options, **kwargs):
        self.options = options
        return select(
            (
                option(opt.value, value=str(opt.value).capitalize())
                if len(opt.value) == 1
                else option(opt.value[0], value=str(opt.value[1]))
            )
            for opt in options
        )


class CharEnumInput(component.Component):
    options: T.Union[str, Enum, None] = StringEnumValidator(logger=False, debug=True)

    def render(self, *args, options, **kwargs):
        self.options = options
        return select(
            (
                option(opt.value, value=str(opt.value).capitalize())
                if len(opt.value) == 1
                else option(opt.value[0], value=str(opt.value[1]))
            )
            for opt in options
        )
