"""#83: ``<style>`` / ``<script>`` inside ``<svg>`` / ``<math>`` are not raw text.

In an HTML document the parser handles an element whose parent is SVG or
MathML by the rules for foreign content (HTML spec §13.2.6.5): a ``<style>`` or
``<script>`` there is an SVG/MathML element, its body is tokenized as markup
and character references are decoded. #53's verbatim body is therefore live
markup there, so the renderer emits it as one CDATA section, which the parser
keeps verbatim (§13.2.5.42); a ``]]>`` in the body is split across two. An
author's own outer ``<![CDATA[ … ]]>`` (the usual SVG idiom) is unwrapped
first, so it still works.

The HTML rules resume below an HTML integration point (SVG ``foreignObject``,
``desc``, ``title``; MathML ``annotation-xml`` with an HTML ``encoding``) and a
MathML text integration point (``mi``, ``mo``, ``mn``, ``ms``, ``mtext``; not
for ``mglyph`` / ``malignmark``) (§13.2.6 tree construction dispatcher). There
#53's raw text applies again.
"""

from __future__ import annotations

import asyncio
import re

import pytest

from ux_dom import Component
from ux_dom.dom import div, g, raw, script, style, svg
from ux_dom.dom.src.ext import PlaceholderTag, Tags
from ux_dom.dom.src.svgtags import desc, foreignObject
from ux_dom.dom.src.svgtags import title as svg_title
from ux_dom.dom.src.utils.dom_util import lazy, neutralize_raw_text

IMG = "<img src=x onerror=alert(1)>"
CSS = 'a > b::after { content: "&<"; }'
JS = "if (a < b && c > d) { window.ok = 1; }"


def _tag(name, base=Tags):
    return type(name.replace("-", "_"), (base,), {"tagname": name})


math = _tag("math")
mi = _tag("mi")
mtext = _tag("mtext")
mglyph = _tag("mglyph")
annotation_xml = _tag("annotation-xml")
mtitle = _tag("title")  # a MathML <title>: not an integration point


def _component(el):
    class Wrap(Component):
        def render(self):
            return el

    return Wrap()


def _body(out, name):
    m = re.search(rf"<{name}>(.*)</{name}>", out, re.S)
    assert m, out
    return m.group(1)


def _cdata_text(body):
    """The text a parser reads from ``body`` that is only CDATA sections."""
    text, rest = [], body.strip()
    while rest:
        assert rest.startswith("<![CDATA["), body
        end = rest.index("]]>")
        text.append(rest[len("<![CDATA[") : end])
        rest = rest[end + 3 :]
    return "".join(text)


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


# Raw-text element as a function of its ancestors, per §13.2.6.
FOREIGN = {
    "svg": lambda el: svg(el),
    "svg > g": lambda el: svg(g(el)),
    "math": lambda el: math(el),
    "math > mi > mglyph": lambda el: math(mi(mglyph(el))),
    "math > annotation-xml": lambda el: math(annotation_xml(el)),
    "math > annotation-xml[encoding=image/svg+xml]": lambda el: math(
        annotation_xml(el, encoding="image/svg+xml")
    ),
    "math > annotation-xml > svg": lambda el: math(
        annotation_xml(svg(el), encoding="text/html")
    ),
    "math > title": lambda el: math(mtitle(el)),
    "svg > foreignObject > svg": lambda el: svg(foreignObject(svg(el))),
    "math > mi > svg": lambda el: math(mi(svg(el))),
    "svg > Component": lambda el: svg(_component(el)),
    "svg > PlaceholderTag": lambda el: svg(PlaceholderTag(el)),
    "div > svg": lambda el: div(svg(el)),
}
HTML = {
    "root": lambda el: el,
    "div": lambda el: div(el),
    "svg > foreignObject": lambda el: svg(foreignObject(el)),
    "svg > g > foreignObject > div": lambda el: svg(g(foreignObject(div(el)))),
    "svg > desc": lambda el: svg(desc(el)),
    "svg > title": lambda el: svg(svg_title(el)),
    "math > mi": lambda el: math(mi(el)),
    "math > mtext": lambda el: math(mtext(el)),
    "math > annotation-xml[encoding=text/html]": lambda el: math(
        annotation_xml(el, encoding="text/html")
    ),
    "math > annotation-xml[encoding=APPLICATION/XHTML+XML]": lambda el: math(
        annotation_xml(el, encoding="APPLICATION/XHTML+XML")
    ),
    "foreignObject outside svg": lambda el: div(foreignObject(el)),
}


@pytest.mark.parametrize("where", sorted(FOREIGN))
@pytest.mark.parametrize("kind", [style, script])
@pytest.mark.parametrize(
    "payload",
    [IMG, "</style>" + IMG, "</script>" + IMG, "]]>" + IMG, "x]]]]>" + IMG, CSS, JS],
)
def test_foreign_body_is_one_cdata_section(where, kind, payload):
    name = kind.__name__
    for out in _renders(FOREIGN[where](kind(payload))):
        # Markup only as CDATA text; it reads as the (#53-neutralized) body.
        body = _body(out, name)
        assert _cdata_text(body).strip() == neutralize_raw_text(payload, name), out


@pytest.mark.parametrize("where", sorted(HTML))
@pytest.mark.parametrize("kind", [style, script])
def test_html_context_keeps_raw_text(where, kind):
    text = CSS if kind is style else JS
    for out in _renders(HTML[where](kind(text))):
        assert _body(out, kind.__name__).strip() == text, out


@pytest.mark.parametrize("where", sorted(HTML))
def test_html_context_keeps_breakout_guard(where):
    out = HTML[where](style("x</style>" + IMG)).__render__(pretty=False)
    assert "<\\/style>" + IMG in out
    assert len(re.findall(r"</style", out, re.I)) == 1


def test_split_children_and_raw_are_one_cdata_section():
    s = style("<im", "g src=x ")
    s.add(raw("onerror=alert(1)>"))
    out = svg(s).__render__(pretty=False)
    assert _body(out, "style") == f"<![CDATA[{IMG}]]>"


@pytest.mark.parametrize("kind", [style, script])
def test_author_cdata_wrapper_is_unwrapped(kind):
    text = CSS if kind is style else JS
    out = svg(kind(f"\n  <![CDATA[{text}]]>\n")).__render__(pretty=False)
    assert _body(out, kind.__name__) == f"<![CDATA[{text}]]>"


def test_commented_cdata_idiom_stays_comments():
    js = "//<![CDATA[\nwindow.ok = 1 < 2;\n//]]>"
    out = svg(script(js)).__render__(pretty=False)
    assert _cdata_text(_body(out, "script")) == js


@pytest.mark.parametrize("kind", [style, script])
def test_lazy_tag_renders_in_its_parent_context(kind):
    out = svg(lazy(lambda: kind(IMG))).__render__(pretty=False)
    assert _body(out, kind.__name__) == f"<![CDATA[{IMG}]]>"


def test_annotation_xml_needs_every_encoding_to_be_html():
    # Attributes render sorted, and a browser keeps the first of a duplicate:
    # here ``ENCODING="x"``. Count it as foreign unless every spelling is HTML.
    el = annotation_xml(style(IMG), **{"encoding": "text/html", "ENCODING": "x"})
    out = math(el).__render__(pretty=False)
    assert f"<![CDATA[{IMG}]]>" in out


def test_parent_cycle_does_not_hang():
    s = style(IMG)
    outer = svg(s)
    outer.parent = s  # a cycle in the parent chain only, not in children
    assert s.__render__(pretty=False) == f"<style><![CDATA[{IMG}]]></style>"
