"""Sanitize an HTML string, or a stream of HTML string chunks (#121).

Both use the one string sanitizer (``defHTML``, ADR 0002); there is no second
policy here. ``sanitize_html(s)`` is exactly the ``defHTML(s)`` nodes
rendered with ``pretty=False``: nothing is added, not even a newline.

A stream is buffered up to safe boundaries, not sanitized statefully. The
sanitizer decides on whole top-level nodes (an unknown tag is unwrapped, a
``template`` is dropped with its children, ``svg`` changes the rules for what
is inside), so the stream holds text until the tokenizer itself
(``HtmlCuts``) reports a point where every element is closed and no tag,
comment, raw text or reference is open. Each stretch between two such points
is sanitized as a whole string. Concatenated, the pieces are byte-identical
to ``sanitize_html`` of the whole text, wherever the chunks were split.

The text held between two boundaries is at most ``max_chars`` characters
(``MAX_BUFFER_CHARS`` by default). Past that the stream fails closed: it
raises :class:`HtmlStreamOverflow` and emits nothing of the held text.
"""

from __future__ import annotations

import typing as T

from ux_dom.dom.src.html_string import _sanitized_html
from ux_dom.dom.src.parse_html import HtmlCuts

__all__ = [
    "MAX_BUFFER_CHARS",
    "HtmlStreamOverflow",
    "sanitize_html",
    "sanitize_html_stream",
]

MAX_BUFFER_CHARS = 1 << 20

Chunks = T.Union[T.Iterable[str], T.AsyncIterable[str]]


class HtmlStreamOverflow(ValueError):
    """A stream held more than ``max_chars`` characters without a safe boundary."""


def sanitize_html(html: str) -> str:
    """Sanitized HTML for one string: ``defHTML`` rendered, nothing added.

    A ``__html__`` value (``Markup``) is trusted and returned verbatim, as on
    every string entry point (ADR 0002).
    """
    trusted = _trusted(html)
    if trusted is not None:
        return trusted
    if not isinstance(html, str):
        raise TypeError(f"sanitize_html takes a str, not {type(html).__name__}")
    return _sanitized_html(html)


def sanitize_html_stream(
    chunks: Chunks, *, max_chars: int = MAX_BUFFER_CHARS
) -> T.Union[T.Iterator[str], T.AsyncIterator[str]]:
    """Sanitize a sync or async iterable of ``str`` chunks.

    Returns the same kind of iterator it is given. Each yielded piece is
    sanitized HTML; joined, they equal ``sanitize_html("".join(chunks))``.
    A ``__html__`` chunk (``Markup``) is trusted: the text held before it is
    sanitized as a whole (any element still open there is closed), then the
    chunk is yielded verbatim. Raises :class:`HtmlStreamOverflow` when more
    than ``max_chars`` characters arrive without a safe boundary.
    """
    if isinstance(chunks, str):
        raise TypeError(
            "sanitize_html_stream takes chunks; use sanitize_html for a str"
        )
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if hasattr(chunks, "__aiter__"):
        return _async_stream(T.cast(T.AsyncIterable[str], chunks), max_chars)
    return _sync_stream(T.cast(T.Iterable[str], chunks), max_chars)


def _sync_stream(chunks: T.Iterable[str], max_chars: int) -> T.Iterator[str]:
    buffer = _Buffer(max_chars)
    for chunk in chunks:
        yield from buffer.push(chunk)
    yield from buffer.close()


async def _async_stream(
    chunks: T.AsyncIterable[str], max_chars: int
) -> T.AsyncIterator[str]:
    buffer = _Buffer(max_chars)
    async for chunk in chunks:
        for piece in buffer.push(chunk):
            yield piece
    for piece in buffer.close():
        yield piece


def _trusted(value: T.Any) -> T.Optional[str]:
    html_method = getattr(value, "__html__", None)
    return str(html_method()) if callable(html_method) else None


class _Buffer:
    """Text since the last safe boundary, and the cut finder that reads it.

    The finder is fed as soon as nothing is held. While the parser waits on
    an unfinished construct of ``held`` characters, it is fed again only once
    at least that many new characters have arrived, so re-reading the held
    construct costs at most as much as the new text: linear time overall.
    """

    def __init__(self, max_chars: int) -> None:
        self.max_chars = max_chars
        self._reset()

    def _reset(self) -> None:
        self.cuts = HtmlCuts()
        self.parts: list[str] = []
        self.size = 0  # characters in ``parts``
        self.start = 0  # stream offset of ``parts[0]``
        self.unfed: list[str] = []
        self.unfed_size = 0

    def push(self, chunk: str) -> T.Iterator[str]:
        trusted = _trusted(chunk)
        if trusted is not None:
            yield from self.close()
            if trusted:
                yield trusted
            return
        if not isinstance(chunk, str):
            raise TypeError(
                f"sanitize_html_stream chunks are str, not {type(chunk).__name__}"
            )
        if not chunk:
            return
        self.parts.append(chunk)
        self.size += len(chunk)
        self.unfed.append(chunk)
        self.unfed_size += len(chunk)
        if self.unfed_size >= self.cuts.held:
            self._feed()
        if self.size > self.max_chars and self.unfed:
            self._feed()  # the held text may still contain a boundary
        piece = self._take()
        if self.size > self.max_chars:
            raise HtmlStreamOverflow(
                f"{self.size} characters without a safe HTML boundary "
                f"(max_chars={self.max_chars}); the held text is not emitted"
            )
        if piece:
            yield piece

    def close(self) -> T.Iterator[str]:
        text = "".join(self.parts)
        self._reset()
        piece = _sanitized_html(text) if text else ""
        if piece:
            yield piece

    def _feed(self) -> None:
        self.cuts.feed("".join(self.unfed))
        self.unfed.clear()
        self.unfed_size = 0

    def _take(self) -> str:
        """Sanitize and drop the text before the last boundary."""
        end = self.cuts.cut - self.start
        if end <= 0:
            return ""
        text = "".join(self.parts)
        rest = text[end:]
        self.parts = [rest] if rest else []
        self.size = len(rest)
        self.start = self.cuts.cut
        return _sanitized_html(text[:end])
