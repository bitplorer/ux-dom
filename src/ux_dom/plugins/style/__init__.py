# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Style pipeline plugins.

``NullStyle`` is the only working style plugin (no CSS compile).
``TailwindStyle`` is a fail-closed teaching stub — product compile is
``uxcompose build`` (``ux_compose.tailwind``). Document still links
stylesheets; it does not run the compiler.
"""

from __future__ import annotations

from typing import Any

from ux_dom.settings.commands import ProductCssMoved


class NullStyle:
    plugin_kind = "style"
    name = "null"

    def stylesheet_href(self) -> str:
        return ""

    async def build(self, *, watch: bool = False) -> Any:
        return None

    async def stop(self) -> None:
        return None


class TailwindStyle:
    """Fail-closed. Compile CSS with ``uxcompose build``, not Document lifespan."""

    plugin_kind = "style"
    name = "tailwind"

    def __init__(self, *args, **kwargs):
        raise ProductCssMoved()


__all__ = ["NullStyle", "ProductCssMoved", "TailwindStyle"]
