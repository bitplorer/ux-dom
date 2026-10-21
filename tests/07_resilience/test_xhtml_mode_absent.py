"""#87 (part 2) absence lock: there is no ``xhtml=True`` render mode.

``xhtml=True`` only wrote void elements as ``<br/>``. Served as XHTML
(``application/xhtml+xml``) its output was not XML: ``<style>`` / ``<script>``
bodies stayed raw, so ``a < b`` or ``&&`` broke the page and well-formed markup
in a body ran (``<script>1;<img src='x' onerror='…'/></script>``). Nested
``title`` / ``textarea`` (#91), bare attributes and ``--`` in comments were not
well-formed either, nothing wrote the XHTML namespace, and the foreign-content
model (#85, #98) is the HTML parser's, not XML's. No ux-* caller passed it, so
it is removed (ADR 0004), not fixed. Output is HTML only.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from ux_dom import Component, Document
from ux_dom.dom import br, div, style
from ux_dom.dom.src.dom_tag import dom_tag

RENDER_METHODS = (
    "__render__",
    "__async_render__",
    "_render",
    "_render_children",
    "_render_open_tag",
    "_render_attribute",
    "_walk_render_tokens",
    "_iter_pretty_stream",
    "_iter_pretty_stream_worker",
)


class Card(Component):
    def render(self):
        return div(style("a{}"), br())


def _subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _subclasses(sub)


@pytest.mark.parametrize(
    "build",
    [lambda: div(style("a < b"), br()), Card, lambda: Document()(Card())],
    ids=["element", "component", "document"],
)
def test_render_rejects_xhtml(build):
    with pytest.raises(TypeError):
        build().__render__(xhtml=True)

    async def stream():
        return [t async for t in build().__async_render__(xhtml=True)]

    with pytest.raises(TypeError):
        asyncio.run(stream())


def test_no_render_method_takes_xhtml():
    found = [
        f"{cls.__qualname__}.{name}"
        for cls in {dom_tag, *_subclasses(dom_tag)}
        for name in RENDER_METHODS
        if name in vars(cls)
        and "xhtml" in inspect.signature(vars(cls)[name]).parameters
    ]
    assert not found, found
