"""#59 D4 absence lock: no ``escape=`` on string HTML, no ``escape_string``.

``defHTML`` / ``_sanitized_html`` / ``StringToHTML`` accepted ``escape`` and
ignored it: string HTML is always sanitized (ADR 0002). ``escape_string`` (and
its ``__escape_string=`` kwarg) switched a tag's string children from text to
HTML; only ``HTMLElement``, ``JinjaElement`` and ``MarkdownElement`` turned it
off. They now parse their strings themselves, so a string child of a tag is
text everywhere and HTML is added as ``*defHTML(s)`` (ADR 0004).
"""

from __future__ import annotations

import dataclasses

import pytest
from markupsafe import Markup

from ux_dom.dom import b, div, textarea
from ux_dom.dom.htmlelement import HTMLElement, JinjaElement, MarkdownElement
from ux_dom.dom.src.component import Component
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.html_string import StringToHTML, _sanitized_html, defHTML

IMG = "<img src=x onerror=alert(1)>"
TEXT = "<div>&lt;img src=x onerror=alert(1)&gt;</div>"


def _render(node) -> str:
    return node.__render__(pretty=False)


@pytest.mark.parametrize(
    "call",
    [
        lambda: defHTML("x", escape=False),
        lambda: defHTML("x", False),
        lambda: _sanitized_html("x", escape=True),
        lambda: StringToHTML("x", escape=False),
    ],
)
def test_escape_parameter_is_gone(call):
    with pytest.raises(TypeError):
        call()


def test_escape_string_is_gone():
    assert not hasattr(dom_tag, "escape_string")
    assert "escape_string" not in {f.name for f in dataclasses.fields(Component)}
    for cls in (HTMLElement, JinjaElement, MarkdownElement):
        assert "escape_string" not in vars(cls)


def test_escape_string_kwarg_no_longer_makes_html():
    # The kwarg is an ordinary attribute now (False renders nothing).
    assert _render(div(IMG, __escape_string=False)) == TEXT


def test_setting_escape_string_changes_nothing():
    node = div()
    node.escape_string = False
    node.add(IMG)
    assert _render(node) == TEXT


@pytest.mark.parametrize("E", [div, textarea])
def test_explicit_defhtml_is_the_html_child(E):
    out = _render(E(*defHTML(f"<b>t</b>{IMG}")))
    assert out == f'<{E.__name__}><b>t</b><img src="x"></{E.__name__}>'


@pytest.mark.parametrize("W", [HTMLElement, JinjaElement, MarkdownElement])
def test_html_wrappers_parse_their_strings(W):
    out = _render(W([f"<b>t</b>{IMG}", Markup("<i>m</i>"), b"<u>u</u>", div("d")]))
    assert out == '<b>t</b><img src="x"><i>m</i><u>u</u><div>d</div>'
    assert _render(W(x for x in ["<b>g</b>"])) == "<b>g</b>"
    assert _render(W(b"<b>y</b>")) == "<b>y</b>"


def test_html_wrapper_add_after_build_is_text():
    node = HTMLElement([b("x"), b("y")])
    node.add(IMG)
    node.add(*defHTML("<i>h</i>"))
    assert _render(node) == (
        "<b>x</b><b>y</b>&lt;img src=x onerror=alert(1)&gt;<i>h</i>"
    )


def test_markdown_code_keeps_its_markup_as_text():
    # Unescaping the converted Markdown before parsing used to drop this.
    out = _render(MarkdownElement("Document `<link>` and\n\n```\n<b>x</b>\n```"))
    assert "<code>&lt;link&gt;</code>" in out
    assert "&lt;b&gt;x&lt;/b&gt;" in out
