"""SVG animation values and srcset candidates get the URL check (#86).

``<animate attributeName="href" to="javascript:…">`` ran script in Chromium.
On ``animate``, ``set``, ``animateMotion`` and ``animateTransform``, ``to``,
``from``, ``by`` and each ``;`` item of ``values`` are checked as URLs,
whatever ``attributeName`` says. Browser oracle:
``tests/06_browser/test_svg_animation_url_browser.py``.
"""

from __future__ import annotations

import pytest
from markupsafe import Markup

from ux_dom.dom import div, img, link
from ux_dom.dom.src.html_string import create_dynamic_element
from ux_dom.dom.src.svgtags import animate, animateMotion, animateTransform, svg_tag
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, safe_attr_value

svg_set = type("set", (svg_tag,), {"tagname": "set"})
ANIMATIONS = [animate, svg_set, animateMotion, animateTransform]
EVIL = [
    "javascript:hit()",
    "JaVaScRiPt:hit()",
    "  javascript:hit()",
    "\x01javascript:hit()",
    "java\tscript:hit()",
    "java\nscript:hit()",
    "java\rscript:hit()",
    "data:text/html,<script>hit()</script>",
    Markup("javascript:hit()"),
]


@pytest.mark.parametrize("tag", ANIMATIONS, ids=lambda t: t.__name__)
@pytest.mark.parametrize("attr", ["to", "from", "by", "values"])
@pytest.mark.parametrize("value", EVIL, ids=repr)
def test_animation_url_values_refused(tag, attr, value):
    html = tag(attributeName="href", **{attr: value}).__render__(pretty=False)
    name = "set" if tag is svg_set else tag.__name__
    assert html == f'<{name} attributeName="href" {attr}="{UNSAFE_URL}"></{name}>'


@pytest.mark.parametrize("target", ["href", "xlink:href", "opacity", "HREF", ""])
def test_attribute_name_is_not_parsed(target):
    html = animate(attributeName=target, to="javascript:x").__render__(pretty=False)
    assert html == f'<animate attributeName="{target}" to="{UNSAFE_URL}"></animate>'


def test_each_values_item_is_checked():
    assert (
        animate(values="#a;javascript:hit()").__render__(pretty=False)
        == f'<animate values="{UNSAFE_URL}"></animate>'
    )


@pytest.mark.parametrize(
    "attrs",
    [
        {"attributeName": "opacity", "values": "0;1;0.5"},
        {"attributeName": "fill", "from": "red", "to": "rgb(0, 128, 0)"},
        {"attributeName": "width", "by": "10px"},
        {"attributeName": "href", "values": "#c1; #c2;"},
        {"attributeName": "href", "to": "https://example.com/a?b=c"},
        {"attributeName": "fill", "values": "url(#g1);url(#g2)"},
    ],
)
def test_ordinary_animation_values_kept(attrs):
    html = animate(**attrs).__render__(pretty=False)
    body = " ".join(f'{k}="{v}"' for k, v in sorted(attrs.items()))
    assert html == f"<animate {body}></animate>"


def test_animate_transform_and_motion_values_kept():
    assert (
        animateTransform(type="rotate", values="0 50 50;360 50 50").__render__(pretty=False)
        == '<animateTransform type="rotate" values="0 50 50;360 50 50"></animateTransform>'
    )
    assert (
        animateMotion(values="0,0;10,10").__render__(pretty=False)
        == '<animateMotion values="0,0;10,10"></animateMotion>'
    )


def test_other_elements_keep_to_and_values():
    assert div(to="javascript:x").__render__(pretty=False) == '<div to="javascript:x"></div>'
    fe = create_dynamic_element("feColorMatrix")
    assert fe(values="1 0 0 0 0").__render__(pretty=False) == '<feColorMatrix values="1 0 0 0 0"></feColorMatrix>'


@pytest.mark.parametrize("tag", ["animate", "SET", "animatemotion", "svg:animateTransform"])
def test_helper_tag_context(tag):
    assert safe_attr_value("to", "javascript:x", tag) == UNSAFE_URL
    assert safe_attr_value("values", "0;1", tag) == "0;1"
    assert safe_attr_value("to", "javascript:x") == "javascript:x"
    assert safe_attr_value("to", "javascript:x", "div") == "javascript:x"


@pytest.mark.parametrize(
    "value",
    [
        "a.png",
        "a.png 1x, b.png 2x",
        "a.png 480w,b.png 800w",
        "https://example.com/a.png 2x",
        "data:image/png;base64,AA,BB 1x, /b.png 2x",
        "a.png (x, javascript:y) 1x",
        "",
    ],
)
def test_srcset_candidates_kept(value):
    assert img(srcset=value).__render__(pretty=False) == f'<img srcset="{value}">'


@pytest.mark.parametrize(
    "value",
    [
        "javascript:x",
        "a.png 1x, javascript:x 2x",
        "a.png 1x,javascript:x 2x",
        "a.png,, JAVASCRIPT:x",
        "//evil.example/a.png 2x",
        "data:image/svg+xml,<svg/> 1x",
    ],
)
def test_srcset_candidates_refused(value):
    assert img(srcset=value).__render__(pretty=False) == f'<img srcset="{UNSAFE_URL}">'
    assert safe_attr_value("imagesrcset", value) == UNSAFE_URL


def test_link_imagesrcset_refused():
    html = link(rel="preload", imagesrcset="javascript:x 1x").__render__(pretty=False)
    assert html == f'<link imagesrcset="{UNSAFE_URL}" rel="preload">'
