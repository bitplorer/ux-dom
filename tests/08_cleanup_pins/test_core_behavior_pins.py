"""Pins for core behaviour that the 2026-10 deep cleanup must keep.

Written before the cleanup started (against 19af869). Each test names a
feature callers rely on; a failure here means a refactor changed behaviour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ux_dom import Component, Document, Fragment, Htmx
from ux_dom.dom import a, button, div, img, li, raw, span, ul
from ux_dom.dom.htmlelement import HTMLElement, JinjaElement
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, escape, safe_attr_value


def html(node) -> str:
    return node.__render__(pretty=False)


# ── text and attribute escaping ──────────────────────────────────────────


def test_tag_text_is_escaped():
    assert html(div("<b>x</b> & y")) == "<div>&lt;b&gt;x&lt;/b&gt; &amp; y</div>"


def test_attribute_values_are_escaped():
    out = html(span(title="a\"b'c<d>"))
    assert out == '<span title="a&quot;b&#39;c&lt;d&gt;"></span>'


def test_escape_function_contract():
    assert escape("<&>\"'") == "&lt;&amp;&gt;&quot;&#39;"
    assert escape("<&>\"'", quote=False) == "&lt;&amp;&gt;\"'"


def test_bare_and_false_attributes():
    assert html(button(disabled=None, hidden=False)) == "<button disabled></button>"


def test_alpine_and_htmx_attributes_render_from_code():
    out = html(
        div(x_data="{open: false}", hx_post="/save", **{"@click": "open = !open"})
    )
    assert 'x-data="{open: false}"' in out
    assert 'hx-post="/save"' in out
    assert '@click="open = !open"' in out


# ── URL allow-list keeps legitimate URLs ─────────────────────────────────


def test_safe_urls_pass():
    for url in (
        "/a/b?q=1#f",
        "rel/path",
        "?q",
        "#frag",
        "https://example.com/x",
        "http://example.com",
        "mailto:a@b.c",
        "tel:+123",
        "data:image/png;base64,AAAA",
    ):
        assert safe_attr_value("href", url) == url, url


def test_unsafe_url_is_replaced():
    assert safe_attr_value("href", "javascript:alert(1)") == UNSAFE_URL
    assert html(a("x", href="javascript:alert(1)")) == f'<a href="{UNSAFE_URL}">x</a>'


def test_non_url_attribute_untouched():
    assert safe_attr_value("title", "javascript:alert(1)") == "javascript:alert(1)"


def test_img_src_relative():
    assert html(img(src="/i.png", alt="i")) == '<img alt="i" src="/i.png">'


# ── Components, Fragments, trusted markup ────────────────────────────────


def test_component_returning_tree():
    @dataclass(eq=False)
    class Card(Component):
        title: str = ""

        def render(self, title):
            return div(span(title), className="card")

    assert html(Card(title="Hi")) == '<div class="card"><span>Hi</span></div>'


def test_fragment_fans_shared_attrs_and_unique_id_once():
    frag = Fragment(span("A"), span("B"), className="row", id="first")
    out = html(frag)
    assert out.count('class="row"') == 2
    assert out.count('id="first"') == 1


def test_fragment_of_tags_renders_children_only():
    assert html(Fragment(span("A"), span("B"))) == "<span>A</span><span>B</span>"


def test_raw_is_trusted_markup():
    assert html(div(raw("<b>ok</b>"))) == "<div><b>ok</b></div>"


def test_html_element_parses_trusted_markup():
    class Box(HTMLElement):
        def render(self):
            return '<section class="s"><b>bold</b><x-foo a="1"></x-foo></section>'

    assert (
        html(Box()) == '<section class="s"><b>bold</b><x-foo a="1"></x-foo></section>'
    )


def test_jinja_element_keeps_template_syntax():
    class J(JinjaElement):
        def render(self):
            return "<ul>{% for x in xs %}<li>{{ x }}</li>{% endfor %}</ul>"

    assert html(J()) == "<ul>{% for x in xs %}<li>{{ x }}</li>{% endfor %}</ul>"


def test_defhtml_trusted_round_trip():
    src = '<div id="a" x-data="{n: 1}"><button @click="n++">+</button></div>'
    nodes = defHTML(src, escape=False)
    assert "".join(html(n) for n in nodes) == src


def test_nested_list_build_with_context_managers():
    with ul() as root:
        for i in range(2):
            li(str(i))
    assert html(root) == "<ul><li>0</li><li>1</li></ul>"


# ── Document shell with runtimes ─────────────────────────────────────────


def test_document_with_htmx_emits_htmx_and_idiomorph_scripts():
    page = Document(head=[], body=[]).use(Htmx())(body=[div("hi")])
    out = page.__render__(pretty=False)
    assert out.startswith("<!DOCTYPE html>")
    assert "<div>hi</div>" in out
    assert re.search(r'<script[^>]+src="https://[^"]*htmx\.org@[^"]+"', out)
    assert re.search(r'<script[^>]+src="https://[^"]*idiomorph[^"]*"', out)


def test_document_use_is_idempotent_by_name():
    doc = Document(head=[], body=[]).use(Htmx(), Htmx())
    assert len(doc.runtimes()) == 1
