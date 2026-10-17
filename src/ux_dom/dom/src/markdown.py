"""Markdown to HTML for Components (``string_is_markdown`` / ``.md`` files)."""

from __future__ import annotations

import html
from collections.abc import Callable

import marko
from marko.html_renderer import HTMLRenderer

__all__ = ["render_markdown"]


class _EscapingRenderer(HTMLRenderer):
    """Render raw HTML found in Markdown as visible text, never as markup."""

    def render_html_block(self, element) -> str:
        return html.escape(element.body)

    def render_inline_html(self, element) -> str:
        return html.escape(str(element.children))


_trusted = marko.Markdown()
_untrusted = marko.Markdown(renderer=_EscapingRenderer)


def render_markdown(
    text: str, *, trusted: bool = False, convert: Callable | None = None
) -> str:
    """Convert Markdown to HTML.

    ``trusted=False`` (default) escapes raw HTML in the source. The caller
    still sanitizes the result (``defHTML``). ``convert`` replaces the
    converter (a callable or an object with ``.convert``).
    """
    if convert is not None:
        return getattr(convert, "convert", convert)(text)
    return (_trusted if trusted else _untrusted).convert(text)
