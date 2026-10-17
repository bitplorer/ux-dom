"""The HTML shell for the gallery.

``ux_dom.ui`` components are plain server HTML styled with Tailwind classes;
they need no client runtime. ``Htmx`` is added for the one interactive demo
(the toast button). The Tailwind play CDN keeps the example build-free; it
injects ``<style>`` tags at runtime, which a nonce CSP blocks, so this example
has no ``Csp``. Build the CSS (Tailwind CLI) and add ``Csp.auto()`` for
production; ``examples/showcase`` shows that setup.
"""

from __future__ import annotations

from ux_dom import Document
from ux_dom.dom import meta, script, title
from ux_dom.runtime import Htmx

document = Document(
    head=[
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        script(src="https://cdn.tailwindcss.com"),
    ],
).use(Htmx(version="2.0.4"))


def page(*content, page_title: str = "UI Kit · UxDom"):
    return document(*content, head=[title(page_title)])
