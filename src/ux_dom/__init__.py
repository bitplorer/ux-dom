# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""ux-dom — Python hypermedia **render** layer (tree → HTML / stream).

Brand lines
-----------
| Layer | Name |
|-------|------|
| **PyPI / pip** | ``ux-dom`` |
| **Import** | ``ux_dom`` |
| **CLI** | ``uxdom`` |

Ownership (residual-free)
-------------------------
**ux-dom renders.** Product delivery, host strategy, HMR process, and product
scaffold live in **ux-compose**.

| Layer | Package | Role |
|-------|---------|------|
| **Shell** | ``Document`` | HTML head/body SSoT — ``.use`` (runtime tags, CSP) |
| **Core** | ``Component``, ``Fragment``, ``ReactiveComponent`` | Build trees |
| **DOM** | ``ux_dom.dom`` | Tags, parse, ``__render__`` / ``__async_render__`` |
| **UI kit** | ``ux_dom.ui`` | Optional copy-in components |

Serialize SSoT: ``tree.__render__()`` / ``tree.__async_render__()``.
Optional HTTP adapters under ``ux_dom.response`` are **not** the product path.

Product apps::

    uxcompose create-app myapp
    uxcompose build
    uxcompose serve app:asgi
    # composition root + CSS compile + delivery — see ux-compose FLOW:
    # https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md

Pure document (no product host)::

    from ux_dom import Document, Component
    from ux_dom.runtime import XElement, Htmx, Csp
    from ux_dom.dom import div

    document = Document(head=[], body=[]).use(
        XElement(), Htmx(), Csp.auto()
    )

See ``docs/internals/SYSTEM.md`` and ux-compose FLOW:
https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md
"""

from ux_dom.dom.src.component import (
    Component,
    Fragment,
    MergeClassAttribute,
    ReactiveComponent,
)
from ux_dom.runtime import Channel, Csp, Htmx, XElement
from ux_dom.settings import Document
from ux_dom.slots.custom_element_slot import SlotElement, x_slot
from ux_dom.slots.slots import Slots
from ux_dom.slots.web_component_slot import WebComponentSlot

__all__ = [
    "Channel",
    "Component",
    "Csp",
    "Document",
    "Fragment",
    "Htmx",
    "MergeClassAttribute",
    "ReactiveComponent",
    "SlotElement",
    "Slots",
    "WebComponentSlot",
    "XElement",
    "x_slot",
]

__version__ = "0.3.0"
