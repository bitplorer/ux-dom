from __future__ import annotations

from ux_dom.dom import body, head, html, link, meta, script, title as title_tag
from ux_dom.scripts import x_element_js


def page(*children, page_title: str = "UxDom UI"):
    return html(
        head(
            meta(charset="utf-8"),
            meta(name="viewport", content="width=device-width, initial-scale=1"),
            title_tag(page_title),
            # Tailwind CDN for gallery demos (production: use built CSS)
            script(src="https://cdn.tailwindcss.com"),
            script(src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js", defer=True),
            x_element_js(),  # Component embedding runtime
            # hide x-cloak
            # style via meta not needed
        ),
        body(
            *children,
            className="min-h-screen bg-slate-50 text-slate-900 antialiased",
        ),
    )
