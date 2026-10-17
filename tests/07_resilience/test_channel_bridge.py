"""ux-channel bridge emits exactly what the channel client parses (review M2)."""
from __future__ import annotations

import html
import json
import re

from channel_gate import require_channel
from ux_dom.ui import channel_bridge
from ux_dom.ui.channel_bridge import action_button_attrs, live_button


def setup_module():
    require_channel()


def _attr(markup: str, name: str) -> str:
    return html.unescape(re.search(rf'{name}="([^"]*)"', markup).group(1))


def test_args_are_escaped_once_and_decode_to_json():
    trust = {"sku": 'a"b<c&d', "n": 2}
    out = str(live_button("Buy", action="Cart.add", trust=trust))
    assert json.loads(_attr(out, "data-channel-args")) == trust


def test_target_uid_becomes_region_selector():
    attrs = action_button_attrs("Cart.add", target="Cart:1")
    assert attrs["data-channel-target"] == '[data-channel-id="Cart:1"]'
    assert action_button_attrs("x", target="#id")["data-channel-target"] == "#id"


def test_host_with_mint_signs_the_control():
    class Registry:
        def mint(self, action, trust):
            return f"cap:{action}:{trust['sku']}"

    attrs = action_button_attrs("Cart.add", host=Registry(), trust={"sku": "s1"})
    assert attrs["data-channel-cap"] == "cap:Cart.add:s1"


def test_stub_without_channel(monkeypatch):
    monkeypatch.setattr(channel_bridge, "channel_available", lambda: False)
    assert action_button_attrs("A.b", target="t") == {
        "data-channel-action": "A.b",
        "data-channel-target": "t",
    }
