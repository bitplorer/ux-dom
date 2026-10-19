"""F-05: htmx/SSE/WS URLs stay same-origin; protocol-relative URLs refused."""

from __future__ import annotations

import pytest

from ux_dom.dom import cross_origin, div
from ux_dom.dom.src.html_string import StringToHTML
from ux_dom.dom.src.utils.dom_util import (
    SAME_ORIGIN_URL_ATTRIBUTES,
    UNSAFE_URL,
    safe_attr_value,
)

FOREIGN = [
    "https://evil.example/x",
    "//evil.example/x",
    "\\\\evil",
    "/\\evil",
    "javascript:alert(1)",
    "http:evil",
]
LOCAL = ["/x", "x/y", "?q=1", "#f", "/api/items?id=3"]
HTMX_ATTRS = [
    "hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete",
    "data-hx-get", "data-hx-post", "data-hx-put", "data-hx-patch", "data-hx-delete",
    "sse-connect", "ws-connect", "data-sse-connect", "data-ws-connect",
]


@pytest.mark.parametrize("attr", HTMX_ATTRS)
@pytest.mark.parametrize("url", FOREIGN)
def test_foreign_urls_refused(attr, url):
    assert safe_attr_value(attr, url) == UNSAFE_URL


@pytest.mark.parametrize("url", LOCAL)
def test_same_origin_urls_pass(url):
    assert safe_attr_value("hx-get", url) == url
    assert safe_attr_value("data-hx-get", url) == url


def test_cross_origin_is_the_explicit_opt_in():
    assert safe_attr_value("hx-get", cross_origin("https://api.example/x")) == "https://api.example/x"
    assert safe_attr_value("ws-connect", cross_origin("wss://rt.example/ws")) == "wss://rt.example/ws"
    assert (
        safe_attr_value("data-sse-connect", cross_origin("https://api.example/s"))
        == "https://api.example/s"
    )
    assert safe_attr_value("hx-get", cross_origin("javascript:alert(1)")) == UNSAFE_URL


def test_protocol_relative_href_refused():
    assert safe_attr_value("href", "//evil.example/") == UNSAFE_URL
    assert safe_attr_value("src", "//evil.example/a.js") == UNSAFE_URL
    assert safe_attr_value("href", "https://ok.example/") == "https://ok.example/"
    assert safe_attr_value("href", "/local") == "/local"


def test_rendered_attribute():
    out = div(hx_get="https://evil.example/x", hx_post="/save").__render__(pretty=False)
    assert f'hx-get="{UNSAFE_URL}"' in out and 'hx-post="/save"' in out
    out2 = div(**{"data-hx-get": "//evil.example/x"}).__render__(pretty=False)
    assert UNSAFE_URL in out2


# htmx 1.9.2 reads hx-sse / hx-ws and the data- spellings as connect:<url>.
SSE_WS_ATTRS = ["hx-sse", "hx-ws", "data-hx-sse", "data-hx-ws"]
CONNECT_FOREIGN = [
    "connect:http://evil",
    "connect:https://evil.com/s",
    "connect:https://evil.example/feed",
    "connect:wss://evil.com/s",
    "connect://evil",
    "connect:javascript:alert(1)",
    "CONNECT:https://evil.com/s",
    "connect:\thttps://evil.com/s",
    " connect:http://evil",
]
CONNECT_LOCAL = [
    "connect:/feed",
    "connect:/ws",
    "CONNECT:/feed",
    " connect:/feed",
    "connect: /feed",
]


def test_item4c_connect_http_evil_refused_and_local_kept():
    """Port of the item4c live script's render contract (no browser).

    ``connect:http://evil`` must not survive on ``data-hx-sse``.
    ``connect:/feed`` must survive on ``hx-sse`` (the colon is a prefix).
    """
    foreign = div(**{"data-hx-sse": "connect:https://evil.example/feed"}).__render__(
        pretty=False
    )
    local = div(hx_sse="connect:/feed").__render__(pretty=False)
    http_evil = div(**{"data-hx-sse": "connect:http://evil"}).__render__(pretty=False)
    assert "connect:https://evil.example/feed" not in foreign
    assert UNSAFE_URL in foreign
    assert 'hx-sse="connect:/feed"' in local
    assert UNSAFE_URL not in local
    assert "connect:http://evil" not in http_evil
    assert UNSAFE_URL in http_evil
    assert safe_attr_value("data-hx-sse", "connect:http://evil") == UNSAFE_URL
    assert safe_attr_value("hx-sse", "connect:/feed") == "connect:/feed"
    assert safe_attr_value("data-hx-ws", "connect:http://evil") == UNSAFE_URL
    assert safe_attr_value("hx-ws", "connect:/ws") == "connect:/ws"


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
@pytest.mark.parametrize("url", CONNECT_FOREIGN)
def test_connect_foreign_urls_refused(attr, url):
    assert safe_attr_value(attr, url) == UNSAFE_URL
    rendered = div(**{attr: url}).__render__(pretty=False)
    assert url not in rendered
    assert UNSAFE_URL in rendered


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
@pytest.mark.parametrize("url", CONNECT_LOCAL)
def test_connect_same_origin_kept(attr, url):
    assert safe_attr_value(attr, url) == url
    assert url in div(**{attr: url}).__render__(pretty=False)


@pytest.mark.parametrize("escape", [True, False])
def test_string_to_html_gates_data_hx_sse_ws(escape):
    foreign = StringToHTML(
        '<div data-hx-sse="connect:http://evil" '
        'data-hx-ws="connect:wss://evil.com/s"></div>',
        escape=escape,
    ).parse()
    rendered = foreign.__render__(pretty=False)
    assert "evil" not in rendered
    assert rendered.count(UNSAFE_URL) == 2
    local = StringToHTML(
        '<div data-hx-sse="connect:/feed" data-hx-ws="connect:/ws"></div>',
        escape=escape,
    ).parse()
    kept = local.__render__(pretty=False)
    assert 'data-hx-sse="connect:/feed"' in kept
    assert 'data-hx-ws="connect:/ws"' in kept


@pytest.mark.parametrize(
    ("attr", "url"),
    [
        ("hx-sse", "swap:message"),
        ("data-hx-sse", "swap:message"),
        ("hx-ws", "send:submit"),
        ("data-hx-ws", "send:submit"),
        ("hx-sse", "connect:/feed swap:message"),
        ("hx-ws", "connect:/ws send:submit"),
    ],
)
def test_sse_ws_non_url_directives_kept(attr, url):
    """htmx 1.9.2 ``swap:`` / ``send:`` are not URLs. See ATTRIBUTES.md."""
    assert safe_attr_value(attr, url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/s",
        "swap:https://evil.com/s",
        "send:wss://evil.com/s",
        "swap:message connect:http://evil",
        "connect:/feed connect:https://evil.com/s",
    ],
)
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_sse_ws_non_connect_urls_refused(attr, url):
    assert safe_attr_value(attr, url) == UNSAFE_URL


def test_cross_origin_applies_to_url_inside_connect():
    assert (
        safe_attr_value("hx-sse", cross_origin("connect:https://api.example/feed"))
        == "connect:https://api.example/feed"
    )
    assert (
        safe_attr_value("data-hx-ws", cross_origin("connect:wss://rt.example/ws"))
        == "connect:wss://rt.example/ws"
    )
    assert (
        safe_attr_value("hx-sse", cross_origin("connect:javascript:alert(1)"))
        == UNSAFE_URL
    )
    assert safe_attr_value("hx-ws", cross_origin("connect://evil")) == UNSAFE_URL


# Mutation locks: noise stripping and the protocol-relative cross_origin
# refusal. data-hx-sse / data-hx-ws fail here until those names are gated.
@pytest.mark.parametrize("value", [" //evil", "/\t/evil", "java\tscript:alert(1)"])
@pytest.mark.parametrize("attr", ["href", "hx-get", "hx-sse", "data-hx-sse"])
def test_probe_noise_stripped_before_scheme_check(attr, value):
    assert safe_attr_value(attr, value) == UNSAFE_URL


def test_cross_origin_refuses_protocol_relative():
    assert safe_attr_value("hx-get", cross_origin("//evil")) == UNSAFE_URL
    assert safe_attr_value("hx-sse", cross_origin("//evil")) == UNSAFE_URL
    assert safe_attr_value("data-hx-ws", cross_origin("//evil")) == UNSAFE_URL


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_sse_ws_attrs_stay_in_the_gate(attr):
    assert attr in SAME_ORIGIN_URL_ATTRIBUTES
    assert safe_attr_value(attr, "connect:http://evil") == UNSAFE_URL
