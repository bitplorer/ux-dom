"""F-23: ``markdown=`` is decided by ``render``'s signature, not the value's type.

* ``render`` declares ``markdown`` -> the value is passed through (callable or not).
* otherwise -> callable or ``.convert`` object is the converter; ``None`` keeps
  the default; anything else raises ``TypeError``.
"""

from __future__ import annotations

import pytest

from ux_dom import Component
from ux_dom.dom import div
from ux_dom.dom.htmlelement import MarkdownElement


class MD(Component):
    string_is_markdown = True

    def render(self):
        return "# Title"


class Post(Component):
    def render(self, title, markdown="(none)"):
        return div(title, " / ", markdown if isinstance(markdown, str) else markdown("x"))


class ConvertOnly:
    """python-markdown style: ``.convert`` but no ``__call__``."""

    def convert(self, text):
        return "<p>CONVOBJ</p>"


def html(c):
    return c.__render__(pretty=False)


def test_callable_converter():
    assert "FAKE" in html(MD(markdown=lambda s: "<p>FAKE</p>"))
    assert "<p>FAKE</p>" in html(MarkdownElement("# x", markdown=lambda s: "<p>FAKE</p>"))


def test_convert_only_object_is_converter():
    assert not callable(ConvertOnly())
    assert "<p>CONVOBJ</p>" in html(MD(markdown=ConvertOnly()))
    assert "<p>CONVOBJ</p>" in html(MarkdownElement("# x", markdown=ConvertOnly()))


def test_none_keeps_default_converter():
    assert "<h1>Title</h1>" in html(MD(markdown=None))
    assert "<h1>x</h1>" in html(MarkdownElement("# x", markdown=None))


def test_render_declaring_markdown_receives_string():
    out = html(Post("T", markdown="**body**"))
    assert "**body**" in out
    assert "(none)" not in out


def test_render_declaring_markdown_receives_callable():
    out = html(Post("T", markdown=str.upper))
    assert "T / X" in out
    assert "(none)" not in out


@pytest.mark.parametrize("value", ["**body**", 42])
def test_non_converter_to_render_without_param_raises(value):
    with pytest.raises(TypeError, match=r"MD\(markdown=\.\.\.\) expects a Markdown converter"):
        MD(markdown=value)
    with pytest.raises(TypeError, match=r"MarkdownElement\(markdown=\.\.\.\)"):
        MarkdownElement("# x", markdown=value)
