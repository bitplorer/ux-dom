"""ADR 0004 absence lock: no Python 2 residue and no private tag aliases in the DOM layer.

``basestring`` / ``unichr`` / ``__unicode__`` / ``__nonzero__`` compat shims are gone
(``str`` / ``chr`` / ``__str__`` / ``__bool__``). The htmltags ``_time`` / ``_del`` /
``_object`` / ``_map`` / ``_input`` second names and ``dom/src/main.py`` (an alias of
``ext``) are deleted.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

import ux_dom
from ux_dom.dom.src import dom_tag, htmltags

SRC = Path(ux_dom.__file__).parent
PY2_NAMES = re.compile(r"basestring|unichr|__unicode__|__nonzero__")


def test_no_py2_names_in_src():
    hits = [
        f"{path.relative_to(SRC)}:{n}"
        for path in SRC.rglob("*.py")
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if PY2_NAMES.search(line)
    ]
    assert hits == []


def test_dom_tag_uses_py3_dunders():
    assert "__nonzero__" not in vars(dom_tag.dom_tag)
    assert "__unicode__" not in vars(dom_tag.dom_tag)
    tag = htmltags.div("x")
    assert str(tag) == tag.__render__()
    assert bool(tag)


@pytest.mark.parametrize("name", ["_time", "_del", "_object", "_map", "_input"])
def test_private_tag_aliases_absent(name):
    assert not hasattr(htmltags, name)
    assert name not in htmltags.__all__
    assert hasattr(htmltags, name[1:] + "_")


def test_main_module_absent():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ux_dom.dom.src.main")
