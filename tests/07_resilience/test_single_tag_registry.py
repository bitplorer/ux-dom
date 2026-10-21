"""#87: only the HTML void elements are written without an end tag.

HTML void elements (HTML spec §13.1.2) have no end tag. Every other element
needs one. SVG and MathML elements are foreign: an HTML parser leaves a bare
foreign start tag open (§13.2.6.5), so it swallows the siblings after it, as
``<animateTransform>`` did. An empty foreign element is written with an end
tag. camelCase SVG names keep their case.

Chromium oracle: ``tests/06_browser/test_svg_tree_browser.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from ux_dom.dom import div, span
from ux_dom.dom.src import htmltags, svgtags

# HTML spec §13.1.2, as the tags are written.
HTML_VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}

# Every element in ``svgtags``, as the classes are named (SVG 2 element index,
# without ``a`` / ``script`` / ``style``, which are the HTML classes). ``set_``
# and ``filter_`` write ``<set>`` / ``<filter>``: a trailing ``_`` keeps a builtin
# name free, as ``input_``.
SVG_ELEMENTS = [
    "svg",
    "animate",
    "animateMotion",
    "animateTransform",
    "set_",
    "circle",
    "clipPath",
    "defs",
    "desc",
    "discard",
    "ellipse",
    "foreignObject",
    "g",
    "image",
    "line",
    "linearGradient",
    "marker",
    "mask",
    "metadata",
    "mpath",
    "pattern",
    "polygon",
    "polyline",
    "radialGradient",
    "path",
    "rect",
    "stop",
    "switch",
    "symbol",
    "text",
    "textPath",
    "title",
    "tspan",
    "use",
    "view",
    "filter_",
    "feBlend",
    "feColorMatrix",
    "feComponentTransfer",
    "feComposite",
    "feConvolveMatrix",
    "feDiffuseLighting",
    "feDisplacementMap",
    "feDropShadow",
    "feFlood",
    "feFuncA",
    "feFuncB",
    "feFuncG",
    "feFuncR",
    "feGaussianBlur",
    "feImage",
    "feMerge",
    "feMergeNode",
    "feMorphology",
    "feOffset",
    "feSpecularLighting",
    "feTile",
    "feTurbulence",
    "feDistantLight",
    "fePointLight",
    "feSpotLight",
]


def _html_classes():
    for name in htmltags.__all__:
        cls = getattr(htmltags, name)
        if isinstance(cls, type) and issubclass(cls, htmltags.html_tag):
            yield name.strip("_"), cls


def _async(node, **kw):
    async def go():
        return "".join([t async for t in node.__async_render__(**kw)])

    return asyncio.run(go())


def _flat(node):
    """Every flat render: sync and async."""
    return [node.__render__(pretty=False), _async(node, pretty=False)]


def test_only_html_void_elements_are_single():
    singles = {name for name, cls in _html_classes() if cls.is_single}
    assert singles == HTML_VOID


def test_svg_registry_is_the_listed_elements():
    assert svgtags.__all__ == SVG_ELEMENTS


@pytest.mark.parametrize("name", sorted(HTML_VOID))
def test_html_void_has_no_end_tag(name):
    void = getattr(htmltags, "input_" if name == "input" else name)
    node = div(void(), span())
    for out in _flat(node):
        assert out == f"<div><{name}><span></span></div>"


@pytest.mark.parametrize("name", ["param", "keygen", "command"])
def test_html_non_void_has_an_end_tag(name):
    # Not in §13.1.2. ``<command>`` is an ordinary element to the spec's
    # parser, so without ``</command>`` it held the siblings after it.
    el = getattr(htmltags, name)
    for out in _flat(div(el(), span())):
        assert out == f"<div><{name}></{name}><span></span></div>"
    for out in _flat(div(el("x"), span())):
        assert out == f"<div><{name}>x</{name}><span></span></div>"


@pytest.mark.parametrize("name", SVG_ELEMENTS)
def test_empty_svg_element_is_closed(name):
    el, name = getattr(svgtags, name), name.rstrip("_")
    expected = f"<svg><{name}></{name}><rect></rect></svg>"
    for out in _flat(svgtags.svg(el(), svgtags.rect())):
        assert out == expected
    assert svgtags.svg(el(), svgtags.rect()).__render__() == expected


@pytest.mark.parametrize("name", SVG_ELEMENTS)
def test_svg_element_keeps_its_children(name):
    el, name = getattr(svgtags, name), name.rstrip("_")
    expected = f"<svg><{name}><g></g></{name}><rect></rect></svg>"
    for out in _flat(svgtags.svg(el(svgtags.g()), svgtags.rect())):
        assert out == expected


def test_animate_transform_does_not_swallow_its_siblings():
    node = svgtags.svg(
        svgtags.animateTransform(attributeName="transform", type="rotate"),
        svgtags.circle(r="1"),
    )
    assert node.__render__(pretty=False) == (
        '<svg><animateTransform attributeName="transform" type="rotate">'
        '</animateTransform><circle r="1"></circle></svg>'
    )
