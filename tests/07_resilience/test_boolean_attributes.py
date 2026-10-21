"""#122: one contract for HTML boolean attributes.

``True`` renders the attribute, ``False`` and ``None`` omit it, and any other
value raises ``TypeError``: ``checked="unchecked"`` used to render checked.
Only the spec's boolean attributes are governed. htmx / Alpine attributes and
enumerated attributes that merely look boolean (``hx-boost``, ``draggable``,
``hidden``) keep their values. Browser check:
``tests/06_browser/test_boolean_state_browser.py``.
"""

from __future__ import annotations

import pytest

from ux_dom.dom import attr, defHTML, div, input_, svg
from ux_dom.dom.src.utils.dom_util import BOOLEAN_ATTRIBUTES
from ux_dom.elements import BooleanField, BooleanInput, CheckboxInput, RadioInput

# WHATWG HTML, "Attributes" index: every attribute whose value is
# "Boolean attribute". ``hidden`` is enumerated (``until-found``), so not here.
SPEC = {
    "allowfullscreen", "alpha", "async", "autofocus", "autoplay", "checked",
    "controls", "default", "defer", "disabled", "formnovalidate", "headingreset",
    "inert", "ismap", "itemscope", "loop", "multiple", "muted", "nomodule",
    "novalidate", "open", "playsinline", "readonly", "required", "reversed",
    "selected", "shadowrootclonable", "shadowrootcustomelementregistry",
    "shadowrootdelegatesfocus", "shadowrootserializable",
}  # fmt: skip

NOT_BOOL = ["unchecked", "false", "true", "checked", "", "0", 0, 1, 1.0, [], {}]


def _html(node):
    return node.__render__(pretty=False)


def test_governed_set_is_the_spec_list():
    assert BOOLEAN_ATTRIBUTES == SPEC


@pytest.mark.parametrize("name", sorted(SPEC))
def test_true_renders_the_attribute(name):
    assert _html(div(**{name: True})) == f'<div {name}="{name}"></div>'


@pytest.mark.parametrize("value", [False, None])
@pytest.mark.parametrize("name", sorted(SPEC))
def test_false_and_none_omit_it(name, value):
    assert _html(div(**{name: value})) == "<div></div>"


@pytest.mark.parametrize("value", NOT_BOOL, ids=repr)
def test_any_other_value_raises(value):
    with pytest.raises(TypeError, match="'checked'.*True, False or None"):
        input_(type="checkbox", checked=value)


def test_every_write_path_is_governed():
    tag = input_()
    tag["disabled"] = True
    assert _html(tag) == '<input disabled="disabled">'
    tag["disabled"] = None
    assert _html(tag) == "<input>"
    with pytest.raises(TypeError):
        tag["disabled"] = "no"
    with pytest.raises(TypeError):
        input_({"readonly": "readonly"})
    with pytest.raises(TypeError), input_():
        attr(required="yes")
    with pytest.raises(TypeError):
        input_(Checked="false")  # attribute names are case-insensitive


def test_parsed_boolean_attribute_is_present():
    # A browser treats any value as present, so the parser keeps True.
    (tag,) = defHTML('<input type="checkbox" checked="false" disabled>')
    assert tag.attributes == {"type": "checkbox", "checked": True, "disabled": True}
    assert _html(tag) == '<input checked="checked" disabled="disabled" type="checkbox">'


def test_look_alike_attributes_keep_their_values():
    node = div(
        hx_boost="false",
        draggable="false",
        contenteditable="false",
        spellcheck="false",
        hidden="until-found",
        x_cloak=True,
    )
    assert _html(node) == (
        '<div contenteditable="false" draggable="false" hidden="until-found" '
        'hx-boost="false" spellcheck="false" x-cloak="x-cloak"></div>'
    )


def test_svg_attributes_are_not_governed():
    assert _html(svg(open="x")) == '<svg open="x"></svg>'


class TestBooleanElements:
    """The #44 ux-valio elements follow the same contract."""

    @pytest.mark.parametrize("cls", [BooleanInput, CheckboxInput, RadioInput])
    def test_checked_renders_and_unset_omits(self, cls):
        assert 'checked="checked"' in _html(cls(name="n", checked=True))
        for value in (False, None):
            assert "checked" not in _html(cls(name="n", checked=value))
        assert "checked" not in _html(cls(name="n"))

    @pytest.mark.parametrize("cls", [BooleanInput, CheckboxInput, RadioInput])
    @pytest.mark.parametrize("value", ["unchecked", "checked", "null", "false", 1])
    def test_string_checked_raises(self, cls, value):
        with pytest.raises(TypeError):
            cls(name="n", checked=value)

    def test_field(self):
        html = _html(BooleanField(label="Terms", name="t", type="radio", checked=None))
        assert "checked" not in html
        with pytest.raises(TypeError):
            BooleanField(label="Terms", name="t", type="radio", checked="null")
