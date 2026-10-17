"""Attribute names are validated on every render path (fail closed)."""

from __future__ import annotations

import pytest

from ux_dom.dom import a, div, span
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.utils.dom_util import InvalidAttributeName, checked_attr_name

BAD = [
    'x" onmouseover="alert(1)',
    "x onmouseover",
    "x\tonclick",
    "x\nonclick",
    "a'b",
    "a>b",
    "a/b",
    "a=b",
    "a\x00b",
    "a\x1fb",
    "a\x7fb",
    "",
]
GOOD = [
    "class",
    "id",
    "data-x",
    "aria-label",
    "@click",
    ":class",
    "x-on:keyup.enter",
    "hx-post",
    "xlink:href",
    "x-bind:href",
    "_hyperscript",
]


@pytest.mark.parametrize("name", BAD)
def test_helper_rejects_bad_names(name):
    with pytest.raises(InvalidAttributeName):
        checked_attr_name(name)


@pytest.mark.parametrize("name", GOOD)
def test_helper_accepts_real_names(name):
    assert checked_attr_name(name) == name


def test_onmouseover_breakout_raises_on_tags_render():
    tag = span("t", **{'x" onmouseover="alert(1)': "1"})
    with pytest.raises(InvalidAttributeName):
        tag.__render__(pretty=False)


def test_breakout_raises_on_valueless_attribute():
    tag = span("t")
    tag.attributes['x" onmouseover="alert(1)'] = None
    with pytest.raises(InvalidAttributeName):
        tag.__render__(pretty=False)


def test_breakout_raises_on_str():
    with pytest.raises(InvalidAttributeName):
        str(div(**{"a b": "1"}))


def test_breakout_raises_on_dom_tag_render():
    class plain(dom_tag):
        pass

    tag = plain()
    tag.attributes['x" onmouseover="alert(1)'] = "1"
    with pytest.raises(InvalidAttributeName):
        tag.__render__(pretty=False)


def test_invalid_name_is_a_value_error():
    assert issubclass(InvalidAttributeName, ValueError)


def test_real_names_still_render():
    html = a(
        "x", href="/a", **{"@click": "go()", "x-on:keyup.enter": "go()"}
    ).__render__(pretty=False)
    assert 'href="/a"' in html and '@click="go()"' in html
