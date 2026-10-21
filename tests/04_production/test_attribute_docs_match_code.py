"""docs/security/ATTRIBUTES.md lists exactly the attribute sets the renderer uses (#86, #122)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ux_dom.dom.src.utils import dom_util

DOC = Path(__file__).resolve().parents[2] / "docs" / "security" / "ATTRIBUTES.md"
ROW = re.compile(r"^\| `(\w+)` \| (.+) \|$", re.MULTILINE)
ROWS = dict(ROW.findall(DOC.read_text(encoding="utf-8")))
SETS = [
    "URL_ATTRIBUTES",
    "_SRCSET_ATTRIBUTES",
    "_ANIMATION_TAGS",
    "_ANIMATION_VALUE_ATTRIBUTES",
    "_SAFE_SCHEMES",
    "_SAFE_DATA_IMAGE_TYPES",
    "SAME_ORIGIN_URL_ATTRIBUTES",
    "HTML_ATTRIBUTES",
    "BOOLEAN_ATTRIBUTES",
]


def test_every_documented_set_is_checked():
    assert sorted(ROWS) == sorted(SETS)


@pytest.mark.parametrize("name", SETS)
def test_documented_members_match_code(name):
    documented = re.findall(r"`([^`]+)`", ROWS[name])
    # The code lowercases tag names; the docs keep the SVG spelling.
    assert sorted(m.lower() for m in documented) == sorted(getattr(dom_util, name))
