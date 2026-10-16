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


# --- Round-2 review bypasses: each row of the reviewer's table has a test. ---


class _Stringy:
    """A non-str value whose text is a script URL."""

    def __str__(self) -> str:
        return "javascript:alert(1)"


class _Trusted:
    """Explicit opt-in: the ``__html__`` protocol (as MarkupSafe uses)."""

    def __init__(self, html: str) -> None:
        self._html = html

    def __html__(self) -> str:
        return self._html


def test_non_str_value_is_checked_by_its_text():
    assert safe_attr_value("href", _Stringy()) == UNSAFE_URL
    html = a("x", href=_Stringy()).__render__(pretty=False)
    assert "javascript" not in html.lower()


@pytest.mark.parametrize(
    "value",
    [
        "&#106;avascript:alert(1)",
        "&#x6A;avascript:alert(1)",
        "javascript&colon;alert(1)",
        "java&Tab;script:alert(1)",
        "&#0000106avascript:alert(1)",
    ],
)
def test_entity_encoded_scheme_is_blocked(value):
    # The unescaped render path (safe_attributes[attr] = False) hands the
    # value to the browser as-is, and the browser decodes entities.
    assert safe_attr_value("href", value) == UNSAFE_URL


def test_entity_encoded_scheme_blocked_on_unescaped_render_path():
    tag = a("x", href="&#106;avascript:alert(1)")
    tag.safe_attributes["href"] = False
    assert "avascript" not in tag.__render__(pretty=False)


@pytest.mark.parametrize("value", ["\u00a0javascript:alert(1)", "\ufeffjavascript:alert(1)"])
def test_unicode_space_prefix_is_not_executable(value):
    # Not a scheme to the URL parser (relative URL), so it is safe either way;
    # pin that it never renders as a live javascript: URL.
    out = safe_attr_value("href", value)
    assert out == UNSAFE_URL or not out.lstrip().lower().startswith("javascript:")


def test_srcdoc_refused_by_default():
    assert safe_attr_value("srcdoc", "<script>alert(1)</script>") == UNSAFE_URL
    assert safe_attr_value("srcdoc", "<p>harmless</p>") == UNSAFE_URL
    html = iframe(srcdoc="<script>alert(1)</script>").__render__(pretty=False)
    assert "script" not in html.lower()


def test_srcdoc_allowed_with_explicit_html_opt_in():
    out = safe_attr_value("srcdoc", _Trusted("<p>ok</p>"))
    assert out == "<p>ok</p>"
    html = iframe(srcdoc=_Trusted("<p>ok</p>")).__render__(pretty=False)
    assert _attrs(html)["srcdoc"] == "<p>ok</p>"


@pytest.mark.parametrize(
    "value",
    [
        "data:image/svg+xml,<svg onload=alert(1)>",
        "data:image/svg+xml;base64,PHN2Zz4=",
        "data:application/javascript,alert(1)",
        "data:,alert(1)",
        "data:text/plain,hi",
        "file:///etc/passwd",
        "blob:https://x/1",
        "livescript:x",
        "ftp://example.com/x",
        "sms:+911234567890",
    ],
)
def test_schemes_outside_allow_list_are_blocked(value):
    assert safe_attr_value("href", value) == UNSAFE_URL
    assert safe_attr_value("data", value) == UNSAFE_URL


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",
        "HTTPS://example.com",
        "tel:+911234567890",
        "mailto:a@b.c",
        "data:image/png;base64,iVBOR",
        "data:image/jpeg;base64,/9j/",
        "data:image/gif;base64,R0lG",
        "data:image/webp;base64,UklG",
        "/abs",
        "rel/path",
        "?q=1",
        "#frag",
        "//cdn.example.com/x.js",
        "",
    ],
)
def test_allow_listed_and_relative_urls_pass(value):
    assert safe_attr_value("src", value) == value


@pytest.mark.parametrize("attr", ["icon", "archive", "usemap", "profile", "lowsrc", "dynsrc"])
def test_legacy_url_attributes_are_covered(attr):
    assert safe_attr_value(attr, "javascript:alert(1)") == UNSAFE_URL
