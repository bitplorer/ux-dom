"""F-01, F-02: Jinja export never runs user text; string HTML gets no nonce."""

from __future__ import annotations

import html
import os
import random

import pytest

from ux_dom.dom import a, div, li, p, script
from ux_dom.dom.src.jinjatags import For, Var, render_jinja
from ux_dom.plugins.csp import reset_nonce, set_nonce, stamp_nonce, stamp_tree
from ux_dom.response.serialize import prepare_html_body, to_html_bytes

XSS = "<img src=x onerror=alert(1)>"


def test_jinja_context_values_are_autoescaped():
    out = str(For("n in names", li(Var("n")))(names=[XSS]))
    assert "<img" not in out
    assert "&lt;img" in out


@pytest.mark.parametrize(
    "payload",
    [
        "{{ 7*7 }}",
        "{{ cycler.__init__.__globals__.os.getcwd() }}",
        "{% for x in [1,2] %}LOOP{% endfor %}",
        "{# hidden #}visible",
    ],
)
def test_user_text_in_tree_is_not_template_code(payload):
    out = str(render_jinja(div(p(payload), a("x", title=payload))))
    assert "49" not in out
    assert os.getcwd() not in out
    assert "LOOPLOOP" not in out
    assert html.unescape(out).count(payload) == 2


def test_var_attribute_still_renders():
    out = str(render_jinja(a("go", href=Var("link")), link="/next"))
    assert 'href="/next"' in out


def test_string_template_is_sandboxed():
    from jinja2.exceptions import SecurityError

    with pytest.raises(SecurityError):
        render_jinja("{{ cycler.__init__.__globals__.os.getcwd() }}")


def test_string_body_is_never_nonce_stamped():
    tok = set_nonce("N0NCE")
    try:
        body = "<p>Hello <script>alert(document.cookie)</script></p>"
        assert "nonce" not in prepare_html_body(body)
        assert b"nonce" not in to_html_bytes(body)
        assert stamp_tree(body, "N0NCE") == body
        assert stamp_nonce([body]) == [body]
    finally:
        reset_nonce(tok)


def test_tree_scripts_still_get_the_nonce():
    tok = set_nonce("N0NCE")
    try:
        assert b'nonce="N0NCE"' in to_html_bytes(div(script(src="/a.js")))
    finally:
        reset_nonce(tok)


def test_for_loop_whitespace_is_unchanged():
    out = str(For("n in ns", li(Var("n")))(ns=[1, 2]))
    assert out == "  <li>\n    1\n  </li>\n  <li>\n    2\n  </li>\n"


@pytest.mark.parametrize("payload", ["{{ 7*7", "x {# y", "{% if", "a}b", "c{d"])
def test_unbalanced_braces_render_as_text(payload):
    from ux_dom.dom.src.utils import dom_text

    out = str(render_jinja(div(p(payload), a("x", title=payload), dom_text(payload))))
    assert html.unescape(out).count(payload) == 3
    assert "{" not in out and "}" not in out


def test_escaped_text_node_is_data_but_raw_is_template():
    from ux_dom.dom.src.utils import dom_text, raw

    out = str(render_jinja(div(dom_text("{{ 7*7 }}"), raw("{{ 6*7 }}"))))
    assert "49" not in out and "&#123;&#123; 7*7 &#125;&#125;" in out
    assert "42" in out


def test_export_does_not_change_the_tree():
    from ux_dom.dom.src.utils import dom_text

    tree = div(p("{{ a }}"), dom_text("{b}"), a("x", title="{c}"))
    before = tree.__render__()
    render_jinja(tree)
    assert tree.__render__() == before
    assert "{{ a }}" in before and "{b}" in before and 'title="{c}"' in before


_ALPHABET = "{}%#<>&\"' =/abcXYZ019\u00e9\u4e2d\U0001f600"


def _random_texts(n=500, seed=1337):
    # Property test with a fixed seed (no extra test dependency).
    rng = random.Random(seed)
    for _ in range(n):
        yield "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 30))).strip()


def test_property_any_text_round_trips_through_jinja_export():
    for t in _random_texts():
        out = str(render_jinja(div(p(t), a("x", title=t))))
        assert "{" not in out and "}" not in out, t
        if t:
            assert html.unescape(out).count(t) >= 2, t
