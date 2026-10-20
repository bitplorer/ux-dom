"""Locks for Alpine ``dataset_*`` helpers and Fragment/DataSet attribute merges."""

import pytest

from ux_dom.alpinejs import DataSet
from ux_dom.alpinejs import dataset as ds
from ux_dom.dom.src.component import Fragment
from ux_dom.dom.src.dom_tag import attr
from ux_dom.dom.src.htmltags import div

_HELPERS = [
    (name, getattr(ds, name)) for name in ds.__all__ if name.startswith("dataset_")
]


@pytest.mark.parametrize("name,helper", _HELPERS, ids=[n for n, _ in _HELPERS])
def test_each_dataset_helper_renders_inside_dataset(name, helper):
    with DataSet() as d:
        helper(True) if name == "dataset_checked" else helper()
        div("x")
    html = d.__render__(pretty=False)
    assert html.startswith("<div ") and "x-data=" in html


def test_two_datasets_merge():
    with DataSet() as d:
        ds.dataset_focused()
        ds.dataset_hovered()
        div("x")
    html = d.__render__(pretty=False)
    for key in ("focused", "hovered", ":data-focused", ":data-hovered"):
        assert key in html


def test_bind_attr_first_set_is_kept():
    with DataSet() as d:
        attr(**{":class": "{a: b}"})
        div("x")
    assert ':class="{a: b}"' in d.__render__(pretty=False)


@pytest.mark.parametrize("group", [Fragment, DataSet])
def test_bool_x_transition_merged_with_value_keeps_value(group):
    with group() as d:
        attr(x_transition=True)
        div("x", x_transition="opacity")
    assert d.__render__(pretty=False) == '<div x-transition="opacity">x</div>'


@pytest.mark.parametrize("group", [Fragment, DataSet])
def test_bool_x_transition_merged_with_bool_renders_bare(group):
    with group() as d:
        attr(x_transition=True)
        div("x", x_transition=True)
    assert d.__render__(pretty=False) == "<div x-transition>x</div>"


def test_dataset_bool_x_transition_after_value_keeps_value():
    with DataSet() as d:
        attr(x_transition="opacity")
        attr(x_transition=True)
        div("x")
    assert d.__render__(pretty=False) == '<div x-transition="opacity">x</div>'
