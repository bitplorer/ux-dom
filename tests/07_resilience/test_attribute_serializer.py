"""One attribute serializer for every renderer (review L1)."""
from __future__ import annotations

from ux_dom.dom import span
from ux_dom.dom.src.dom_tag import dom_tag


class bare(dom_tag):
    pass


ATTRS = {
    "hidden": None,
    "off": False,
    "title": "a\"b'c<d>",
    "href": "javascript:alert(1)",
    "class": "  a\n   b ",
    "data-x": {"k": "</script>"},
}


def _attrs(html: str) -> str:
    return html[html.index(" ") : html.index(">")]


def test_dom_tag_and_tags_serialize_attributes_identically():
    a = _attrs(bare(**ATTRS).__render__(pretty=False))
    b = _attrs(span(**ATTRS).__render__(pretty=False))
    assert a == b
    assert " hidden" in a and "off" not in a and "about:invalid" in a
    assert 'class="a b"' in a
