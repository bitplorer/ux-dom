"""N3: the string sinks #32 left raw go through the same sanitizer.

A string child is text; HTML is added as ``*defHTML(s)`` (the
``escape_string`` switch that appended it verbatim is gone, see
``test_escape_param_absent.py``). ``to_fragment`` fell back to ``str(node)`` for anything else, so ``bytes``
rendered as ``b'<img onerror=…>'``. ``raw()`` / ``Markup`` stay the verbatim
opt-out (ADR 0002). The CDATA / PI / DOCTYPE rows guard the fix itself: a
version of it that wrote parsed text unescaped emitted a live ``<img>``.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from markupsafe import Markup

from ux_dom.dom import div, script
from ux_dom.dom.htmlelement import HTMLElement
from ux_dom.dom.src.html_string import defHTML
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


@pytest.mark.parametrize("payload", PAYLOADS)
def test_html_child_via_defhtml_sanitizes(payload):
    out = _render(div(*defHTML(payload)))
    assert _runnable(out) == [], out


@pytest.mark.parametrize("payload", PAYLOADS)
def test_html_element_list_strings_sanitize(payload):
    out = _render(HTMLElement([payload, payload.encode()]))
    assert _runnable(out) == [], out


def test_defhtml_child_keeps_safe_markup_and_entities():
    out = _render(div(*defHTML('<p class="note"><b>Tom &amp; Jerry</b></p>')))
    assert out == '<div><p class="note"><b>Tom &amp; Jerry</b></p></div>'


@pytest.mark.parametrize("child", [Markup(IMG), raw(IMG)])
def test_markup_and_raw_stay_verbatim(child):
    assert IMG in _render(HTMLElement([child, div()]))


def test_raw_text_element_untouched():
    """script/style children are raw text; no parse, render-time neutralize."""
    out = _render(script("if (a<b) go()"))
    assert "if (a<b) go()" in out


def test_str_child_is_escaped():
    assert _render(div(IMG)) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"


# ── bytes children ───────────────────────────────────────────────────────


def test_bytes_child_is_utf8_text():
    assert _render(div("café".encode())) == "<div>café</div>"
    assert _render(div(IMG.encode())) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"


def test_bytes_given_to_html_element_is_sanitized():
    assert _render(HTMLElement(IMG.encode())) == '<img src="x">'


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
    assert _render(div(lazy(lambda: b("x")))) == _render(div(b("x")))


def test_lazy_in_script_is_raw_text():
    from ux_dom.dom.src.utils import lazy

    assert "if (a<b) go()" in _render(script(lazy(lambda: "if (a<b) go()")))


# ── to_fragment: render protocol ─────────────────────────────────────────


def test_to_fragment_duck_typed_render():
    class Card:
        def __render__(self, *a, **kw):
            return "<b>ok</b>"

    assert to_fragment(Card()) == "<b>ok</b>"


# ── tag[i] = sequence / dom_string: each element takes the add() path ───


@pytest.mark.parametrize("wrap", [list, tuple])
def test_setitem_sequence_adds_each_element(wrap):
    node = div("a", "b")
    node[0] = wrap([IMG, raw("<i>r</i>")])
    out = _render(node)
    assert out == "<div>&lt;img src=x onerror=alert(1)&gt;<i>r</i>b</div>"
    assert _async_render(node) == out
    assert "&lt;img" in node.__render__()  # pretty mode renders too


def test_setitem_dom_string_is_escaped_like_add():
    from ux_dom.dom.src.dom_tag import dom_string

    node = div("a")
    node[0] = dom_string(IMG)
    assert _render(node) == "<div>&lt;img src=x onerror=alert(1)&gt;</div>"
    assert _render(div(dom_string(IMG))) == _render(node)


@pytest.mark.parametrize("value", [None, True, {"id": "x"}])
def test_setitem_rejects_non_children(value):
    node = div("a")
    with pytest.raises(TypeError):
        node[0] = value
    assert _render(node) == "<div>a</div>"


# ── open_tag / close_tag: verbatim markup overrides need Markup ─────────


def _set_control(how, key, value):
    if how == "kwarg":
        return div("x", **{key: value})
    if how == "dict":
        return div({key: value}, "x")
    node = div("x")
    node[key] = value
    return node


@pytest.mark.parametrize("how", ["kwarg", "dict", "item"])
@pytest.mark.parametrize("key", ["open_tag", "close_tag"])
def test_plain_str_open_close_tag_is_rejected(how, key):
    node = _set_control(how, key, IMG)
    with pytest.raises(TypeError):
        node.__render__(pretty=False)
    with pytest.raises(TypeError):
        _async_render(node)


def test_markup_open_close_tag_verbatim():
    node = div("x", open_tag=Markup("<!--O-->"), close_tag=Markup("<!--C-->"))
    assert _render(node) == "<!--O-->x<!--C-->"
    assert _render(node) == _async_render(node)


def test_jinja_templates_still_render():
    from ux_dom.dom import For, If, Var

    out = _render(div(For("x in xs", If("x", Var("x")))))
    assert "{% for x in xs %}" in out and "{% endfor %}" in out
    assert "{% if x %}" in out and "{{ x }}" in out


# ── tag names: validated where they are emitted ─────────────────────────

BAD_NAMES = [
    "img src=x onerror=alert(1)",
    "img/onerror=alert(1)",
    "b><img src=x onerror=alert(1)",
    "1div",
    "-x",
    "",
    "di\tv",
    'a"b',
]


def _named(how, name):
    if how == "kwarg":
        return div("x", tagname=name)
    if how == "dict":
        return div({"tagname": name}, "x")
    if how == "item":
        node = div("x")
        node["tagname"] = name
        return node
    if how == "instance":
        node = div("x")
        node.tagname = name
        return node
    return type("T", (div,), {"tagname": name})("x")


@pytest.mark.parametrize("how", ["instance", "class"])
@pytest.mark.parametrize("name", BAD_NAMES)
def test_bad_tag_name_raises(how, name):
    node = _named(how, name)
    with pytest.raises(ValueError):
        node.__render__(pretty=False)
    with pytest.raises(ValueError):
        node.__render__()
    with pytest.raises(ValueError):
        _async_render(node)


@pytest.mark.parametrize("name", BAD_NAMES)
def test_bad_dynamic_element_name_raises(name):
    from ux_dom.dom.src.html_string import create_dynamic_element

    with pytest.raises(ValueError):
        create_dynamic_element(name)


GOOD_NAMES = [
    "section",
    "linearGradient",
    "feGaussianBlur",
    "x-counter",
    "amp-img",
    "my.el-x",
    "svg:rect",
]


@pytest.mark.parametrize("name", GOOD_NAMES)
def test_good_tag_names_render(name):
    assert _render(_named("instance", name)) == f"<{name}>x</{name}>"


def test_builtin_and_css_tags_still_render():
    from ux_dom.dom import For, Var

    assert _render(div(For("x in xs", Var("x")))).startswith("<div>{% for")
    assert _render(type("MyCard", (div,), {})("x")) == "<MyCard>x</MyCard>"


# ── custom element names: the spec's PCENChar grammar ───────────────────


@pytest.mark.parametrize("name", ["x-ñ", "math-α", "my-el.v2_x", "font-face"])
def test_custom_element_names_with_pcen_chars_render(name):
    assert _render(_named("class", name)) == f"<{name}>x</{name}>"


@pytest.mark.parametrize(
    "name", ["X-Upper", "x-a b", "x-<", "x-a/b", 'x-a"b', "-x", "x-a:b"]
)
def test_bad_custom_element_names_raise(name):
    with pytest.raises(ValueError):
        _render(_named("class", name))


def test_builtin_names_still_valid():
    import inspect

    from ux_dom.dom.src import htmltags, svgtags
    from ux_dom.dom.src.dom_tag import dom_tag
    from ux_dom.dom.src.utils.dom_util import checked_tag_name

    for module in (htmltags, svgtags):
        for obj in vars(module).values():
            if inspect.isclass(obj) and issubclass(obj, dom_tag):
                name = (getattr(obj, "tagname", None) or obj.__name__).strip("_")
                if name:
                    checked_tag_name(name)


# ── comment() / DocType(): spec grammar, ValueError otherwise ───────────

BAD_COMMENTS = [
    "--><img src=x onerror=alert(1)>",
    "a --!><img src=x onerror=alert(1)>",
    ">x",
    "->x",
    "a <!-- b",
    "ends <!-",
]


@pytest.mark.parametrize("text", BAD_COMMENTS)
def test_bad_comment_text_raises(text):
    from ux_dom.dom import comment

    with pytest.raises(ValueError):
        comment(text)


@pytest.mark.parametrize(
    "text", ["note", "a - b", "a -> b", "x- ->y", "[if IE]>x<![endif]"]
)
def test_good_comment_text_renders(text):
    from ux_dom.dom import comment

    assert _render(comment(text)) == f"<!-- {text} -->"


BAD_DOCTYPES = [
    "html><img src=x onerror=alert(1)>",
    'html PUBLIC "a"><img src=x onerror=alert(1)>',
    "html SYSTEM 'x'><img src=x onerror=alert(1)>",
    'html SYSTEM "a" "b"',
    "",
    "h tml",
]


@pytest.mark.parametrize("text", BAD_DOCTYPES)
def test_bad_doctype_raises(text):
    from ux_dom.dom.src.htmltags import DocType

    with pytest.raises(ValueError):
        DocType(text)


@pytest.mark.parametrize(
    "text",
    [
        "html",
        'html SYSTEM "about:legacy-compat"',
        'html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"',
        "html public '-//W3C//DTD HTML 4.01//EN'",
    ],
)
def test_good_doctype_renders(text):
    from ux_dom.dom.src.htmltags import DocType

    assert _render(DocType(text)) == f"<!DOCTYPE {text}>"


def test_document_mode_drops_bad_doctype():
    from ux_dom.dom.src.html_string import _sanitized_html

    out = _sanitized_html('<!DOCTYPE html "x"><p>a</p>', document=True)
    assert _runnable(out) == [] and "<p>a</p>" in out
    good = _sanitized_html("<!DOCTYPE html><p>a</p>", document=True)
    assert good.startswith("<!DOCTYPE html>")


# ── tagname is never read from the attribute dict ───────────────────────


@pytest.mark.parametrize("how", ["kwarg", "dict", "item"])
@pytest.mark.parametrize("name", BAD_NAMES + ["section"])
def test_tagname_attribute_does_not_rename(how, name):
    """kwarg / dict / tag["tagname"] are an HTML attribute, never the name."""
    node = _named(how, name)
    for out in (_render(node), node.__render__(), _async_render(node)):
        assert out.lstrip().startswith("<div"), out
        assert _runnable(out) == [], out


def test_css_tagname_attribute_does_not_rename():
    from ux_dom.dom import style
    from ux_dom.dom.src.csstags import CSSClass

    class btn(CSSClass):
        pass

    payload = "</style><img src=x onerror=alert(1)>"
    out = _render(style(btn(color="red", tagname=payload)))
    assert out.startswith("<style>.btn{"), out
    # A CSS value is raw text (#127); ``style`` neutralizes ``</style``.
    assert out.lower().count("</style") == 1 and out.endswith("</style>"), out
    assert _runnable(out) == [], out


def test_plugins_read_the_real_tag_name():
    from ux_dom.dom import script
    from ux_dom.plugins.csp import _tag_name
    from ux_dom.plugins.dedupe import _resource

    assert _tag_name(div(tagname="script")) == "div"
    assert _tag_name(script("x")) == "script"
    assert _resource(div(tagname="script", src="/a.js")) is None
