"""F-23: markdown= string reaches render; callable still overrides converter."""

from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div


def test_markdown_string_kwarg_reaches_render():
    class Post(Component):
        def render(self, title, markdown="(none)"):
            return div(title, " / ", markdown)

    html = str(Post("T", markdown="**body**"))
    assert "**body**" in html or "body" in html
    assert "(none)" not in html


def test_callable_markdown_still_overrides_converter():
    class MD(Component):
        string_is_markdown = True

        def render(self):
            return "# Title"

    html = MD(markdown=lambda x: "<p>FAKE</p>").__render__(pretty=False)
    assert "FAKE" in html
