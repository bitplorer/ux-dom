"""HTML document shell for route handlers."""
from __future__ import annotations

from ux_dom import Document
from ux_dom.dom import link, meta, title

from app import settings


def page(*body, page_title: str | None = None):
    """Wrap body content in a full HTML document."""
    head = [
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        title(page_title or settings.APP_TITLE),
    ]
    if settings.WITH_TAILWIND:
        # Compiled sheet under /css (compile with uxcompose build, not Document)
        head.append(
            link(href=f"/css/{settings.OUTPUT_CSS}", rel="stylesheet")
        )
    # include_runtimes=True pulls HTMX (and other App control plane) scripts
    # from the process hub set by App.build() — without this, hx-* attrs are inert.
    return Document(
        head=head,
        ensure_csrf_token=False,
        webassets=settings.webassets if settings.WITH_TAILWIND else None,
        include_runtimes=True,
    )(*body)
