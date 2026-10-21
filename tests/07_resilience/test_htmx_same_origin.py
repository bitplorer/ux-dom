"""F-05: htmx/SSE/WS URLs stay same-origin; protocol-relative URLs refused."""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ux_dom.dom import cross_origin, div
from ux_dom.dom.src.html_string import StringToHTML
from ux_dom.dom.src.utils import dom_util
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


def _ws_id(char):
    return f"U+{ord(char):04X}"


# The 25 characters in ``_JS_WS``. ASCII first, then the non-ASCII set below.
_JS_WS_CHARS = [
    "\t",
    "\n",
    "\v",
    "\f",
    "\r",
    " ",
]
# ECMAScript \s, minus ASCII. Python str.split() does not split on U+FEFF.
_JS_NON_ASCII_WS = [
    "\u00a0",
    "\u1680",
    "\u2000",
    "\u2001",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u2028",
    "\u2029",
    "\u202f",
    "\u205f",
    "\u3000",
    "\ufeff",
]
_JS_WS_CHARS.extend(_JS_NON_ASCII_WS)


def _js_ws_class_without(dropped):
    """``_JS_WS`` with one character removed. Used to prove the splitter tests bite."""
    kept = "".join(char for char in _JS_WS_CHARS if char != dropped)
    return re.compile(f"[{kept}]+")


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


def test_string_to_html_drops_data_hx_sse_ws():
    # The string→HTML allowlist drops every hx-* / data-hx-* attribute, so a
    # foreign connect: target cannot survive (stronger than the URL gate).
    for markup in (
        '<div data-hx-sse="connect:http://evil" '
        'data-hx-ws="connect:wss://evil.com/s"></div>',
        '<div data-hx-sse="connect:/feed" data-hx-ws="connect:/ws"></div>',
    ):
        node = StringToHTML(markup).parse()
        rendered = node.__render__(pretty=False)
        assert "evil" not in rendered
        assert "data-hx-" not in rendered
        assert "connect:" not in rendered


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


def test_hx_get_connect_is_an_ordinary_url():
    """``connect:`` is an hx-sse/hx-ws prefix, not an hx-get prefix."""
    assert safe_attr_value("hx-get", "connect:/feed") == UNSAFE_URL
    assert safe_attr_value("data-hx-post", "connect:/feed") == UNSAFE_URL


def test_embedded_connect_does_not_hide_a_foreign_prefix():
    """A foreign prefix is an ordinary URL. The tail does not replace it."""
    assert safe_attr_value("hx-get", "https://evil.com/connect:/a") == UNSAFE_URL
    assert safe_attr_value("data-hx-post", "//evil.com/connect:/a") == UNSAFE_URL
    foreign = cross_origin("javascript:alert(1)//connect:/a")
    assert safe_attr_value("hx-get", foreign) == UNSAFE_URL


def test_sse_ws_splits_on_whitespace_like_htmx():
    assert safe_attr_value("hx-sse", "connect:feed swap:msg") == "connect:feed swap:msg"
    assert (
        safe_attr_value("data-hx-ws", "connect:feed send:submit")
        == "connect:feed send:submit"
    )


def test_event_name_must_not_contain_a_colon():
    """A swap/send name is ``[A-Za-z0-9_.-]+``. ``:`` refuses the whole value."""
    assert safe_attr_value("hx-sse", "swap:msg:part") == UNSAFE_URL
    assert safe_attr_value("hx-ws", "send:click:once") == UNSAFE_URL
    glued = "connect:/feed swap:user:login"
    assert safe_attr_value("hx-sse", glued) == UNSAFE_URL


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_bom_separator_cannot_hide_a_foreign_connect(attr):
    """U+FEFF is JavaScript whitespace. htmx splits; ``str.split()`` does not."""
    value = "swap:x\ufeffconnect:wss:evil.com"
    assert safe_attr_value(attr, value) == UNSAFE_URL


def test_bom_separator_cannot_hide_an_sse_https_target():
    value = "swap:x\ufeffconnect:https:evil.com"
    assert safe_attr_value("hx-sse", value) == UNSAFE_URL
    assert safe_attr_value("data-hx-sse", value) == UNSAFE_URL


@pytest.mark.parametrize(
    "sep", _JS_NON_ASCII_WS, ids=lambda char: f"U+{ord(char):04X}"
)
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_js_whitespace_separates_sse_ws_tokens(attr, sep):
    value = f"swap:x{sep}connect:wss:evil.com"
    assert safe_attr_value(attr, value) == UNSAFE_URL


def test_empty_swap_or_send_name_is_refused():
    """Fails if the empty-name check in ``_sse_ws_directive`` is removed."""
    assert safe_attr_value("hx-sse", "swap:") == UNSAFE_URL
    assert safe_attr_value("hx-ws", "send:") == UNSAFE_URL
    assert safe_attr_value("data-hx-sse", "connect:/feed swap:") == UNSAFE_URL
    assert safe_attr_value("data-hx-ws", "connect:/ws send:") == UNSAFE_URL


def test_bare_connect_is_refused():
    """Fails if the empty ``connect:`` target check is removed.

    ``cross_origin`` treats an empty probe as allowed, so a bare ``connect:``
    stays refused only while that empty-target check is present.
    """
    assert safe_attr_value("hx-sse", "connect:") == UNSAFE_URL
    assert safe_attr_value("hx-ws", "connect:") == UNSAFE_URL
    assert safe_attr_value("data-hx-sse", "connect:") == UNSAFE_URL
    assert safe_attr_value("hx-sse", cross_origin("connect:")) == UNSAFE_URL
    assert safe_attr_value("data-hx-ws", cross_origin("connect:")) == UNSAFE_URL


def test_connect_matches_only_a_leading_prefix():
    assert safe_attr_value("hx-sse", "x connect:/feed") == "x connect:/feed"
    assert safe_attr_value("hx-sse", "prefixconnect:/feed") == UNSAFE_URL
    assert safe_attr_value("hx-ws", "https://evil.com/connect:/a") == UNSAFE_URL


# ``swap:x{sep}connect:...`` is also refused by the name charset when the
# separator is not split, so it does not lock ``_JS_WS``. These values stay
# allowed unless the separator is actually a split: the inner ``/feed...``
# hides the later colon, and ``connect:{sep}//evil`` hides ``//`` when the
# separator is not ASCII noise.
@pytest.mark.parametrize("sep", _JS_WS_CHARS, ids=_ws_id)
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_each_js_ws_char_splits_a_second_connect(attr, sep):
    value = f"connect:/feed{sep}connect:wss:evil.com"
    assert safe_attr_value(attr, value) == UNSAFE_URL


@pytest.mark.parametrize("sep", _JS_WS_CHARS, ids=_ws_id)
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_each_js_ws_char_splits_a_protocol_relative_connect(attr, sep):
    value = f"connect:{sep}//evil.com"
    assert safe_attr_value(attr, value) == UNSAFE_URL


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_connect_feed_stays_same_origin(attr):
    assert safe_attr_value(attr, "connect:/feed") == "connect:/feed"


# A single separator is still split by ``maxsplit=1``, so the two-token tests
# above do not lock a full split. This one does: the second separator must
# also split, or the foreign connect stays glued to ``/feed``.
@pytest.mark.parametrize("sep", (" ", "\ufeff"), ids=("U+0020", "U+FEFF"))
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_every_separator_is_split(attr, sep):
    value = f"swap:a{sep}connect:/feed{sep}connect:wss:evil.com"
    assert safe_attr_value(attr, value) == UNSAFE_URL


# Same-origin connect targets. A tail that still starts with one of these
# hides the foreign colon after ``/``, so a bounded ``maxsplit`` keeps it.
_LOCAL_CONNECT_TOKENS = (
    "connect:/feed",
    "connect:/ok",
    "connect:/a",
    "connect:/ws",
)


@st.composite
def _tokens_ending_in_foreign_connect(draw):
    """1-8 tokens, a random JS-whitespace separator between each, evil last."""
    count = draw(st.integers(min_value=1, max_value=8))
    tokens = [
        draw(st.sampled_from(_LOCAL_CONNECT_TOKENS)) for _ in range(count - 1)
    ]
    tokens.append("connect:wss:evil.com")
    if count == 1:
        return tokens[0]
    pieces = [tokens[0]]
    for token in tokens[1:]:
        pieces.append(draw(st.sampled_from(tuple(_JS_WS_CHARS))))
        pieces.append(token)
    return "".join(pieces)


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
@settings(max_examples=100, deadline=None)
@given(value=_tokens_ending_in_foreign_connect())
def test_foreign_connect_is_refused_at_any_token_count(attr, value):
    """Any fixed ``maxsplit`` misses a longer value. 2 and 3 both fail here."""
    assert safe_attr_value(attr, value) == UNSAFE_URL


# Meta tests. They monkeypatch a broken splitter and assert the bad value is
# kept, so they stay green if production regresses. The locks are
# ``test_each_js_ws_char_splits_a_second_connect``,
# ``test_each_js_ws_char_splits_a_protocol_relative_connect``, and
# ``test_every_separator_is_split`` (that last one is the ``maxsplit=1`` lock).
@pytest.mark.parametrize("dropped", _JS_WS_CHARS, ids=_ws_id)
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_dropping_one_js_ws_char_keeps_the_foreign_connect(attr, dropped, monkeypatch):
    """Fails closed only while this character is in ``_JS_WS``.

    With the character removed, ``connect:/feed{sep}connect:wss:evil.com`` is
    kept, so ``test_each_js_ws_char_splits_a_second_connect`` would fail.
    """
    monkeypatch.setattr(dom_util, "_JS_WS", _js_ws_class_without(dropped))
    value = f"connect:/feed{dropped}connect:wss:evil.com"
    assert safe_attr_value(attr, value) != UNSAFE_URL


@pytest.mark.parametrize("dropped", _JS_NON_ASCII_WS, ids=_ws_id)
@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_dropped_non_ascii_ws_keeps_protocol_relative(attr, dropped, monkeypatch):
    """ASCII separators are still noise-stripped; these 19 are not.

    Dropping one of them keeps ``connect:{sep}//evil.com``, so
    ``test_each_js_ws_char_splits_a_protocol_relative_connect`` would fail.
    """
    monkeypatch.setattr(dom_util, "_JS_WS", _js_ws_class_without(dropped))
    value = f"connect:{dropped}//evil.com"
    assert safe_attr_value(attr, value) != UNSAFE_URL


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
@pytest.mark.parametrize(
    "value",
    [
        "connect:/feed\ufeffconnect:wss:evil.com",
        "connect:\ufeff//evil.com",
    ],
    ids=["second-connect", "protocol-relative"],
)
def test_str_split_mutant_keeps_a_bom_separated_connect(attr, value, monkeypatch):
    """``str.split()`` does not split on U+FEFF, so both refuse-tests would fail."""
    monkeypatch.setattr(dom_util, "_js_ws_tokens", lambda text: str(text).split())
    assert safe_attr_value(attr, value) != UNSAFE_URL


@pytest.mark.parametrize("attr", SSE_WS_ATTRS)
def test_entity_space_cannot_glue_a_foreign_connect(attr):
    """``&#32;`` is a space and must be decoded before the split."""
    value = "connect:/f&#32;connect:wss:evil.com"
    assert safe_attr_value(attr, value) == UNSAFE_URL
