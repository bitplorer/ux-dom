# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""Typed form elements: dates. Optional higher-level inputs over HTML tags."""
from dataclasses import dataclass

from ux_dom.dom.src import component

__all__ = [
    "DateLabel",
    "TimeInput",
    "DateInput",
    "WeekInput",
    "MonthInput",
    "DateTimeLocalInput",
]


@dataclass(eq=False)
class DateLabel(component.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        return self.html_tags.label(*args, **kwargs)


@dataclass(eq=False)
class TimeInput(component.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        return self.html_tags.input_(*args, type="time", **kwargs)


@dataclass(eq=False)
class DateInput(component.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        return self.html_tags.input_(*args, type="date", **kwargs)


@dataclass(eq=False)
class WeekInput(component.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        return self.html_tags.input_(*args, type="week", **kwargs)


@dataclass(eq=False)
class MonthInput(component.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        return self.html_tags.input_(*args, type="month", **kwargs)


@dataclass(eq=False)
class DateTimeLocalInput(component.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        return self.html_tags.input_(*args, type="datetime-local", **kwargs)
