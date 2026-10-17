"""examples/ux_channel_counter: ux-dom renders, ux-channel acts.

Checked against ux-channel f1a93fc (the pin in channel_gate.HINT).
"""

from __future__ import annotations

import json
import re

import pytest
from channel_gate import require_channel
from example_checks import (
    assert_external_scripts_pinned,
    assert_scripts_nonced,
    client,
    compact,
)

CONTROL = re.compile(
    r'data-channel-action="(?P<action>[^"]+)"'
    r'(?: data-channel-args="(?P<args>[^"]*)")?'
    r' data-channel-cap="(?P<cap>[^"]+)"'
)


@pytest.fixture()
def c():
    require_channel()
    from examples.ux_channel_counter.main import app, ch

    ch.draft.set("count", 0)  # the dev memory store is process-wide
    with client(app) as test_client:
        yield test_client


def controls(html: str) -> dict[str, dict]:
    """Signed controls on the page, keyed by label of the button."""
    out = {}
    for tag in re.findall(r"<button\b[^>]*>\s*[^<]*", html):
        m = CONTROL.search(tag)
        if not m:
            continue
        label = tag.rsplit(">", 1)[1].strip()
        args = json.loads(m["args"].replace("&quot;", '"')) if m["args"] else {}
        out[label] = {"action": m["action"], "args": args, "cap": m["cap"]}
    return out


def dispatch(c, control: dict):
    body = {"v": "1", **control}
    return c.post(
        "/ux-channel/action",
        content=json.dumps(body),
        headers={
            "content-type": "application/json",
            "x-channel": "1",
            "origin": "http://testserver",
        },
    )


def morphed_html(response) -> str:
    """The HTML of the region morph(s) in an action reply."""
    reply = response.json()
    assert reply["ok"] is True, reply
    return "".join(op["html"] for op in reply["ops"] if op["op"] == "morph")


def count(html: str) -> int:
    return int(re.search(r'data-count="(\d+)"', html)[1])


def test_page_is_a_ux_dom_document_with_channel_scripts(c):
    r = c.get("/")
    assert r.status_code == 200
    html = compact(r.text)
    assert "<title>Counter · ux-dom × ux-channel</title>" in html
    assert 'src="/ux-channel/static/ux-channel.js"' in html
    assert 'data-channel-id="counter"' in html  # ch.html(region) wrapper
    assert count(html) == 0
    assert_scripts_nonced(r)
    assert_external_scripts_pinned(r.text)


def test_buttons_carry_control_attrs(c):
    found = controls(c.get("/").text)
    assert set(found) == {"+1", "+5", "Reset"}
    assert found["+5"]["action"] == "add" and found["+5"]["args"] == {"step": 5}
    assert found["Reset"]["action"] == "reset" and found["Reset"]["args"] == {}


def test_dispatching_an_action_refreshes_the_region(c):
    found = controls(c.get("/").text)
    r = dispatch(c, found["+5"])
    assert r.status_code == 200, r.text
    assert count(morphed_html(r)) == 5  # the refreshed region rides in the reply
    assert count(morphed_html(dispatch(c, found["+1"]))) == 6
    assert count(c.get("/").text) == 6  # the next page render sees the state
    dispatch(c, found["Reset"])
    assert count(c.get("/").text) == 0


def test_tampered_args_are_refused(c):
    plus_one = controls(c.get("/").text)["+1"]
    forged = {**plus_one, "args": {"step": 1000}}
    r = dispatch(c, forged)
    assert r.status_code in (400, 401, 403), r.text
    assert count(c.get("/").text) == 0


def test_health(c):
    assert c.get("/health").json() == {"ok": True, "app": "ux_channel_counter"}
