"""examples/standalone: single-file apps for SSE, WebSocket, MCP-style tools
and htmx search.

Migrated from tests/04_production/test_standalone_apps_production.py (the
top-level standalone/ package) and test_examples_production.py (realtime_kit,
which duplicated the SSE and WebSocket apps). Load and isolation checks kept.
"""

from __future__ import annotations

import concurrent.futures
import re

import pytest
from example_checks import (
    assert_external_scripts_pinned,
    assert_scripts_nonced,
    client,
    compact,
)

from ux_dom.dom import div

HTMX = "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"
SSE_EXT = "https://unpkg.com/htmx-ext-sse@2.2.3/dist/sse.min.js"


def _page_checks(response):
    assert response.status_code == 200
    assert response.text.lower().startswith("<!doctype html>")
    assert_scripts_nonced(response)
    assert_external_scripts_pinned(response.text)


# ── SSE ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def sse():
    from examples.standalone.sse import create_app

    return client(create_app())


def test_sse_page_loads_htmx_and_the_sse_extension(sse):
    r = sse.get("/")
    _page_checks(r)
    assert HTMX in r.text and SSE_EXT in r.text
    html = compact(r.text)
    assert 'sse-connect="/sse/market"' in html and 'sse-swap="message"' in html


def test_sse_dialect():
    h = div(sse_connect="/sse/x", sse_swap="message").__render__(pretty=False)
    assert "sse-connect" in h and "sse-swap" in h


def test_sse_events_carry_html_fragments(sse):
    r = sse.get("/sse/market?n=3")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    events = [e for e in r.text.split("\n\n") if "event: message" in e]
    assert len(events) == 3
    data = "\n".join(
        line[len("data: ") :]
        for line in events[0].splitlines()
        if line.startswith("data: ")
    )
    assert compact(data) == '<span class="tick" data-i="0">market:0</span>'
    assert "{" not in r.text  # no raw JSON on the page


def test_sse_under_load(sse):
    def hit(i):
        rr = sse.get(f"/sse/t{i}?n=2")
        return rr.status_code == 200 and f"t{i}:0" in rr.text

    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        assert all(ex.map(hit, range(30)))


# ── WebSocket ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def ws():
    from examples.standalone.ws import create_app

    return client(create_app())


def test_ws_page_loads_its_client_script(ws):
    r = ws.get("/")
    _page_checks(r)
    assert 'src="/static/ws_counter.js"' in r.text
    assert 'data-socket="/ws/counter"' in r.text
    js = ws.get("/static/ws_counter.js")
    assert js.status_code == 200
    assert "new WebSocket" in js.text and "bump" in js.text


def test_ws_protocol(ws):
    with ws.websocket_connect("/ws/counter") as sock:
        assert sock.receive_json()["event"] == "hello"
        sock.send_json({"event": "bump", "data": {"delta": 3}})
        assert sock.receive_json()["data"]["n"] == 3
        sock.send_json({"event": "reset", "data": {}})
        assert sock.receive_json()["data"]["n"] == 0


def test_ws_isolation_and_cleanup(ws):
    cms = []
    for _ in range(6):
        cm = ws.websocket_connect("/ws/counter")
        sock = cm.__enter__()
        sock.receive_json()
        cms.append((cm, sock))
    ns = []
    for i, (_, sock) in enumerate(cms):
        sock.send_json({"event": "bump", "data": {"delta": i + 1}})
        ns.append(sock.receive_json()["data"]["n"])
    assert ns == list(range(1, 7))
    for cm, _ in cms:
        cm.__exit__(None, None, None)
    assert ws.get("/health").json() == {"ok": True, "connections": 0}
    from examples.standalone.ws import adapter

    assert adapter._instances == {}  # per-connection state released


def test_ws_malformed_message_keeps_connection(ws):
    with ws.websocket_connect("/ws/counter") as sock:
        sock.receive_json()  # hello
        sock.send_json({"data": {"x": 1}})  # no event
        sock.send_json({"event": "get", "data": {}})
        assert sock.receive_json()["event"] == "update"


# ── MCP-style tools ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mcp():
    from examples.standalone.mcp import create_app

    return client(create_app())


def test_mcp_home_is_a_document(mcp):
    r = mcp.get("/")
    _page_checks(r)
    assert 'id="tool-echo"' in r.text


def test_mcp_tools_http(mcp):
    assert len(mcp.get("/mcp/tools/list").json()["tools"]) >= 3
    r = mcp.post("/mcp/tools/call", json={"name": "echo", "arguments": {"text": "hi"}})
    assert r.json()["result"] == "hi"
    assert 'id="tool-result">hi</span>' in compact(r.json()["html"])
    r = mcp.post(
        "/mcp/tools/call",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 2, "b": 3}},
        },
    )
    assert r.json() == {"jsonrpc": "2.0", "id": 1, "result": r.json()["result"]}
    assert r.json()["result"]["result"] == 5


def test_mcp_tool_html_is_escaped(mcp):
    r = mcp.post(
        "/mcp/tools/call",
        json={"name": "render_card", "arguments": {"title": "<script>x</script>"}},
    )
    assert "<script" not in r.json()["html"]
    assert "&lt;script&gt;" in r.json()["html"]


def test_mcp_errors(mcp):
    r = mcp.post("/mcp/tools/call", json={"name": "nope", "arguments": {}})
    assert r.json() == {"ok": False, "error": "unknown tool nope", "html": ""}
    r = mcp.post("/mcp/tools/call", json={"jsonrpc": "2.0", "id": 9, "method": "x"})
    assert r.status_code == 400
    r = mcp.post(
        "/mcp/tools/call", json={"name": "add", "arguments": {"a": "two", "b": 1}}
    )
    assert r.json()["ok"] is False and "a and b must be numbers" in r.json()["error"]


def test_mcp_tools_ws_and_load(mcp):
    # Leaving each ``with`` block disconnects the client; the TestClient would
    # re-raise any server error from that (the old app swallowed all of them).
    with mcp.websocket_connect("/mcp/ws") as sock:
        sock.send_json({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert "tools" in sock.receive_json()["result"]
        sock.send_json(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"text": "ws"}},
            }
        )
        assert sock.receive_json()["result"]["result"] == "ws"
        sock.send_text("not json")
        assert sock.receive_json() == {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "parse error"},
        }

    def hit(i):
        rr = mcp.post(
            "/mcp/tools/call", json={"name": "add", "arguments": {"a": i, "b": 1}}
        )
        return rr.json().get("result") == i + 1

    with concurrent.futures.ThreadPoolExecutor(16) as ex:
        assert all(ex.map(hit, range(40)))


# ── htmx search ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def search():
    from examples.standalone.search import SearchBox, create_app

    assert SearchBox(q="").get(id="q")
    return client(create_app())


def test_search_page_loads_htmx(search):
    r = search.get("/")
    _page_checks(r)
    assert HTMX in r.text
    assert 'hx-get="/search"' in r.text


def test_search_partial_and_full_page(search):
    r = search.get("/search?q=abc", headers={"HX-Request": "true"})
    assert "<html" not in r.text and 'id="r0"' in r.text and "abc-0" in r.text
    full = search.get("/search?q=abc")
    assert full.text.lower().startswith("<!doctype html>") and "abc-0" in full.text
    assert re.search(r'value="abc"', full.text)


def test_search_escapes_the_query(search):
    r = search.get("/search?q=<b>x</b>", headers={"HX-Request": "true"})
    assert "<b>" not in r.text and "&lt;b&gt;x&lt;/b&gt;-0" in r.text


def test_search_under_load(search):
    def hit(i):
        rr = search.get(f"/search?q=q{i}", headers={"HX-Request": "true"})
        return rr.status_code == 200 and f"q{i}-0" in rr.text

    with concurrent.futures.ThreadPoolExecutor(16) as ex:
        assert all(ex.map(hit, range(50)))
