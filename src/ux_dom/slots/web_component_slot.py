# Copyright (c) 2022–2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Advanced Alpine-assisted multi-slot WebComponent helper.

Prefer host-first :class:`~ux_dom.dom.htmlelement.WebComponent` + ``slot()``
for new apps. This helper keeps a definition-first constructor because it
carries configuration fields (slot_names, classes, css).
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from ux_dom.dom.htmlelement import XElement
from ux_dom.dom.src.htmltags import template
from ux_dom.slots.custom_element_slot import x_slot

__all__ = ["WebComponentSlot"]


@dataclass(eq=False, kw_only=True)
class WebComponentSlot(XElement):
    """Alpine-assisted slot host (definition uses ``x_slot`` inside shadow).

    ::

        panel = WebComponentSlot(
            tag_name="wcs",
            slot_names=["t"],
            classes={},
            css=[],
        )
        host = panel(...)  # host; not host-first class construction
    """

    tag_name: str
    slot_names: typing.Union[list, tuple]
    classes: dict
    css: list[str]
    slot_class: str = ""

    def __new__(cls, *args, **kwargs):
        kw = dict(kwargs)
        kw["__xelement_definition__"] = True
        return super().__new__(cls, *args, **kw)

    def __post_init__(self):
        super(WebComponentSlot, self).__post_init__(
            slot_names=self.slot_names,
            classes=self.classes,
            css=self.css,
            slot_class=self.slot_class,
        )

    def render(self, tag_name, slot_names, classes, css, slot_class):
        return template(
            x_slot(
                slotnames=slot_names,
                container_part=f"{tag_name}",
                classes=classes,
                css=css,
                exportparts="*",
                className=slot_class if slot_class != "" else False,
            ),
            **{
                "x-tagname": tag_name,
                "shadowroot": "true",
                "tabindex": "0",
            },
        )

    def __checks__(self, element):
        return XElement.__checks__(self, element)

    def __call__(self, *args, **kwargs):
        return super(WebComponentSlot, self).__call__(*args, exportparts="*", **kwargs)
