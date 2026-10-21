"""A comment ends where a browser ends it, in strings and streams (#124).

The expected tokens are what Chromium builds from each string; the live check
is ``tests/06_browser/test_comment_end_browser.py``.
"""

from __future__ import annotations

import ast
import html.parser
import itertools
from pathlib import Path

import pytest

from ux_dom.dom.src import parse_html
from ux_dom.dom.src.parse_html import Comment, tokenize_html
from ux_dom.response import sanitize_html, sanitize_html_stream

# (string, Chromium's top-level nodes as ("#comment" | "#text", data))
COMMENT_ENDS = [
    ("<!--a-->b", [("#comment", "a"), ("#text", "b")]),
    ("<!--a--!>b", [("#comment", "a"), ("#text", "b")]),
    ("<!--a--->b", [("#comment", "a-"), ("#text", "b")]),
    ("<!--a---!>b", [("#comment", "a-"), ("#text", "b")]),
    ("<!--a--!-->b", [("#comment", "a--!"), ("#text", "b")]),
    ("<!--a--!b-->c", [("#comment", "a--!b"), ("#text", "c")]),
    ("<!-->b", [("#comment", ""), ("#text", "b")]),
    ("<!--->b", [("#comment", ""), ("#text", "b")]),
    ("<!---->b", [("#comment", ""), ("#text", "b")]),
    ("<!----!>b", [("#comment", ""), ("#text", "b")]),
    ("<!-->x-->y", [("#comment", ""), ("#text", "x-->y")]),
    ("<!--->x-->y", [("#comment", ""), ("#text", "x-->y")]),
    # End of input inside a comment: a trailing ``-``, ``--`` or ``--!`` is
    # part of the unfinished end, not of the comment.
    ("<!--", [("#comment", "")]),
    ("<!---", [("#comment", "")]),
    ("<!--a", [("#comment", "a")]),
    ("<!--a-", [("#comment", "a")]),
    ("<!--a--", [("#comment", "a")]),
    ("<!--a--!", [("#comment", "a")]),
]


def _nodes(text: str) -> list[tuple[str, str]]:
    return [
        ("#comment" if isinstance(node, Comment) else "#text", node.data)
        for node in tokenize_html(text)
    ]


@pytest.mark.parametrize("text,expected", COMMENT_ENDS)
def test_comment_ends_where_chromium_ends_it(text, expected):
    assert _nodes(text) == expected


def test_markup_after_an_empty_comment_is_parsed_and_sanitized():
    assert sanitize_html("<!-->a<b>b</b>-->c") == "a<b>b</b>--&gt;c"
    assert sanitize_html("<!--><img src=x onerror=alert(1)>") == '<img src="x">'


def test_stream_cuts_right_after_an_empty_comment():
    pieces = list(sanitize_html_stream(["<!--> a ", "<i>b"]))
    assert pieces == [" a ", "<i>b</i>"]


@pytest.mark.parametrize("text", [t for t, _ in COMMENT_ENDS])
def test_stream_split_anywhere_equals_whole(text):
    """Every split into three chunks, so a chunk can end mid-comment-end."""
    text = f"<p>a</p> {text} <i>z</i>"
    whole = sanitize_html(text)
    for i, j in itertools.combinations_with_replacement(range(len(text) + 1), 2):
        chunks = [text[:i], text[i:j], text[j:]]
        assert "".join(sanitize_html_stream(chunks)) == whole, chunks


def test_parser_imports_only_public_stdlib_names():
    tree = ast.parse(Path(parse_html.__file__).read_text())
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "html.parser"
        for alias in node.names
    }
    assert imported <= set(html.parser.__all__), imported
