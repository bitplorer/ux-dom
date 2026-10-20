"""#92: a breakout tag in foreign content pops the parser back to HTML.

In ``<svg>`` / ``<math>`` a start tag such as ``<p>``, ``<div>`` or ``<img>``
(and ``<font>`` with ``color`` / ``face`` / ``size``) pops the open foreign
elements up to an HTML element or integration point (HTML spec §13.2.6.5).
Its descendants and every later sibling are HTML, so a ``style`` / ``script``
there is raw text (#53), not a CDATA section (#85), which would put a literal
``<![CDATA[`` into the CSS / JS. A later ``svg`` / ``math`` opens foreign
content again.

Where the HTML rules may have closed an element early (``<div>`` closes a
``<p>``, ``<img>`` is void, ``<a>`` closes an ``<a>``), the model keeps every
possible state and stays foreign unless all are HTML. Chromium:
``tests/06_browser/test_foreign_breakout_browser.py``.
"""

from __future__ import annotations

import asyncio
import re

import pytest

from ux_dom.dom import a, div, img, p, script, span, style
from ux_dom.dom.src.ext import Tags
from ux_dom.dom.src.svgtags import desc, g, rect, svg, svg_tag
from ux_dom.dom.src.utils.dom_util import lazy, neutralize_raw_text

CSS = 'a > b::after { content: "&<"; }'
IMG = "<img src=x onerror=alert(1)>"


def _tag(name, base=Tags, **kw):
    return type(name.replace("-", "_"), (base,), {"tagname": name, **kw})


foreignObject = _tag("foreignObject", svg_tag)
svg_a = _tag("a", svg_tag)
math, mi, mglyph = _tag("math"), _tag("mi"), _tag("mglyph")
font = _tag("font")


def _async(node, **kw):
    async def go():
        return "".join([t async for t in node.__async_render__(**kw)])

    return asyncio.run(go())


def _bodies(node):
    """The ``style`` body of each render (sync / async × compact / pretty)."""
    outs = [
        node.__render__(pretty=False),
        node.__render__(pretty=True),
        _async(node, pretty=False),
        _async(node, pretty=True),
    ]
    return [re.search(r"<style>(.*?)</style>", out, re.S).group(1) for out in outs]


# The style is HTML: below a breakout, or after one in the same foreign run.
HTML = {
    "svg > p": lambda el: svg(p(el)),
    "svg > [div, el]": lambda el: svg(div(), el),
    "svg > [g > p, el]": lambda el: svg(g(p()), el),
    "svg > [img, el]": lambda el: svg(img(), el),
    "svg > font[color] > el": lambda el: svg(font(el, color="red")),
    "svg > [FONT[SIZE], el]": lambda el: svg(_tag("FONT")(SIZE="1"), el),
    "math > [span, el]": lambda el: math(span(), el),
    "math > mi > mglyph > [b, el]": lambda el: math(mi(mglyph(_tag("b")(), el))),
    "svg > foreignObject > [svg > p, el]": lambda el: svg(foreignObject(svg(p()), el)),
    "div > [svg > p, el]": lambda el: div(svg(p()), el),
}
# The style is foreign: no breakout reaches it, or the parser may not have
# closed what the tree closes.
FOREIGN = {
    "svg > font": lambda el: svg(font(el)),
    "svg > font[color=False]": lambda el: svg(font(el, color=False)),
    "svg > [p, svg > el]": lambda el: svg(p(), svg(el)),
    "svg > [foreignObject > p, el]": lambda el: svg(foreignObject(p()), el),
    "svg > [lazy, el]": lambda el: svg(lazy(lambda: div()), el),
    "svg > [comment-like text, el]": lambda el: svg("<div>", el),
    # The parser pops the outer <svg> on the inner </svg>: the next style
    # is outside both, but el below <desc> stays where the tree puts it.
    "svg > desc > [svg > g > p, svg > el]": lambda el: svg(
        desc(svg(g(p())), svg(el))
    ),
    # Unsafe on main: these ran script.
    "math > mi > p > [div, mglyph > el]": lambda el: math(
        mi(p(div(), mglyph(el)))
    ),
    "math > mi > img > mglyph > el": lambda el: math(mi(img(mglyph(el)))),
    "math > mi > [open mglyph, el]": lambda el: math(
        mi(_tag("mglyph", is_single=True)(), el)
    ),
    "svg > a > foreignObject > [a > a, el]": lambda el: svg(
        svg_a(foreignObject(a(a()), el))
    ),
    # A breakout's children land in the integration point it popped to.
    "math > mi > mglyph > [img, mglyph > el]": lambda el: math(
        mi(mglyph(img(), mglyph(el)))
    ),
}


@pytest.mark.parametrize("where", sorted(HTML))
def test_after_breakout_style_is_raw_text(where):
    for body in _bodies(HTML[where](style(CSS))):
        assert body == CSS


@pytest.mark.parametrize("where", sorted(HTML))
def test_after_breakout_guard_still_applies(where):
    for body in _bodies(HTML[where](style("x</style>" + IMG))):
        assert body == neutralize_raw_text("x</style>" + IMG, "style")


@pytest.mark.parametrize("where", sorted(FOREIGN))
def test_foreign_style_is_cdata(where):
    for body in _bodies(FOREIGN[where](style(IMG))):
        assert body == f"<![CDATA[{IMG}]]>"


def test_script_after_breakout_is_raw_text():
    js = "if (a < b && c > d) { go(); }"
    out = svg(div(), script(js)).__render__(pretty=False)
    assert out == f"<svg><div></div><script>{js}</script></svg>"


def test_outer_style_after_closed_svg_is_html():
    # The inner </svg> closes the outer <svg> too (foreign end tag rules).
    out = svg(desc(svg(g(p()))), rect(), style(CSS)).__render__(pretty=False)
    assert f"<style>{CSS}</style>" in out
