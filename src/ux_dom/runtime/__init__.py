# Copyright (c) 2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Document-facing runtime aliases (attach with ``document.use``).

::

    from ux_dom.runtime import XElement, Htmx, Channel, Csp

    document = Document(head=[...], body=[]).use(
        XElement(),          # x_element.js + auto custom-element defs
        Htmx(),              # HTMX script + optional middleware
        Csp.auto(),          # CSP middleware (dev/prod from DEBUG)
        Channel.optional(),  # UxChannelRuntime when ux-channel installed
    )
    document.mount(app)      # FastAPI app

These names wrap plugin implementations; they do not duplicate logic.

XElement naming (F-20 / keep name)
----------------------------------
* ``ux_dom.runtime.XElement`` — Document plugin (``document.use(XElement())``);
  loads ``x_element.js`` and registers custom-element definitions. Alias of
  ``XElementRuntime``.
* ``ux_dom.dom.XElement`` — component base class for authoring ``<x-*>`` hosts.
  Subclass it; do not construct ``XElement()`` directly.

Both names stay. Prefer the import path that matches the role (plugin vs class).
"""

from __future__ import annotations

from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.csp import Csp, CspMiddleware
from ux_dom.plugins.runtime import (
    XELEMENT_JS_URL,
    XELEMENT_STATIC_PREFIX,
    UxChannelRuntime,
    XElementRuntime,
)

XElement = XElementRuntime
Htmx = HtmxControl
# Document plugin alias — NOT ux_channel.Channel (action plane)
Channel = UxChannelRuntime

__all__ = [
    "XElement",
    "XElementRuntime",
    "Htmx",
    "HtmxControl",
    "Channel",
    "UxChannelRuntime",
    "Csp",
    "CspMiddleware",
    "XELEMENT_JS_URL",
    "XELEMENT_STATIC_PREFIX",
]
