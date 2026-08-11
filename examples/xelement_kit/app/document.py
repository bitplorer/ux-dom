"""Document shell — plugin contributions inject XElement script URL."""
from __future__ import annotations

from ux_dom import Document
from ux_dom.dom import meta, script, title
from ux_dom.plugins import get_hub, shell_fragments

from app import settings


def page(*body, page_title: str | None = None):
    head = [
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        title(page_title or settings.APP_TITLE),
        script(src="https://cdn.tailwindcss.com"),
        script(src="https://unpkg.com/htmx.org@2.0.4"),
        script(
            defer=None,
            src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js",
        ),
    ]
    # XElementRuntime tags → /ux-dom/static/x_element.js (package, single copy)
    plugin_head, plugin_body = shell_fragments(get_hub())
    head.extend(plugin_head)
    return Document(head=head, ensure_csrf_token=False)(*body, *plugin_body)
