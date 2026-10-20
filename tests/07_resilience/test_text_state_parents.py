"""#90: no descendant can end an RCDATA or RAWTEXT parent early.

The HTML tokenizer reads the body of ``textarea`` / ``title`` as RCDATA
(§13.2.5.2) and of ``xmp``, ``iframe``, ``noembed``, ``noframes`` and (with
scripting on) ``noscript`` as RAWTEXT (§13.2.5.3). In both states only the
parent's own end tag (``</textarea`` …, any ASCII case) changes parser state.
Text children are escaped, but a ``style`` / ``script`` body (#53), a comment
or ``raw()`` is not, so ``textarea(style("</textarea><img onerror=…>"))``
ended the textarea and ran the ``<img>``.

The parent now checks its own joined body. RCDATA decodes character
references, so ``</textarea`` becomes ``&lt;/textarea`` (the same value).
RAWTEXT decodes nothing and has no equivalent spelling, so the render raises
``InvalidNodeContext``. The rule holds in every namespace: inside ``<svg>`` a
breakout tag (``<div>``, ``<p>``) pops the parser back to HTML, so a
``textarea`` the tree places under ``svg`` can still be RCDATA (§13.2.6.5).
"""

from __future__ import annotations

import asyncio
import re

import pytest

from ux_dom import Component
from ux_dom.dom import (
    comment,
    div,
    iframe,
    noscript,
    p,
    raw,
    script,
    span,
    style,
    svg,
    template,
    textarea,
    title,
)
from ux_dom.dom.src.ext import Tags
from ux_dom.dom.src.html_string import create_dynamic_element
from ux_dom.dom.src.htmltags import html_tag
from ux_dom.dom.src.svgtags import svg_tag
from ux_dom.dom.src.svgtags import title as svg_title
from ux_dom.dom.src.utils.dom_util import InvalidNodeContext, lazy

IMG = "<img src=x onerror=alert(1)>"


def _tag(name, base=Tags):
    return type(name.replace("-", "_"), (base,), {"tagname": name})


foreignObject = _tag("foreignObject", svg_tag)
xmp = create_dynamic_element("xmp")
noembed = _tag("noembed", html_tag)
noframes = _tag("NOFRAMES", html_tag)

RCDATA = {"textarea": textarea, "title": title}
RAWTEXT = {
    "xmp": xmp,
    "iframe": iframe,
    "noembed": noembed,
    "noframes": noframes,
    "noscript": noscript,
}


def _async(node, **kw):
    async def go():
        return "".join([t async for t in node.__async_render__(**kw)])

    return asyncio.run(go())


def _renders(node):
    return [
        node.__render__(pretty=False),
        node.__render__(pretty=True),
        _async(node, pretty=False),
        _async(node, pretty=True),
    ]


def _component(el):
    class Wrap(Component):
        def render(self):
            return el

    return Wrap()


def _split(end):
    s = style("x</", end[:3])
    s.add(raw(end[3:] + ">" + IMG))
    return s


# Descendants whose output is not escaped text, as a function of the end tag.
CHILDREN = {
    "style": lambda end: style(f"</{end}>{IMG}"),
    "script": lambda end: script(f"</{end}>{IMG}"),
    "upper-case": lambda end: style(f"</{end.upper()} >{IMG}"),
    "slash": lambda end: style(f"</{end}/{IMG}"),
    "newline": lambda end: style(f"</{end}\n>{IMG}"),
    "deep": lambda end: div(span(div(style(f"</{end}>{IMG}")))),
    "component": lambda end: _component(div(style(f"</{end}>{IMG}"))),
    "lazy": lambda end: lazy(lambda: style(f"</{end}>{IMG}")),
    "comment": lambda end: comment(f" </{end}>{IMG} "),
    "raw": lambda end: raw(f"</{end}>{IMG}"),
    "split-across-children": _split,
}


def _end_tags(out, name):
    return len(re.findall(rf"</{name}", out, re.I | re.A))


@pytest.mark.parametrize("child", sorted(CHILDREN))
@pytest.mark.parametrize("name", sorted(RCDATA))
def test_rcdata_parent_cannot_be_ended_by_a_descendant(name, child):
    node = div(RCDATA[name](CHILDREN[child](name)))
    for out in _renders(node):
        assert _end_tags(out, name) == 1, out  # only the element's own end tag
        assert "&lt;/" in out, out


@pytest.mark.parametrize("child", sorted(CHILDREN))
@pytest.mark.parametrize("name", sorted(RAWTEXT))
def test_rawtext_parent_refuses_a_descendant_end_tag(name, child):
    node = div(RAWTEXT[name](CHILDREN[child](name)))
    for render in (
        lambda n: n.__render__(pretty=False),
        lambda n: n.__render__(pretty=True),
        lambda n: _async(n, pretty=False),
        lambda n: _async(n, pretty=True),
    ):
        with pytest.raises(InvalidNodeContext, match=name):
            render(node)


# The tree may put these under <svg>, but a breakout tag pops the parser back
# to HTML and the parent is RCDATA / RAWTEXT again.
FOREIGN = {
    "svg > foreignObject": lambda el: svg(foreignObject(el)),
    "svg > foreignObject > div": lambda el: svg(foreignObject(div(el))),
    "svg > p (breakout)": lambda el: svg(p(el)),
    "svg > [div, el] (breakout sibling)": lambda el: svg(div(), el),
    "svg": lambda el: svg(el),
    "template": lambda el: template(el),
    "template > svg > foreignObject": lambda el: template(svg(foreignObject(el))),
}


@pytest.mark.parametrize("where", sorted(FOREIGN))
def test_textarea_is_guarded_in_every_namespace(where):
    node = FOREIGN[where](textarea(style(f"</textarea>{IMG}")))
    for out in _renders(node):
        assert _end_tags(out, "textarea") == 1, out


@pytest.mark.parametrize("where", sorted(FOREIGN))
def test_xmp_is_guarded_in_every_namespace(where):
    with pytest.raises(InvalidNodeContext):
        FOREIGN[where](xmp(style(f"</xmp>{IMG}"))).__render__(pretty=False)


def test_outer_parent_is_guarded_through_an_inner_one():
    # In <textarea>, "<title>" is text: only </textarea ends the parent.
    out = textarea(title(style(f"</textarea>{IMG}"))).__render__(pretty=False)
    assert _end_tags(out, "textarea") == 1, out


def test_svg_title_is_guarded():
    out = svg(svg_title(style(f"</title>{IMG}"))).__render__(pretty=False)
    assert _end_tags(out, "title") == 1, out


# Legitimate content: byte-identical to main.
@pytest.mark.parametrize(
    "node, html",
    [
        (
            textarea("a<b & c</textarea>\n  x"),
            "<textarea>a&lt;b &amp; c&lt;/textarea&gt;\n  x</textarea>",
        ),
        (textarea("<title>", name="t"), '<textarea name="t">&lt;title&gt;</textarea>'),
        (
            title("Atelier — Linen & Object"),
            "<title>Atelier — Linen &amp; Object</title>",
        ),
        (title("x</title>"), "<title>x&lt;/title&gt;</title>"),
        (textarea(raw("&amp; <b>")), "<textarea>&amp; <b></textarea>"),
        (xmp("</xmp>"), "<xmp>&lt;/xmp&gt;</xmp>"),
        (
            noscript(style("a{color:red}"), span("x")),
            "<noscript><style>a{color:red}</style><span>x</span></noscript>",
        ),
        (iframe(src="/a"), '<iframe src="/a"></iframe>'),
        (div(style("</textarea>")), "<div><style></textarea></style></div>"),
    ],
)
def test_legitimate_content_is_unchanged(node, html):
    assert node.__render__(pretty=False) == html
    assert _async(node, pretty=False) == html


def test_rcdata_value_is_preserved():
    # &lt; decodes to "<" in RCDATA, so the browser value is unchanged.
    out = textarea(raw("a</TEXTAREA b")).__render__(pretty=False)
    assert out == "<textarea>a&lt;/TEXTAREA b</textarea>"
