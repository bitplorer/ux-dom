# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Fail-closed Tailwind *compiler* stub.

Product CSS compile is ``uxcompose build`` (``ux_compose.tailwind``).
This package keeps render-only CSS: ``className``, Document ``<link>``.
It does not find, download, scaffold ``@source``, or
invoke the Tailwind CLI. App folders are ``ux_compose.assets.WebAssets``.

``TailwindCommand`` remains importable so leftover callers fail closed
with a teaching error instead of silently compiling from Document.
"""

from __future__ import annotations

__all__ = ["ProductCssMoved", "TailwindCommand"]


_TEACH = (
    "Tailwind CLI is product DX, not a Document API. "
    "Use: uxcompose build   "
    "(ux_compose.tailwind finds / ensures / invokes the compiler; "
    "create-app writes assets/css/input.css @source). "
    "ux-dom keeps className, Document <link>, and package static "
    "/ux-dom/static/x_element.js."
)


class ProductCssMoved(RuntimeError):
    """Raised when a caller tries to run the Tailwind compiler from ux-dom."""

    def __init__(self, message: str = _TEACH):
        super().__init__(message)


class TailwindCommand:
    """Historical compiler wrapper. Construction fails closed."""

    def __init__(self, *args, **kwargs):
        raise ProductCssMoved()
