"""Pin the public ``ux_dom.dom`` seam: ``Component``, ``dom_tag``, ``escape``, ``raw``.

These names were already importable from ``ux_dom.dom`` (via star imports)
before F-15; this test pins them so sibling packages (ux-compose, ux-channel,
ux-motion) can import them here instead of from ``ux_dom.dom.src.*``.
See docs/reference/API_SURFACE.md.
"""

from __future__ import annotations

import ux_dom.dom
from ux_dom.dom.src.component import Component
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.utils.dom_util import escape, raw

SEAM = {"Component": Component, "dom_tag": dom_tag, "escape": escape, "raw": raw}


def test_seam_names_are_the_src_definitions():
    for name, obj in SEAM.items():
        assert getattr(ux_dom.dom, name, None) is obj, name


def test_seam_names_behave():
    from ux_dom.dom import escape, raw

    assert escape("<") == "&lt;"
    assert str(raw("<b>x</b>")) == "<b>x</b>"
