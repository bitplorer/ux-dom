# Copyright (c) 2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Control-plane plugins (browser interaction scripts).

Public
------
* ``ChannelControl`` — stack-native semantic ``data-ux-*`` attrs (Day-1 default)
* ``HtmxControl`` — HTMX (+ optional SSE extension, idiomorph, middleware) **opt-in**
* ``NullControl`` — no-op control for tests / headless shells

Attach via ``Document.use(...)`` or hub ``use_control(...)``.
``Htmx`` is the runtime alias for ``HtmxControl`` (see ``ux_dom.runtime``).
"""

from ux_dom.plugins.control.channel import ChannelControl
from ux_dom.plugins.control.htmx import HtmxControl
from ux_dom.plugins.control.null import NullControl

__all__ = ["ChannelControl", "HtmxControl", "NullControl"]
