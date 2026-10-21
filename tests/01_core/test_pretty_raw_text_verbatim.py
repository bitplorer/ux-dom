"""Pretty render keeps raw text and preformatted bodies verbatim (#88).

The body of ``script``, ``style``, ``textarea``, ``title``, ``xmp``,
``iframe``, ``noembed``, ``noframes``, ``noscript``, ``plaintext``, ``pre``
and ``listing`` is content: an added newline or indent changes a JS template
literal, a CSS string, a form value or preformatted text. Pretty render
writes these bodies exactly as the flat render does. The element is matched
by the name its start tag writes, as the HTML parser matches it. The browser
check is ``tests/06_browser/test_pretty_raw_text_browser.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from ux_dom import Fragment
from ux_dom.dom import (
    b,
    div,
    iframe,
    noscript,
    p,
    pre,
    script,
    span,
    style,
    textarea,
    title,
)
from ux_dom.dom.src.ext import Tags
from ux_dom.dom.src.html_string import create_dynamic_element
from ux_dom.dom.src.svgtags import svg

JS = "const s = `a\n  b\n`;\nconst c = 'x\\\n   y';"


def _tag(name):
    return type(name, (Tags,), {"tagname": name})


def _async_pretty(node):
    async def go():
        return "".join([t async for t in node.__async_render__(pretty=True)])

    return asyncio.run(go())


BODIES = {
    "script": lambda: script(JS),
    "script-split": lambda: script("let a = `x\n", "  y`;"),
    "style": lambda: style(".c::before { content: 'a\\\n  b'; }\n"),
    "textarea": lambda: textarea("\nfirst\n  second\n"),
    "title": lambda: title("a\n  b"),
    "iframe": lambda: iframe("a\n  b"),
    "noscript": lambda: noscript("a\n  b"),
    "pre-text": lambda: pre("\ncode\n  indented"),
    "pre-elements": lambda: pre(span("a"), span("b")),
    "pre-nested": lambda: pre(div(p("a"), p("b"))),
    "xmp": lambda: create_dynamic_element("xmp")("a\n  b"),
    "noembed": lambda: _tag("noembed")("a\n  b"),
    "noframes": lambda: _tag("noframes")("a\n  b"),
    "plaintext": lambda: create_dynamic_element("plaintext")("a\n  b"),
    "listing": lambda: create_dynamic_element("listing")(span("a"), span("b")),
    "listing-text": lambda: create_dynamic_element("listing")("\na\n  b"),
    "PRE": lambda: _tag("PRE")(span("a"), span("b")),
    "PRE-text": lambda: _tag("PRE")("a\n  b"),
    "PRE-blocks": lambda: _tag("PRE")(div(p("a"), p("b"))),
    "TEXTAREA": lambda: _tag("TEXTAREA")("a\n  b"),
    "Script": lambda: _tag("Script")("x = `a\n  b`"),
}


@pytest.mark.parametrize("name", list(BODIES))
def test_body_is_written_as_the_flat_render_writes_it(name):
    flat = BODIES[name]().__render__(pretty=False)
    node = div(BODIES[name]())
    expected = "<div>\n  " + flat + "\n</div>"
    assert str(node) == expected
    assert node.__render__(pretty=True) == expected
    assert _async_pretty(node) == expected


def test_script_template_literal_exact():
    assert str(div(script("const s = `a\nb`;"))) == (
        "<div>\n  <script>const s = `a\nb`;</script>\n</div>"
    )


def test_pretty_adds_no_layout_after_a_pre_or_textarea_start_tag():
    # Only a body that starts with an LF gets one more, which HTML drops (#127).
    assert str(pre(span("a"), span("b"))) == "<pre><span>a</span><span>b</span></pre>"
    assert str(textarea("\nx")) == "<textarea>\n\nx</textarea>"
    assert str(pre("\n\nx")) == "<pre>\n\n\nx</pre>"


@pytest.mark.parametrize(
    "body",
    [
        lambda: script(JS),
        lambda: style("a { content: 'x\\\n  y'; }\nb {}"),
        lambda: script("<![CDATA[\n", JS, "\n]]>"),
    ],
)
def test_foreign_content_cdata_body_matches_flat(body):
    # #85: inside <svg> the body is one CDATA section; its text is the value.
    # The layout around the element is #93's; the element itself is flat.
    node = div(p("x"), svg(body()))
    element = svg(body()).__render__(pretty=False)[len("<svg>") : -len("</svg>")]
    assert element.startswith(("<script><![CDATA[", "<style><![CDATA["))
    assert element in str(node)
    assert _async_pretty(node) == str(node)


def test_layout_around_the_body_is_unchanged():
    assert str(div(p("x", b("y")), script("a\nb"))) == (
        "<div>\n  <p>x<b>y</b></p>\n  <script>a\nb</script>\n</div>"
    )
    assert str(Fragment(div(p("x")), pre("y"))) == (
        "<div>\n  <p>\n    x\n  </p>\n</div>\n<pre>y</pre>"
    )
