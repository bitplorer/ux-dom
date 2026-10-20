"""#81: CSS rule nodes render only as CSS (inside ``<style>``) or standalone.

A ``StyleTags`` node (``CSSClass``, ``CSSId``, ``CSS``, ``Keyframes``) writes
its selector and rule text raw. Inside ``<style>`` the parent neutralizes
``</style`` over the joined body (#53). As the child of any other element the
text landed in HTML body context, so a selector such as ``<img onerror=…>``
ran. A CSS node there now raises instead of emitting anything, including when
``lazy`` produces it: a lazy result renders as a child at the lazy's position.
"""

from __future__ import annotations

import asyncio

import pytest

from ux_dom import Document
from ux_dom.dom import div, script, span, style
from ux_dom.dom.src.csstags import CSS, CSSClass, CSSId, CSSProperty, Keyframes
from ux_dom.dom.src.ext import PlaceholderTag, Tags
from ux_dom.dom.src.utils.dom_util import InvalidNodeContext, lazy

IMG = "<img src=x onerror=alert(1)>"


class btn(CSSClass):
    pass


class main(CSSId):
    pass


class body_(CSS):
    pass


class fade(Keyframes):
    pass


class Order(Tags):
    render_tag = False
    name = CSSProperty()


RULES = {
    "CSSClass": lambda: btn(color="red"),
    "CSSId": lambda: main(color="red"),
    "CSS": lambda: body_(margin=0),
    "Keyframes": lambda: fade(from_={"opacity": 0}, to={"opacity": 1}),
    "CSSProperty.cls": lambda: Order.name.cls(color="red"),
    "CSSProperty.apply": lambda: Order.name.apply(apply="p-2"),
}

HTML_PARENTS = {
    "div": lambda rule: div(rule),
    "nested": lambda rule: div(span(rule)),
    "script": lambda rule: script(rule),
    "placeholder": lambda rule: div(PlaceholderTag(rule)),
    "and": lambda rule: div(rule & btn(margin=0)),
    "document": lambda rule: Document(ensure_csrf_token=False)(rule),
    "lazy": lambda rule: div(lazy(lambda: rule)),
    "lazy-wrapper": lambda rule: div(lazy(lambda: Tags(rule, render_tag=False))),
    "lazy-nested": lambda rule: div(lazy(lambda: lazy(lambda: rule))),
}


def _async_render(node, pretty=False) -> str:
    async def run():
        return "".join([t async for t in node.__async_render__(pretty=pretty)])

    return asyncio.run(run())


RENDERS = [
    lambda node: node.__render__(pretty=False),
    lambda node: node.__render__(pretty=True),
    _async_render,
    lambda node: _async_render(node, pretty=True),
]


def _renders(node):
    return [render(node) for render in RENDERS]


@pytest.mark.parametrize("parent", HTML_PARENTS)
@pytest.mark.parametrize("rule", RULES)
def test_css_rule_outside_style_raises(rule, parent):
    node = HTML_PARENTS[parent](RULES[rule]())
    for render in RENDERS:
        with pytest.raises(InvalidNodeContext, match="<style>"):
            render(node)


def test_assigned_selector_never_reaches_html():
    """The #55 review row: a Python-assigned selector rendered under ``div``."""
    rule = btn(color="red")
    rule.tagname = IMG
    with pytest.raises(InvalidNodeContext, match="<style>"):
        div(rule).__render__(pretty=False)


@pytest.mark.parametrize("rule", RULES)
def test_css_rule_inside_style_renders(rule):
    for out in _renders(style(RULES[rule]())):
        assert out.startswith("<style>") and out.endswith("</style>"), out
        assert "{" in out, out


def test_css_rules_compose_inside_style():
    outer = btn(color="red")
    outer.add(main(margin=0))
    assert (
        style(outer, btn(color="red") & main(margin=0)).__render__(pretty=False)
        == "<style>.btn{color:red;#main{margin:0;}}.btn{color:red;}#main{margin:0;}</style>"
    )


def test_standalone_rule_is_css_text():
    assert btn(color="red").__render__(pretty=False) == ".btn{color:red;}"


@pytest.mark.parametrize(
    "selector", [f"x</style>{IMG}", f"x</STYLE >{IMG}", f"x</st{IMG}"]
)
def test_selector_cannot_close_style(selector):
    rule = btn(color="red")
    rule.tagname = selector
    for out in _renders(div(style(rule), span("ok"))):
        assert out.lower().count("</style") == 1, out
        assert out.index("</style>") > out.index("{color:red;}"), out


def test_value_cannot_close_style():
    out = style(btn(color=f"red</style>{IMG}")).__render__(pretty=False)
    assert out.count("</style>") == 1 and "<img" not in out, out


def test_refusal_is_a_value_error():
    assert issubclass(InvalidNodeContext, ValueError)


@pytest.mark.parametrize("rule", RULES)
def test_lazy_rule_inside_style_renders(rule):
    make = RULES[rule]
    expected = style(make()).__render__(pretty=False)
    assert style(lazy(make)).__render__(pretty=False) == expected


def test_lazy_result_keeps_its_own_parent():
    rule = btn(color="red")
    home = style(rule)
    assert style(lazy(lambda: rule)).__render__(pretty=False) == (
        "<style>.btn{color:red;}</style>"
    )
    with pytest.raises(InvalidNodeContext):
        div(lazy(lambda: rule)).__render__(pretty=False)
    assert rule.parent is home


def test_lazy_tag_result_still_renders_in_html():
    assert div(lazy(lambda: span("a<b"))).__render__(pretty=False) == (
        "<div><span>a&lt;b</span></div>"
    )
