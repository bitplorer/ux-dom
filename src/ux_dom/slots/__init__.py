# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Slot helpers for XElement / WebComponent.

Prefer the simple pattern for new code::

    from ux_dom.dom import div, slot, template
    from ux_dom.dom.htmlelement import WebComponent

    class Card(WebComponent):
        def render(self, tag_name: str = "card"):
            return template(
                div(slot(name="title"), slot()),
                **{"x-tagname": tag_name, "shadowroot": "true"},
            )

Advanced helpers in this package:

* ``Slots`` — multi named slots + optional CSS hrefs (WebComponent subclass)
* ``WebComponentSlot`` / ``x_slot`` — Alpine-driven dynamic slot names

Browser runtime: ``x_element.js`` (see ``docs/guides/XELEMENT.md``, ``docs/guides/HYPERMEDIA.md``).
"""

from .custom_element_slot import *  # isort: skip
from .web_component_slot import *  # isort: skip
from .slots import *  # isort: skip
