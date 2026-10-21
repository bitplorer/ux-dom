"""#114: no tag class shadows a Python builtin.

A tag whose element name is a builtin or a keyword is written with a trailing
``_`` (``input_``, ``object_``, ``map_``, ``del_``, ``set_``, ``filter_``) and still
writes its element name. ``from ux_dom.dom import *`` then leaves every builtin
free. The string parser resolves ``<input>`` to ``input_`` by the same rule.

One exception: ``time_``. ``time`` is not a builtin, but the trailing ``_`` keeps
the stdlib ``time`` module free under a star import.
"""

from __future__ import annotations

import builtins
import keyword

import pytest

import ux_dom.dom
from ux_dom.dom.src import ext, htmltags, svgtags

BUILTINS = set(dir(builtins))
EXCEPTIONS = {"time_"}


def _tag_classes():
    for module in (htmltags, svgtags):
        for name in module.__all__:
            cls = getattr(module, name)
            if isinstance(cls, type) and issubclass(cls, ext.Tags):
                yield name, cls


def test_star_import_shadows_no_builtin():
    public = {n for n in vars(ux_dom.dom) if not n.startswith("_")}
    assert public & BUILTINS == set()
    assert not hasattr(ux_dom.dom, "filter")


@pytest.mark.parametrize("name,cls", list(_tag_classes()))
def test_trailing_underscore_only_for_builtin_or_keyword(name, cls):
    element = name.rstrip("_")
    shadows = element in BUILTINS or keyword.iskeyword(element)
    assert name.endswith("_") == shadows or name in EXCEPTIONS
    if name.endswith("_"):
        assert cls().__render__(pretty=False).startswith(f"<{element}>")


def test_filter_writes_filter():
    node = ux_dom.dom.svg(ux_dom.dom.filter_(ux_dom.dom.feBlend(), id="f"))
    assert node.__render__(pretty=False) == '<svg><filter id="f"><feBlend></feBlend></filter></svg>'


def test_stdlib_module_names_keep_plain_names():
    # #119: only ``time`` gets the ``_``; ``html``, ``code`` and ``select`` stay plain.
    for name in ("html", "code", "select", "time_"):
        assert hasattr(ux_dom.dom, name)
    assert not hasattr(ux_dom.dom, "time")
