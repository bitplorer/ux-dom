"""N3: the string sinks #32 left raw go through the same sanitizer.

``escape_string`` falsy (``__escape_string=False``, ``None``, ``0``, ``""``)
used to append a child string verbatim, so it rendered as live HTML.
``to_fragment`` fell back to ``str(node)`` for anything else, so ``bytes``
rendered as ``b'<img onerror=…>'``. ``raw()`` / ``Markup`` stay the verbatim
opt-out (ADR 0002). The CDATA / PI / DOCTYPE rows guard the fix itself: a
version of it that wrote parsed text unescaped emitted a live ``<img>``.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from markupsafe import Markup

from ux_dom.dom import div, script
from ux_dom.dom.src.utils import raw
from ux_dom.ui.channel_bridge import to_fragment

IMG = "<img src=x onerror=alert(1)>"
PAYLOADS = [
    IMG,
    "<script>alert(1)</script>",
    f"<![CDATA[{IMG}]]>",
    f"<?php {IMG} ?>",
    f"<!DOCTYPE {IMG}>",
    '<a href="javascript:alert(1)">g</a>',
]


def _render(node) -> str:
    return node.__render__(pretty=False)


def _runnable(out: str) -> list:
    """Start tags a browser would run: script, on*, javascript: URLs."""
    bad: list = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "script":
                bad.append(tag)
            for k, v in attrs:
                if k.startswith("on") or "javascript:" in (v or "").lower():
                    bad.append((tag, k))

    P().feed(out)
    return bad


def _unescaped(flag, child) -> str:
    node = div()
    node.escape_string = flag
    node.add(child)
    return _render(node)


@pytest.mark.parametrize("flag", [False, None, 0, ""])
@pytest.mark.parametrize("payload", PAYLOADS)
def test_falsy_escape_string_sanitizes(flag, payload):
    out = _unescaped(flag, payload)
    assert _runnable(out) == [], out


def test_kwarg_escape_string_false_sanitizes():
    out = _render(div(IMG, __escape_string=False))
    assert out == '<div><img src="x"></div>'


def test_escape_string_false_keeps_safe_markup_and_entities():
    out = _unescaped(False, '<p class="note"><b>Tom &amp; Jerry</b></p>')
    assert out == '<div><p class="note"><b>Tom &amp; Jerry</b></p></div>'


@pytest.mark.parametrize("child", [Markup(IMG), raw(IMG)])
def test_markup_and_raw_stay_verbatim(child):
    assert IMG in _unescaped(False, child)


def test_raw_text_element_untouched():
    """script/style children are raw text; no parse, render-time neutralize."""
    out = _render(script("if (a<b) go()", __escape_string=False))
    assert "if (a<b) go()" in out


def test_default_escape_string_still_escapes():
    assert _render(div(IMG)) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"


# ── bytes children ───────────────────────────────────────────────────────


def test_bytes_child_is_utf8_text():
    assert _render(div("café".encode())) == "<div>café</div>"
    assert _render(div(IMG.encode())) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"


def test_bytes_child_unescaped_is_sanitized():
    assert _unescaped(False, IMG.encode()) == '<div><img src="x"></div>'


def test_invalid_utf8_bytes_child_raises():
    with pytest.raises(UnicodeDecodeError):
        div(b"\xff")


@pytest.mark.parametrize("child", [bytearray(b"abc"), memoryview(b"abc")])
def test_bytearray_memoryview_child_raises(child):
    with pytest.raises(TypeError):
        div(child)


# ── to_fragment ──────────────────────────────────────────────────────────


def test_to_fragment_bytes_sanitized():
    assert to_fragment(IMG.encode()) == '<img src="x">'


def test_to_fragment_invalid_utf8_raises():
    with pytest.raises(UnicodeDecodeError):
        to_fragment(b"\xff")


class _Evil:
    def __str__(self):
        return IMG


@pytest.mark.parametrize("node", [5, object(), _Evil()])
def test_to_fragment_rejects_other_objects(node):
    with pytest.raises(TypeError):
        to_fragment(node)


def test_to_fragment_unchanged_cases():
    assert to_fragment(None) == ""
    assert to_fragment(Markup(IMG)) == IMG
    assert to_fragment(IMG) == '<img src="x">'
    assert to_fragment(div("hi")) == div("hi").__render__()
