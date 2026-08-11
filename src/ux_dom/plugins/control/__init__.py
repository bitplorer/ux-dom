# Copyright (c) 2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Control-plane plugins (browser interaction scripts).

Public
------
* ``HtmxControl`` — HTMX (+ optional SSE extension, idiomorph, middleware)
* ``NullControl`` — no-op control for tests / headless shells

Attach via ``Document.use(Htmx())`` where ``Htmx`` is the runtime alias
for ``HtmxControl`` (see ``ux_dom.runtime``).
"""

from ux_dom.plugins.control.htmx import HtmxControl
from ux_dom.plugins.control.null import NullControl

__all__ = ["HtmxControl", "NullControl"]
