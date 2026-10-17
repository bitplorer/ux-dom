"""Landing page: what each page demonstrates."""

from __future__ import annotations

from ux_dom.dom import a, code, h1, li, p, ul

from ..components import Shell
from ..document import page

TOUR = (
    ("/shop", "Shop", "CMS HTML through the defHTML sanitizer."),
    ("/cart", "Cart", "htmx POST that swaps a server-rendered partial."),
    ("/guestbook", "Guestbook", "User input as text, Markdown and checked URLs."),
    ("/sse", "Live", "Server-sent events through the htmx SSE extension."),
    ("/stream", "Stream", "A long page streamed with StreamingRoute."),
)


def get():
    return page(
        Shell(
            h1("UxDom Showcase"),
            p(
                "Every page is a ux-dom tree in one shared ",
                code("Document"),
                ". Routes are a plain FastAPI table in ",
                code("main.py"),
                ".",
            ),
            ul(*[li(a(name, href=href), ": ", text) for href, name, text in TOUR]),
            active="/",
        )
    )
