# Copyright (c) 2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Control-plane plugins (browser interaction scripts).

Public
------
* ``ChannelControl`` — stack-native semantic ``data-ux-*`` attrs (Day-1 default)
* ``NullControl`` — no-op control for tests / headless shells

Attach via ``Document.use(...)`` or hub ``use_control(...)``.
"""

from ux_dom.plugins.control.channel import ChannelControl
from ux_dom.plugins.control.null import NullControl

__all__ = ["ChannelControl", "NullControl"]
