"""F-15: public seam names live on ux_dom.dom (not only dom.src)."""

from __future__ import annotations


def test_public_seam_imports():
    from ux_dom.dom import Component, dom_tag, escape, raw

    assert Component is not None
    assert dom_tag is not None
    assert escape("<") == "&lt;"
    assert "x" in str(raw("<b>x</b>")) or raw("<b>x</b>") is not None


def test_public_seam_matches_src():
    from ux_dom.dom import Component, dom_tag, escape, raw
    from ux_dom.dom.src.component import Component as C2
    from ux_dom.dom.src.dom_tag import dom_tag as D2
    from ux_dom.dom.src.utils.dom_util import escape as E2, raw as R2

    assert Component is C2
    assert dom_tag is D2
    assert escape is E2
    assert raw is R2
