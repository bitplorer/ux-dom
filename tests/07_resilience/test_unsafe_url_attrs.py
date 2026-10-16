"""URL attributes fail closed: script-capable schemes never reach the browser."""
from __future__ import annotations

from html.parser import HTMLParser

import pytest

from ux_dom.dom import a, div, form, iframe, img
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, safe_attr_value

EVIL = [
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "  javascript:alert(1)",
    "\x01javascript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "vbscript:msgbox(1)",
    "data:text/html,<script>alert(1)</script>",
    "DATA:text/html;base64,PHNjcmlwdD4=",
]
SAFE = [
    "/cart",
    "https://example.com/a?b=c&d=e",
    "#top",
    "mailto:x@example.com",
    "data:image/png;base64,iVBOR",
    "relative/javascript:path",
]


def _attrs(html: str) -> dict[str, str]:
    found: dict[str, str] = {}

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            found.update({k: v for k, v in attrs})

    P().feed(html)
    return found


@pytest.mark.parametrize("value", EVIL)
def test_evil_href_neutralized(value):
    html = a("x", href=value).__render__(pretty=False)
    assert _attrs(html)["href"] == UNSAFE_URL


@pytest.mark.parametrize(
    "build",
    [
        lambda v: img(src=v),
        lambda v: iframe(src=v),
        lambda v: form(action=v),
        lambda v: div(formaction=v),
        lambda v: div(**{"xlink:href": v}),
    ],
)
def test_all_url_attributes_covered(build):
    html = build("javascript:alert(1)").__render__(pretty=False)
    assert "javascript" not in html.lower()


@pytest.mark.parametrize("value", SAFE)
def test_safe_urls_untouched(value):
    html = a("x", href=value).__render__(pretty=False)
    assert _attrs(html)["href"] == value


def test_non_url_attribute_keeps_text():
    html = div(title="javascript: is a word").__render__(pretty=False)
    assert _attrs(html)["title"] == "javascript: is a word"


def test_helper_contract():
    assert safe_attr_value("href", "javascript:x") == UNSAFE_URL
    assert safe_attr_value("HREF", "javascript:x") == UNSAFE_URL
    assert safe_attr_value("title", "javascript:x") == "javascript:x"
