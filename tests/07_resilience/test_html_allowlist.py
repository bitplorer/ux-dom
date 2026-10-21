"""Allowlist sanitizer, including document mode.

Strings stay HTML. The same sanitizer serves ``defHTML``, ``srcdoc``, and
``to_fragment``. Fragment mode is the default; document mode is the caller's
``document=True`` keyword and is never inferred from the input.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest

from ux_dom.dom.htmlelement import HTMLElement
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.src.utils.dom_util import safe_attr_value
from ux_dom.ui.channel_bridge import to_fragment

# One page. Exact output is the contract for document mode. Whitespace
# between tags is kept as written (#96); a dropped element leaves its line.
PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Tom &amp; Jerry</title>
<meta http-equiv="refresh" content="0;url=https://evil.example/">
<link rel="stylesheet" href="/app.css">
<link rel="icon" href="https://cdn.example/favicon.ico">
<link rel="stylesheet" href="javascript:alert(1)">
<link rel="stylesheet" href="http://evil.example/x.css">
<style>p{color:red}</style>
<script>alert(1)</script>
</head>
<body>
<h1>Hi</h1>
<p class="ok">Yes</p>
<script>alert(2)</script>
<div hx-get="/admin" hx-trigger="load">no</div>
<portal src="/no">z</portal>
</body>
</html>
"""

EXPECTED = (
    "<!DOCTYPE html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    "<title>Tom &amp; Jerry</title>\n"
    "\n"
    '<link href="/app.css" rel="stylesheet">\n'
    '<link href="https://cdn.example/favicon.ico" rel="icon">\n'
    "\n"
    "\n"
    "<style>p{color:red}</style>\n"
    "\n"
    "</head>\n"
    "<body>\n"
    "<h1>Hi</h1>\n"
    '<p class="ok">Yes</p>\n'
    "\n"
    "<div>no</div>\n"
    "z\n"
    "</body>\n"
    "</html>\n"
)

# Every payload named in the #32 review. Rendered markup must not carry it.
REVIEW_PAYLOADS = [
    "<script>alert(1)</script>",
    "<SCRIPT SRC=//evil.example/x.js></SCRIPT>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<a href='javascript:alert(1)'>x</a>",
    "<a href='vbscript:msgbox(1)'>x</a>",
    "<a href='data:text/html,<script>alert(1)</script>'>x</a>",
    "<a href='jav&#x61;script:alert(1)'>x</a>",
    "<a href='java\tscript:alert(1)'>x</a>",
    "<a href='&#0000106;avascript:alert(1)'>x</a>",
    "<a href='javascript&colon;alert(1)'>x</a>",
    "<a href='\x01javascript:alert(1)'>x</a>",
    "<iframe src=javascript:alert(1)></iframe>",
    "<object data=javascript:alert(1)></object>",
    "<embed src=javascript:alert(1)>",
    "<style>*{background:url(javascript:alert(1))}</style>",
    "<base href=//evil.example/>",
    "<meta http-equiv=refresh content='0;url=javascript:alert(1)'>",
    "<link rel=stylesheet href=//evil.example/x.css>",
    "<frameset><frame src=javascript:alert(1)></frameset>",
    "<math><maction xlink:href=javascript:alert(1)>x</maction></math>",
    "<form action=javascript:alert(1)><button>x</button></form>",
    "<button formaction=javascript:alert(1)>x</button>",
    "<div style='width:expression(alert(1))'>x</div>",
    "<div style='background:url(javascript:alert(1))'>x</div>",
    "<iframe srcdoc='<script>alert(1)</script>'></iframe>",
    "<div x-init='alert(1)'>x</div>",
    "<button @click='alert(1)'>x</button>",
    "<div :class='alert(1)'>x</div>",
    "<div hx-on:click='alert(1)'>x</div>",
    "<div _onclick='alert(1)'>x</div>",
    "<div hx-get='/admin' hx-trigger='load'>x</div>",
    "<div data-hx-get='/admin' data-hx-trigger='load'>x</div>",
    "<portal src='/x'>t</portal>",
    "<noscript><p title='</noscript><img src=x onerror=alert(1)>'>",
    "<math><mglyph><style><img src=x onerror=alert(1)></style></mglyph></math>",
    "<template><script>alert(1)</script><p>ok</p></template>",
    "<textarea><img src=x onerror=alert(1)></textarea>",
    "<div onclick=alert(1)",  # unclosed
]


def _render(src: str, document: bool = False) -> str:
    return "".join(
        node.__render__(pretty=False) for node in defHTML(src, document=document)
    )


def _live_bits(html: str) -> list[str]:
    """Tags and attributes a browser could run.

    Text that merely says ``onfocus`` is not one of them.
    """
    found: list[str] = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            name = tag.lower()
            if name in {
                "script",
                "iframe",
                "object",
                "embed",
                "portal",
                "math",
                "frameset",
            }:
                found.append(name)
            for key, value in attrs:
                kl = key.lower()
                while kl.startswith("_"):
                    kl = kl[1:]
                val = value or ""
                if (
                    kl.startswith("on")
                    or kl.startswith("hx-")
                    or kl.startswith("data-hx-")
                ):
                    found.append(kl)
                if kl.startswith(("x-", "@", ":")):
                    found.append(kl)
                low = (
                    val.lower()
                    .replace("\t", "")
                    .replace("\n", "")
                    .replace("\x01", "")
                )
                if (
                    "javascript:" in low
                    or "vbscript:" in low
                    or "data:text/html" in low
                ):
                    found.append(val)

    P().feed(html)
    return found


def test_document_round_trip_exact():
    assert _render(PAGE, document=True) == EXPECTED


def test_document_meta_refresh_dropped():
    src = (
        "<!DOCTYPE html><html><head>"
        "<meta http-equiv='refresh' content='0;url=https://evil.example/'>"
        "<meta charset='utf-8'>"
        "</head><body></body></html>"
    )
    out = _render(src, document=True)
    assert "refresh" not in out.lower()
    assert "evil.example" not in out
    assert 'charset="utf-8"' in out


def test_document_link_javascript_and_http_dropped():
    src = (
        "<!DOCTYPE html><html><head>"
        "<link rel='stylesheet' href='javascript:alert(1)'>"
        "<link rel='stylesheet' href='http://evil.example/x.css'>"
        "<link rel='stylesheet' href='/app.css'>"
        "<link rel='icon' href='https://cdn.example/favicon.ico'>"
        "</head><body></body></html>"
    )
    out = _render(src, document=True)
    assert "javascript:" not in out.lower()
    assert "http://evil.example" not in out
    assert 'href="/app.css"' in out
    assert 'href="https://cdn.example/favicon.ico"' in out


def test_document_scripts_in_head_and_body_stripped():
    src = (
        "<!DOCTYPE html><html><head><script>alert(1)</script></head>"
        "<body><script>alert(2)</script><p>ok</p></body></html>"
    )
    out = _render(src)
    assert "<script" not in out.lower()
    assert "alert(1)" not in out
    assert "alert(2)" not in out
    assert "<p>ok</p>" in out


def test_document_title_amp_kept_as_written():
    src = (
        "<!DOCTYPE html><html><head>"
        "<title>Tom &amp; Jerry</title>"
        "</head><body></body></html>"
    )
    out = _render(src, document=True)
    assert "<title>Tom &amp; Jerry</title>" in out, out
    assert "&amp;amp;" not in out
    assert "Tomamp" not in out


def test_leading_whitespace_and_case_are_still_a_document():
    src = (
        " \n<!DoCtYpE html><HTML><head><title>T&amp;T</title></head>"
        "<body><p>z</p></body></HTML>"
    )
    out = _render(src, document=True)
    # A browser ignores whitespace before the doctype; it is kept as written.
    assert out.startswith(" \n<!DOCTYPE html>")
    assert "<title>T&amp;T</title>" in out
    assert "<html>" in out.lower()
    assert "<p>z</p>" in out


def test_fragment_does_not_keep_document_only_tags():
    out = _render(
        "<div>"
        "<style>p{color:red}</style>"
        "<meta http-equiv='refresh' content='0;url=https://evil.example/'>"
        "<link rel='stylesheet' href='/app.css'>"
        "<p>ok</p>"
        "</div>"
    )
    assert "<style" not in out.lower()
    assert "<meta" not in out.lower()
    assert "<link" not in out.lower()
    assert "<p>ok</p>" in out


def test_hx_and_unknown_tags_do_not_survive():
    out = _render(
        '<div id="a" hx-get="/frag" hx-trigger="load" '
        'hx-vals="js:{pwn:1}" hx-headers=\'{"X-Audit":"1"}\' '
        'data-hx-get="/frag">a</div>'
        '<div hx-on:click="window.ON=1">d</div>'
        '<portal id="p" src="http://127.0.0.1/frag">portal</portal>'
    )
    assert "hx-" not in out.lower()
    assert "data-hx-" not in out.lower()
    assert "<portal" not in out.lower()
    assert 'id="a"' in out
    assert _live_bits(out) == []


def test_entity_split_handler_stays_text():
    """``<&lt;x onfocus`` must not come back as an element. Text stays escaped."""
    payload = "<p><&lt;x autofocus tabindex=1 onfocus=alert(1)></p>"
    for label, out in (
        ("defHTML", _render(payload)),
        ("HTMLElement", HTMLElement(payload).__render__(pretty=False)),
    ):
        assert "&lt;" in out, (label, out)
        assert "<ltx" not in out.lower(), (label, out)
        assert _live_bits(out) == [], (label, out)


def test_fully_stripped_input_renders_empty():
    assert _render("<script>alert(1)</script>") == ""
    assert _render("<iframe src='javascript:alert(1)'></iframe>") == ""
    assert _render("<portal src='/x'></portal>") == ""
    assert to_fragment("<script>alert(1)</script>") == ""
    assert safe_attr_value("srcdoc", "<script>alert(1)</script>") == ""


def test_srcdoc_and_to_fragment_share_the_sanitizer():
    # Both are fragment mode: a whole page loses its doctype, meta, link and
    # style, because the input does not choose document mode.
    fragment = _render(PAGE)
    assert to_fragment(PAGE) == fragment
    assert safe_attr_value("srcdoc", PAGE) == fragment
    for gone in ("<!doctype", "<meta", "<link", "<style", "<script"):
        assert gone not in fragment.lower()
    assert "<h1>Hi</h1>" in fragment
    assert to_fragment("<p>harmless</p>") == "<p>harmless</p>"
    assert safe_attr_value("srcdoc", "<p>harmless</p>") == "<p>harmless</p>"


@pytest.mark.parametrize("payload", REVIEW_PAYLOADS)
def test_review_payload_is_inert(payload):
    out = _render(payload)
    assert _live_bits(out) == [], (payload, out)
