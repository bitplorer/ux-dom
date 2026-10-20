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


# ── tag[i] = value: same path as add() ───────────────────────────────────


def _async_render(node) -> str:
    import asyncio

    async def go():
        return "".join([t async for t in node.__async_render__(pretty=False)])

    return asyncio.run(go())


def test_setitem_str_is_escaped():
    node = div("a", "b")
    node[0] = IMG
    assert _render(node) == "<div>&lt;img src=x onerror=alert(1)&gt;b</div>"
    assert _async_render(node) == _render(node)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_setitem_unescaped_is_sanitized(payload):
    node = div("a", "b", __escape_string=False)
    node[-2] = payload
    out = _render(node)
    assert _runnable(out) == [], out
    assert out.endswith("b</div>")


def test_setitem_bytes_and_types():
    node = div("a")
    node[0] = IMG.encode()
    assert _render(node) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"
    with pytest.raises(TypeError):
        node[0] = bytearray(b"x")
    assert _render(node) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"
    with pytest.raises(IndexError):
        node[5] = "x"


def test_setitem_raw_and_script_unchanged():
    node = div("a")
    node[0] = raw(IMG)
    assert _render(node) == f"<div>{IMG}</div>"
    s = script("x")
    s[0] = "if (a<b) go()"
    assert "if (a<b) go()" in _render(s)


# ── lazy(): str results are text ─────────────────────────────────────────


def test_lazy_str_result_is_escaped():
    from ux_dom.dom.src.utils import lazy

    node = div(lazy(lambda: IMG))
    assert _render(node) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"
    assert _async_render(node) == _render(node)


def test_lazy_other_object_str_is_escaped():
    from ux_dom.dom.src.utils import lazy

    assert _render(div(lazy(_Evil))) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"
    assert _render(div(lazy(lambda: 5))) == "<div>5</div>"


def test_lazy_markup_raw_tag_unchanged():
    from ux_dom.dom import b
    from ux_dom.dom.src.utils import lazy

    assert _render(div(lazy(lambda: Markup(IMG)))) == f"<div>{IMG}</div>"
    assert _render(div(lazy(lambda: raw(IMG)))) == f"<div>{IMG}</div>"
    assert _render(div(lazy(lambda: b("x")))) == f"<div>{b('x')}</div>"


def test_lazy_in_script_is_raw_text():
    from ux_dom.dom.src.utils import lazy

    assert "if (a<b) go()" in _render(script(lazy(lambda: "if (a<b) go()")))


# ── to_fragment: render protocol ─────────────────────────────────────────


def test_to_fragment_duck_typed_render():
    class Card:
        def __render__(self, *a, **kw):
            return "<b>ok</b>"

    assert to_fragment(Card()) == "<b>ok</b>"
