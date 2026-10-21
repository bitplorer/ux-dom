"""The LF right after ``<pre>``, ``<listing>`` and ``<textarea>`` (#127).

The HTML parser drops one LF right after these start tags (§13.2.6.4.7), so
``<textarea>\\nhello`` has the value ``hello``. The renderer writes one more LF
before a body that starts with one, and the string parser drops the first LF
as the browser does, so parse and render round-trip. Browser checks:
``tests/06_browser/test_pretty_raw_text_browser.py`` and
``tests/06_browser/test_parse_whitespace_browser.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from ux_dom.dom import pre, raw, span, svg, textarea
from ux_dom.dom.src.html_string import _sanitized_html, create_dynamic_element
from ux_dom.dom.src.parse_html import tokenize_html


def _listing(*children):
    return create_dynamic_element("listing")(*children)


def _async(node):
    async def go():
        return "".join([t async for t in node.__async_render__(pretty=False)])

    return asyncio.run(go())


RENDERS = [
    lambda n: n.__render__(pretty=False),
    lambda n: n.__render__(pretty=True),
    _async,
]

# (node, every render): the body's own LF is kept behind the one dropped.
CASES = {
    "textarea": (lambda: textarea("\nhello"), "<textarea>\n\nhello</textarea>"),
    "pre": (lambda: pre("\n\nx"), "<pre>\n\n\nx</pre>"),
    "listing": (lambda: _listing("\nx"), "<listing>\n\nx</listing>"),
    "only-lf": (lambda: pre("\n"), "<pre>\n\n</pre>"),
    "raw": (lambda: pre(raw("\nx")), "<pre>\n\nx</pre>"),
    # A reference to an LF is an LF to the parser.
    "raw-ref": (lambda: pre(raw("&#10;x")), "<pre>\n&#10;x</pre>"),
    "raw-hex": (lambda: pre(raw("&#x0A;x")), "<pre>\n&#x0A;x</pre>"),
    "raw-not-lf": (lambda: pre(raw("&#105;x")), "<pre>&#105;x</pre>"),
    "text-ref": (lambda: textarea("&#10;x"), "<textarea>&amp;#10;x</textarea>"),
    "no-lf": (lambda: textarea("x\n"), "<textarea>x\n</textarea>"),
    "tag-first": (lambda: pre(span("\nx")), "<pre><span>\nx</span></pre>"),
    # Foreign content: the parser drops nothing after an SVG ``textarea``.
    "svg": (lambda: svg(textarea("\nx")), "<svg><textarea>\nx</textarea></svg>"),
}


@pytest.mark.parametrize("case", CASES)
def test_render_writes_the_lf_the_parser_drops(case):
    make, expected = CASES[case]
    for render in RENDERS:
        assert render(make()) == expected


@pytest.mark.parametrize(
    "source,ast",
    [
        ("<pre>\nx</pre>", "<pre>x</pre>"),
        ("<pre>\n\nx</pre>", "<pre>\n\nx</pre>"),
        ("<textarea>\n</textarea>", "<textarea></textarea>"),
        ("<listing>\n a</listing>", "<listing> a</listing>"),
        ("<pre/>\nx</pre>", "<pre>x</pre>"),
        # A reference to an LF is the same token.
        ("<pre>&#10;x</pre>", "<pre>x</pre>"),
        ("<pre>&#x0A;x</pre>", "<pre>x</pre>"),
        ("<textarea>&NewLine;x</textarea>", "<textarea>x</textarea>"),
        # Only the very next token: a comment or a stray end tag comes first.
        ("<pre><!--c-->\nx</pre>", "<pre><!--c-->\nx</pre>"),
        ("<pre></b>\nx</pre>", "<pre>\n\nx</pre>"),
        ("<pre>x\n</pre>", "<pre>x\n</pre>"),
        ("<svg><textarea>\nx</textarea></svg>", "<svg><textarea>\nx</textarea></svg>"),
    ],
)
def test_parser_drops_the_first_lf(source, ast):
    assert tokenize_html(source).render() == ast


@pytest.mark.parametrize(
    "source,expected",
    [
        ("<textarea>\nhello</textarea>", "<textarea>hello</textarea>"),
        ("<textarea>\n\nhello</textarea>", "<textarea>\n\nhello</textarea>"),
        ("<pre>&#10;x</pre>", "<pre>x</pre>"),
        ("<pre>&NewLine;\nx</pre>", "<pre>\n\nx</pre>"),
        ("<pre>&#10;&#10;x</pre>", "<pre>\n&#10;x</pre>"),
    ],
)
def test_sanitizer_round_trip_is_idempotent(source, expected):
    assert _sanitized_html(source) == expected
    assert _sanitized_html(expected) == expected
