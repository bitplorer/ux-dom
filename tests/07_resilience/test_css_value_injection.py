"""A CSS value stays one value, and every CSS URL gets the URL check (#136).

``btn(color="red} body{background:yellow")`` added a ``body`` rule, and
``color="red;background:url(//cdn.example/x.png)"`` added a declaration that
skipped the URL check, which ran only on a property named ``background``. A
rule value, a ``Keyframes`` step value and a property name now raise
``InvalidCSSValue`` when they could end the declaration or rule, and each
``url()`` / ``src()`` / ``image()`` / ``image-set()`` URL in any property (and
in a ``style`` attribute) must pass the allowlist. Browser oracle:
``tests/06_browser/test_css_value_injection_browser.py``.
"""

from __future__ import annotations

import pytest

from ux_dom.dom import div, style
from ux_dom.dom.src.csstags import CSSClass, Keyframes
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, InvalidCSSValue


class btn(CSSClass):
    pass


class fade(Keyframes):
    pass


# Each one ends the value early, or would let the next character do so.
BREAKOUTS = {
    "close rule": "red} body{background:yellow",
    "open block": "red{",
    "extra declaration": "red;background:url(//cdn.example/x.png)",
    "unclosed paren": "rgb(0,0,0",
    "stray paren": "red)",
    "unclosed bracket": "[a 1fr",
    "mismatched bracket": "[a)",
    "comment": "red /* x */",
    "unclosed string": '"red',
    "newline in string": '"a\n} b{c:d"',
    "newline": "red\nblue",
    "escaped url function": "\\75rl(//cdn.example/x.png)",
    "escape outside string": "r\\65 d",
    "bad url token": "url(a b)",
    "quote in url token": "url(a')",
}
CONTEXTS = {
    "<style> rule": lambda v: style(btn(color=v)).__render__(pretty=False),
    "pretty": lambda v: style(btn(color=v)).__render__(),
    "attr": lambda v: btn(color=v).attr,
    "keyframes step": lambda v: style(fade(to={"color": v})).__render__(pretty=False),
}


@pytest.mark.parametrize("context", CONTEXTS)
@pytest.mark.parametrize("value", BREAKOUTS.values(), ids=list(BREAKOUTS))
def test_value_that_ends_its_declaration_raises(context, value):
    with pytest.raises(InvalidCSSValue, match="color"):
        CONTEXTS[context](value)


@pytest.mark.parametrize("name", ["color:red}body{x", "a;b", "a{"])
def test_property_name_that_ends_its_declaration_raises(name):
    with pytest.raises(InvalidCSSValue):
        style(btn(**{name: "y"})).__render__(pretty=False)


UNSAFE = [
    "url(//cdn.example/x.png)",
    "url(javascript:alert)",
    'url("javascript:alert")',
    "url('jav\\61script:alert')",
    "URL( //cdn.example/x.png )",
    "url(data:image/svg+xml,x), auto",
    'image-set("//cdn.example/x.png" 1x)',
    '-webkit-image-set("//cdn.example/x.png" 1x)',
    'image("//cdn.example/x.png")',
    'src("//cdn.example/x.woff2")',
    "linear-gradient(red, blue), url(//cdn.example/x.png)",
]


@pytest.mark.parametrize(
    "prop", ["background", "cursor", "list_style", "mask", "--icon"]
)
@pytest.mark.parametrize("value", UNSAFE)
def test_unsafe_css_url_in_any_property_is_inert(prop, value):
    out = style(btn(**{prop: value})).__render__(pretty=False)
    assert out == "<style>.btn{%s:%s;}</style>" % (prop.replace("_", "-"), UNSAFE_URL)


LEGIT = {
    "color": "red",
    "--brand-color": "#f00",
    "width": "calc(100% - var(--gap, 2px))",
    "font-family": "'Courier New', \"Segoe UI\", mono",
    "content": '"a;b} /* \\201C"',
    "background": 'url("https://cdn.example/a.png"), linear-gradient(red 0%, blue)',
    "background-image": "url(/img.png)",
    "cursor": "url(data:image/png;base64,AAAA) 4 4, auto",
    "mask-image": 'image-set("a.png" 1x, "b.avif" type("image/avif") 2x)',
    "grid-template-columns": "[full-start] minmax(0, 1fr) [full-end]",
    "grid-template-areas": '"a b" "c d"',
    "margin": 0,
    "z-index": "1 !important",
    "url-like": "myurl(javascript:x)",
}


def test_legitimate_values_render_unchanged():
    out = style(btn(**LEGIT)).__render__(pretty=False)
    body = "".join("%s:%s;" % item for item in LEGIT.items())
    assert out == "<style>.btn{%s}</style>" % body


@pytest.mark.parametrize(
    "value",
    [
        "width:10%;background:url(//cdn.example/x.png)",
        "background-image: image-set('javascript:x' 1x)",
        "background:\\75rl(//cdn.example/x.png)",
        "color:red;/* x */background:url(//cdn.example/x.png)",
    ],
)
def test_style_attribute_with_unsafe_or_hidden_url_is_inert(value):
    assert (
        div(style=value).__render__(pretty=False) == f'<div style="{UNSAFE_URL}"></div>'
    )


def test_style_attribute_keeps_declaration_lists():
    value = "width: 10%;\n  background: url('/a.png'), linear-gradient(red, blue);"
    out = div(style=value).__render__(pretty=False)
    assert out == '<div style="%s"></div>' % value.replace("'", "&#39;")
