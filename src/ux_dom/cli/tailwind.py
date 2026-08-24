"""Removed from the product path.

CSS *compiler* I/O (``discover_css_io`` / ``resolve_tailwind`` / ``argv_with_io``)
lives on ``ux_compose.tailwind``. This module exists so leftover imports fail
closed with a teaching error instead of a silent path helper that still looks
like ux-dom owns Tailwind.
"""

_MSG = (
    "ux_dom.cli.tailwind is not the CSS compiler. "
    "Use: uxcompose build  "
    "(ux_compose.tailwind.discover_css_io / resolve_tailwind). "
    "ux-dom keeps className, Document <link>, and package static "
    "/ux-dom/static/x_element.js."
)


def argv_with_io(*args, **kwargs):
    raise ImportError(_MSG)


def discover_css_io(*args, **kwargs):
    raise ImportError(_MSG)
