"""Sanitized HTML strings and streams in ``ux_dom.response`` (#121).

``sanitize_html`` is ``defHTML`` rendered, with nothing added. A stream gives
the same bytes wherever its chunks are split: the attack corpora of the
sanitizer PRs, with 1-character chunks and random split points, and random
markup (Hypothesis). Chromium oracle:
``tests/06_browser/test_sanitized_stream_browser.py``.
"""

from __future__ import annotations

import asyncio
import random
import time
from html.parser import HTMLParser

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from markupsafe import Markup

from ux_dom.dom import defHTML
from ux_dom.response import (
    MAX_BUFFER_CHARS,
    HtmlStreamOverflow,
    sanitize_html,
    sanitize_html_stream,
)

from sanitizer_corpus import corpus

CORPUS = corpus()
SEEDS = range(1, 13)


def _defhtml(text: str) -> str:
    return "".join(node.__render__(pretty=False) for node in defHTML(text))


def _split(text: str, seed: int) -> list[str]:
    """Seed 0 is one character per chunk; others split at random points."""
    if seed == 0 or len(text) < 2:
        return list(text)
    rng = random.Random(seed)
    k = rng.randint(1, max(1, len(text) // 3))
    cuts = sorted(rng.sample(range(1, len(text)), min(len(text) - 1, k)))
    return [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)])]


def _stream(chunks, **kw) -> str:
    return "".join(sanitize_html_stream(iter(chunks), **kw))


def _astream(chunks, **kw) -> str:
    async def agen():
        for chunk in chunks:
            yield chunk

    async def run():
        return "".join([p async for p in sanitize_html_stream(agen(), **kw)])

    return asyncio.run(run())


def test_public_names():
    import ux_dom.response as response

    for name in ("sanitize_html", "sanitize_html_stream", "HtmlStreamOverflow"):
        assert name in response.__all__
    assert MAX_BUFFER_CHARS == 1 << 20


def test_corpora_are_loaded():
    prs = {pr for pr, _ in CORPUS}
    assert prs == {"#32", "#55", "#85", "#91", "#97", "#98", "#107", "#113"}
    assert len(CORPUS) > 1000


def test_whole_string_is_defhtml_rendered():
    for pr, text in CORPUS:
        assert sanitize_html(text) == _defhtml(text), (pr, text)


@pytest.mark.parametrize(
    "text, html",
    [
        ("<p>x</p>", "<p>x</p>"),
        ("x", "x"),
        ("<b>a</b>\n", "<b>a</b>\n"),
        ("", ""),
        ("<script>alert(1)</script>", ""),
        ("a\r\nb", "a\nb"),
    ],
)
def test_nothing_is_added(text, html):
    assert sanitize_html(text) == html
    assert _stream([text]) == html


@pytest.mark.parametrize("seed", [0, *SEEDS])
def test_chunked_corpora_equal_whole(seed):
    for pr, text in CORPUS:
        assert _stream(_split(text, seed)) == sanitize_html(text), (pr, seed, text)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_async_chunked_corpora_equal_whole(seed):
    for pr, text in CORPUS:
        assert _astream(_split(text, seed)) == sanitize_html(text), (pr, seed, text)


def test_whole_corpus_as_one_stream_equals_whole():
    text = "\n".join(t for _, t in CORPUS)
    whole = sanitize_html(text)
    for seed in (0, 1):
        assert _stream(_split(text, seed)) == whole


# Pieces that open and end every construct the tokenizer and its reference
# pass know, so random joins and splits land in all of them.
TOKENS = [
    "<!--",
    "-->",
    "--!>",
    "<!-->",
    "<!--->",
    "-",
    "!",
    "<a",
    "<p",
    "<b>",
    "</b>",
    " title=",
    " href=",
    '"',
    "'",
    ">",
    "</p>",
    "</a>",
    "<script>",
    "</script>",
    "<style>",
    "</style>",
    "<style/>",
    "<STYLE ",
    "<ſtyle>",
    "<![CDATA[",
    "]]>",
    "<!",
    "<?",
    "<!DOCTYPE",
    "<",
    "</",
    "/>",
    "x",
    " ",
    "\t",
    "\n",
    "\r",
    ";",
    "=",
    "&",
    "&amp;",
    "&#62",
    "&#x3c",
    "&#",
    "&notin;",
    "&not",
    "é",
    "<svg>",
    "</svg>",
    "<math>",
    "<textarea>",
    "</textarea",
    "<title>",
    "</title>",
    "<xmp>",
    "</xmp>",
    "<plaintext>",
    "<template>",
    "</template>",
    "<noscript>",
    "</noscript>",
    "<img",
    " onerror=alert(1)",
    "javascript:alert(1)",
    "<br>",
    "<li>",
]


@settings(max_examples=1500, deadline=None)
@given(
    st.lists(st.sampled_from(TOKENS), min_size=1, max_size=14),
    st.lists(st.integers(min_value=1, max_value=200), max_size=8),
)
def test_property_any_split_equals_whole(tokens, cuts):
    text = "".join(tokens)
    points = sorted({c for c in cuts if c < len(text)})
    chunks = [text[a:b] for a, b in zip([0, *points], [*points, len(text)])]
    whole = sanitize_html(text)
    assert _stream(chunks) == whole
    assert _stream(list(text)) == whole


def test_pieces_are_emitted_as_safe_boundaries_arrive():
    consumed = []

    def chunks():
        for i in range(200):
            consumed.append(i)
            yield f"<p>{i}</p>\n"

    for i, piece in enumerate(sanitize_html_stream(chunks())):
        assert piece == f"<p>{i}</p>\n"
        assert consumed[-1] == i  # nothing read ahead, nothing held back


def test_a_split_tag_waits_for_its_end():
    pieces = list(
        sanitize_html_stream(["<p>a</p> <img src=x on", "error=alert(1)", ">"])
    )
    assert pieces == ["<p>a</p> ", '<img src="x">']


def test_markup_chunk_is_verbatim_and_ends_the_fragment():
    trusted = Markup("<script>ok()</script>")
    pieces = list(sanitize_html_stream(["<b>x</b> <i>y", trusted, "</i><p>z</p>"]))
    assert pieces == ["<b>x</b> ", "<i>y</i>", str(trusted), "<p>z</p>"]
    assert sanitize_html(trusted) == str(trusted)


def test_overflow_fails_closed():
    out = []
    with pytest.raises(HtmlStreamOverflow):
        for piece in sanitize_html_stream(
            ["<p>ok</p>\n", "<p>" + "x" * 40, "y" * 40], max_chars=64
        ):
            out.append(piece)
    assert out == ["<p>ok</p>\n"]  # the held text is never emitted


@pytest.mark.parametrize(
    "held",
    [
        "<!-->" + "x" * 100,  # an empty comment only if no --> ever follows
        "<div>" + "<b>x</b> " * 20,
        "<a title='" + "x" * 100,
        "word" * 30,  # a cut must end any reference: no space, no cut
        "<style/>" + " x" * 50,
    ],
)
def test_no_boundary_within_max_chars_raises(held):
    with pytest.raises(HtmlStreamOverflow):
        _stream(list(held), max_chars=64)
    with pytest.raises(HtmlStreamOverflow):
        _astream([held], max_chars=64)


def test_boundaries_keep_a_long_stream_under_max_chars():
    text = "<p>a &amp; b</p>\n" * 5000
    assert _stream(_split(text, 3), max_chars=64) == sanitize_html(text)
    # One chunk far over max_chars is fine when it has boundaries.
    assert _stream([text], max_chars=64) == sanitize_html(text)


@pytest.mark.parametrize("bad", [b"<p>x</p>", None, 1])
def test_chunks_must_be_str(bad):
    with pytest.raises(TypeError):
        _stream(["<p>a</p>", bad])
    with pytest.raises(TypeError):
        sanitize_html(bad)


def test_a_str_is_not_a_stream():
    with pytest.raises(TypeError, match="sanitize_html"):
        sanitize_html_stream("<p>x</p>")
    with pytest.raises(ValueError):
        sanitize_html_stream([], max_chars=0)


# Linear time: the tokenizer re-reads a held construct only after as many new
# characters arrive, and each character is sanitized once.
SHAPES = {
    "elements": lambda n: "<p class=a>x &amp; <b>y</b></p>\n" * (n // 33),
    "open div": lambda n: "<div>" + "<p>x</p> " * (n // 9) + "</div>",
    "long comment": lambda n: "<!--" + "x" * n + "-->",
    "long attribute": lambda n: '<a title="' + "x" * n + '">q</a>',
    "unclosed <!-->": lambda n: "<!-->" + "x " * (n // 2),
    "<style/> regions": lambda n: "<style/>a " * (n // 10),
    "words": lambda n: "word " * (n // 5),
}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_parser_work_is_linear(shape, monkeypatch):
    work = []
    goahead = HTMLParser.goahead

    def counted(self, end):
        work.append(len(self.rawdata))
        return goahead(self, end)

    monkeypatch.setattr(HTMLParser, "goahead", counted)
    text = SHAPES[shape](40_000)
    assert _stream(list(text), max_chars=len(text)) == sanitize_html(text)
    assert sum(work) <= 4 * len(text), (shape, sum(work), len(text))


@pytest.mark.parametrize("shape", ["elements", "long comment", "unclosed <!-->"])
def test_time_grows_linearly(shape):
    def seconds(n):
        text = SHAPES[shape](n)
        start = time.perf_counter()
        _stream(list(text), max_chars=len(text))
        return time.perf_counter() - start

    small, large = seconds(10_000), seconds(40_000)
    assert large < 8 * small + 0.5, (shape, small, large)  # quadratic is 16x
