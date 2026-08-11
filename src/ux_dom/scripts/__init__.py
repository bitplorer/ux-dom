# Copyright (c) 2023–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Browser runtime for Python ``XElement`` (0.1).

Contract
--------
| Side    | Name              | Role                                    |
|---------|-------------------|-----------------------------------------|
| Python  | ``XElement``      | Component that emits ``x-tagname`` defs |
| Attr    | ``x-tagname``     | Definition attribute on ``<template>``  |
| Host    | ``x-{name}``      | Custom element tag after upgrade        |
| JS file | ``x_element.js``  | Browser runtime (this package)          |
| Helper  | ``x_element_js``  | Component that embeds / saves the JS    |

::

    from ux_dom.scripts import x_element_js

    script(src=f"/assets/js/{x_element_js().save(file_or_dir=assets.js)}")
"""

from __future__ import annotations

from pathlib import Path

from ux_dom.dom import raw
from ux_dom.dom.src.component import Component

__all__ = [
    "x_element_js",
    "x_element_js_text",
]

_RUNTIME = "x_element.js"


def _runtime_source() -> str:
    path = Path(__file__).parent / _RUNTIME
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — XElement browser runtime required "
            f"(pairs with ux_dom.dom.XElement / x-tagname)"
        )
    return path.read_text(encoding="utf-8")


class x_element_js(Component):
    """Embed or save ``x_element.js`` — browser half of Python ``XElement``.

    Pairs with ``ux_dom.dom.XElement`` (attr ``x-tagname`` → host ``x-{{name}}``).
    """

    file_extension = ".js"

    def render(self, *args, **kwargs):
        return raw(_runtime_source())


def x_element_js_text() -> str:
    """Raw ``x_element.js`` source (scaffolding / static copy)."""
    return _runtime_source()
