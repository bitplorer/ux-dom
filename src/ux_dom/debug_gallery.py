# Copyright (c) 2026 ux-dom
"""Optional dev gallery helpers for XElement definitions.

Mount in DEBUG apps::

    from ux_dom.debug_gallery import gallery_page
    # or call gallery_page([HelloLight("hello"), ...])
"""

from __future__ import annotations

from typing import Iterable

from ux_dom.dom import code, div, h1, h2, p, pre


def gallery_page(definitions: Iterable, *, title: str = "ux-dom XElement gallery"):
    """Render a simple HTML gallery: show definition markup + host tags.

    ``definitions`` are XElement *instances* (definition trees). Hosts are
    produced via ``definition()``.
    """
    defs = list(definitions)
    blocks = []
    for d in defs:
        name = getattr(d, "tag_name", d.__class__.__name__)
        host = d() if callable(d) else d
        blocks.append(
            div(
                h2(str(name), className="text-lg font-semibold mt-6"),
                p(code(d.__class__.__name__), className="text-xs text-slate-500"),
                div(d, className="hidden", **{"data-gallery-def": str(name)}),
                div(host, className="my-2", **{"data-gallery-host": str(name)}),
                pre(
                    str(d)[:800],
                    className="text-[10px] bg-slate-900 text-slate-100 p-2 rounded overflow-x-auto",
                ),
            )
        )
    return div(
        h1(title, className="text-2xl font-bold mb-2"),
        p(
            "Dev gallery — ensure x_element.js is loaded on this page.",
            className="text-sm text-slate-600 mb-4",
        ),
        *blocks,
        className="max-w-2xl mx-auto px-4 py-8",
        id="ux_dom-gallery",
    )
