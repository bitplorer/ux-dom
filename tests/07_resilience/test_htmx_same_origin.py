"""htmx request URLs stay on this origin unless opted out (review M4)."""

from __future__ import annotations

import pytest

from ux_dom.dom import cross_origin, div
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, safe_attr_value

FOREIGN = [
    "https://evil.example/x",
    "//evil.example/x",
    "\\\\evil",
    "/\\evil",
    "javascript:alert(1)",
    "http:evil",
]
LOCAL = ["/x", "x/y", "?q=1", "#f", "/api/items?id=3"]


@pytest.mark.parametrize(
    "attr",
    [
        "hx-get",
        "hx-post",
        "hx-put",
        "hx-patch",
        "hx-delete",
        "sse-connect",
        "ws-connect",
    ],
)
@pytest.mark.parametrize("url", FOREIGN)
def test_foreign_urls_refused(attr, url):
    assert safe_attr_value(attr, url) == UNSAFE_URL


@pytest.mark.parametrize("url", LOCAL)
def test_same_origin_urls_pass(url):
    assert safe_attr_value("hx-get", url) == url


def test_cross_origin_is_the_explicit_opt_in():
    assert (
        safe_attr_value("hx-get", cross_origin("https://api.example/x"))
        == "https://api.example/x"
    )
    assert (
        safe_attr_value("ws-connect", cross_origin("wss://rt.example/ws"))
        == "wss://rt.example/ws"
    )
    assert safe_attr_value("hx-get", cross_origin("javascript:alert(1)")) == UNSAFE_URL


def test_rendered_attribute():
    out = div(hx_get="https://evil.example/x", hx_post="/save").__render__(pretty=False)
    assert f'hx-get="{UNSAFE_URL}"' in out and 'hx-post="/save"' in out
