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
from unittest import mock

import pytest

from ux_dom.dom import a, div, img, p, script, span, style
from ux_dom.dom.src import htmltags
from ux_dom.dom.src.ext import Tags
from ux_dom.dom.src.svgtags import desc, foreignObject, g, rect, svg, svg_tag
from ux_dom.dom.src.svgtags import title as svg_title
from ux_dom.dom.src.utils.dom_util import lazy, neutralize_raw_text

CSS = 'a > b::after { content: "&<"; }'
IMG = "<img src=x onerror=alert(1)>"


def _tag(name, base=Tags, **kw):
    return type(name.replace("-", "_"), (base,), {"tagname": name, **kw})


svg_a = _tag("a", svg_tag)
math, mi, mglyph, mtext = _tag("math"), _tag("mi"), _tag("mglyph"), _tag("mtext")
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
    # #128: the HTML element's end tag closes it, not the integration point
    # of the same name below it.
    "svg > desc > [desc, el]": lambda el: svg(desc(desc(), el)),
    "math > mi > [mi, el]": lambda el: math(mi(mi(), el)),
    "math > mtext > [mtext, el]": lambda el: math(mtext(mtext(), el)),
    "svg > g > desc > [g, el]": lambda el: svg(g(desc(g(), el))),
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
    # #91 writes the inner title's end tag as ``&lt;/title``: its RCDATA
    # runs on to the outer ``</title>``, which the parser does not see.
    "svg > [a > [title > title, p], el]": lambda el: svg(
        svg_a(svg_title(svg_title()), p()), el
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


def test_script_after_same_name_html_element_is_raw_text():
    # #128: was ``<![CDATA[``, a SyntaxError in Chromium.
    out = svg(desc(desc(), script("1"))).__render__(pretty=False)
    assert out == "<svg><desc><desc></desc><script>1</script></desc></svg>"


def test_script_after_breakout_is_raw_text():
    js = "if (a < b && c > d) { go(); }"
    out = svg(div(), script(js)).__render__(pretty=False)
    assert out == f"<svg><div></div><script>{js}</script></svg>"


def test_outer_style_after_closed_svg_is_html():
    # The inner </svg> closes the outer <svg> too (foreign end tag rules).
    out = svg(desc(svg(g(p()))), rect(), style(CSS)).__render__(pretty=False)
    assert f"<style>{CSS}</style>" in out


def _size(node):
    return 1 + sum(_size(c) for c in getattr(node, "children", ()))


def _count_start_tags(node, render):
    real, calls = htmltags._start_tag, []

    def counting(*args):
        calls.append(1)
        return real(*args)

    with mock.patch.object(htmltags, "_start_tag", counting):
        render(node)
    return len(calls)


@pytest.mark.parametrize("render", ["sync", "async"])
def test_namespace_replay_is_linear(render):
    # Replaying from the root for each style is n**2 start tags.
    n = 300
    deep = style(CSS)
    for _ in range(n):
        deep = g(rect(), deep, style(CSS))
    shapes = {
        "styles": svg(*[g(rect(), style(CSS)) for _ in range(n)]),
        "deep": svg(deep),
        "wide": svg(*[rect() for _ in range(10 * n)], style(CSS)),
    }
    go = (lambda x: x.__render__(pretty=False)) if render == "sync" else _async
    for name, node in shapes.items():
        elements = _size(node)
        assert _count_start_tags(node, go) < 4 * elements, name


def test_memo_does_not_outlive_a_render():
    s = style(CSS)
    root = svg(g(rect()), s)
    assert f"<style><![CDATA[{CSS}]]></style>" in root.__render__(pretty=False)
    root.children[0].add(p())  # now a breakout comes before the style
    assert f"<style>{CSS}</style>" in root.__render__(pretty=False)
    assert f"<style>{CSS}</style>" in _async(root, pretty=False)
    root.children[0].children.pop()
    assert f"<![CDATA[{CSS}]]>" in _async(root, pretty=False)
    assert f"<![CDATA[{CSS}]]>" in root.__render__(pretty=True)
