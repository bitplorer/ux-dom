# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Style pipeline plugins.

``NullStyle`` is the only style plugin. It does not compile CSS.
Product compile is ``uxcompose build`` (``ux_compose.tailwind``).
Document still links stylesheets; it does not run the compiler.
"""

from __future__ import annotations

from typing import Any


class NullStyle:
    plugin_kind = "style"
    name = "null"

    def stylesheet_href(self) -> str:
        return ""

    async def build(self, *, watch: bool = False) -> Any:
        return None

    async def stop(self) -> None:
        return None


__all__ = ["NullStyle"]
