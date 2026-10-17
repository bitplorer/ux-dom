"""The HTML shell every showcase page shares.

The runtimes do the wiring: ``Htmx`` adds the pinned htmx scripts (with SRI)
and the middleware that sets ``request.state.htmx``; ``Csp.auto()`` adds a
nonce Content-Security-Policy (``Csp.dev()`` when ``DEBUG`` is on, else
``Csp.prod()``). ``main.py`` calls ``document.mount(app)`` once.
"""

from __future__ import annotations

from ux_dom import Document
from ux_dom.dom import link, meta, title
from ux_dom.runtime import Csp, Htmx

TITLE = "UxDom Showcase"

document = Document(
    head=[
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        link(rel="stylesheet", href="/static/app.css"),
    ],
).use(
    Htmx(version="2.0.4", sse=True, middleware=True),
    Csp.auto(),
)


def page(*content, page_title: str = TITLE):
    """A full HTML page: the shared shell plus this page's title and content."""
    return document(*content, head=[title(page_title)])
