"""Parsing an HTML string keeps its whitespace (#96).

A browser keeps every whitespace character of the source in the DOM, after
it turns CRLF and a lone CR into LF. The parser and the sanitizer keep it too,
so a parse and a flat render give back the page the browser would build.
Browser check: ``tests/06_browser/test_parse_whitespace_browser.py``.
"""

from __future__ import annotations

import pytest

from ux_dom import Fragment
from ux_dom.dom.src.html_string import _sanitized_html
from ux_dom.dom.src.parse_html import tokenize_html


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


SOURCES = [
    "<pre>\n\n  a\tb  \n</pre>",
    "<pre>a\r\nb\rc\r\n</pre>",
    "<textarea>\n\n x  \t y\n\n</textarea>",
    "<listing>\n\n  a\n\tb\n</listing>",
    "a\n<b>x</b>\nc",
    "<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>",
    "<script>if (a  <  2) {\r\n\t}\r</script>",
    "<style>\r\np  >  b {\tcolor: red }\n</style>",
    '<p title="a\r\nb">x</p>',
]


@pytest.mark.parametrize("source", SOURCES)
def test_parser_gives_back_its_source(source):
    assert tokenize_html(source).render() == _lf(source)


# (source, flat render) through the sanitizer.
SANITIZED = [
    # Preformatted bodies, as written.
    ("<pre>\n\n  a\tb  \n</pre>", "<pre>\n\n  a\tb  \n</pre>"),
    ("<pre><b>x</b>  <i>y</i>\n  z</pre>", "<pre><b>x</b>  <i>y</i>\n  z</pre>"),
    # The LF right after the start tag is not text (#127).
    ("<textarea>\n x \n</textarea>", "<textarea> x \n</textarea>"),
    ("<textarea>  <b>x</b>  </textarea>", "<textarea>  &lt;b&gt;x&lt;/b&gt;  </textarea>"),
    ("<listing>\n  a\n\tb\n</listing>", "<listing>  a\n\tb\n</listing>"),
    # CRLF and a lone CR are LF, as in the browser.
    ("<textarea>a\r\nb\rc\r\n</textarea>", "<textarea>a\nb\nc\n</textarea>"),
    ("<p>a\r\n<b>b</b>\rc</p>", "<p>a\n<b>b</b>\nc</p>"),
    # Whitespace between inline elements separates the words.
    ("a <b>x</b> c", "a <b>x</b> c"),
    ("<p>a\n<b>x</b>\n<i>y</i></p>", "<p>a\n<b>x</b>\n<i>y</i></p>"),
    ("<p><b>x</b>\t<i>y</i></p>", "<p><b>x</b>\t<i>y</i></p>"),
    ("<p>foo\n</p>", "<p>foo\n</p>"),
    # Whitespace-only text is a text node in the DOM.
    ("<ul>\n  <li>a</li>\n</ul>", "<ul>\n  <li>a</li>\n</ul>"),
    ("\n\n<p>x</p>\n\n", "\n\n<p>x</p>\n\n"),
]


@pytest.mark.parametrize("source,expected", SANITIZED)
def test_sanitizer_keeps_whitespace(source, expected):
    assert _sanitized_html(source) == expected
    assert _sanitized_html(source, document=True) == expected
    assert Fragment(source).__render__(pretty=False) == expected


def test_document_style_is_byte_exact():
    css = "\n\n  p  >  b {\tcolor: red }\r\n"
    out = _sanitized_html(f"<style>{css}</style>", document=True)
    assert out == f"<style>{_lf(css)}</style>"
