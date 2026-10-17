"""The HTML shell shared by every kit page.

* ``XElement()`` serves ``x_element.js`` from the installed package (one file,
  ``/ux-dom/static/x_element.js``) and adds its script tag; the Document
  emits each custom-element definition used on the page.
* ``Htmx(version="2.0.4")`` adds the pinned htmx script (with SRI).
* Alpine is pinned with SRI too. No ``Csp`` here: Alpine's standard build
  evaluates expressions with ``new Function`` and needs ``'unsafe-eval'``,
  which a strict CSP forbids. Use the showcase for the CSP pattern.
* The Tailwind play CDN styles the demo; it is a development tool and
  publishes no SRI hash. Build CSS for production.
"""

from __future__ import annotations

from ux_dom import Document
from ux_dom.dom import meta, script, title
from ux_dom.runtime import Htmx, XElement

TITLE = "UxDom XElement Kit"
ALPINE_URL = "https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"
ALPINE_SRI = "sha384-X9kJyAubVxnP0hcA+AMMs21U445qsnqhnUF8EBlEpP3a42Kh/JwWjlv2ZcvGfphb"

document = Document(
    head=[
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        script(src="https://cdn.tailwindcss.com"),
        script(
            src=ALPINE_URL,
            integrity=ALPINE_SRI,
            crossorigin="anonymous",
            defer=True,
        ),
    ],
).use(XElement(), Htmx(version="2.0.4"))


def page(*content, page_title: str = TITLE):
    """A full HTML page: the shared shell plus this page's title and content."""
    return document(*content, head=[title(page_title)])
