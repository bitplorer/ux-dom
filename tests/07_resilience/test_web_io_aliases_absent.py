"""ADR 0004 absence lock: web_io has one name per thing.

``HtmxEvents.get_events("hx-get")`` replaces the ``hx_get_events`` property, and
``Message`` replaces the ``MESSAGE`` alias.
"""

from __future__ import annotations

import ux_dom.web_io as web_io
import ux_dom.web_io._types as types
from ux_dom.web_io import HtmxEvents


def test_htmx_events_has_no_hx_get_events():
    assert not hasattr(HtmxEvents, "hx_get_events")
    assert HtmxEvents().get_events("hx-get") == {}


def test_message_is_the_only_name():
    assert not hasattr(types, "MESSAGE")
    assert not hasattr(web_io, "MESSAGE")
    assert "MESSAGE" not in web_io.__all__
    assert "Message" in web_io.__all__
    assert web_io.Message is types.Message
