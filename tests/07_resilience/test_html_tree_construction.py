"""#125: the string parser builds the tree a browser builds, at any depth.

The parser implies end tags as the HTML spec's tree construction does
(§13.2.6: "in body", the table modes, breakout from foreign content), so
``<p>one<p>two<p>three`` is three paragraphs and ``<li>`` x 600 is a flat
list, not 600 levels. Like Chromium it attaches elements past 512 open ones
to the element at depth 511, so a parsed tree is never deeper than
``MAX_TREE_DEPTH``. Parsing, the sanitizer's walk and rendering keep their
own stacks, so neither a parsed nor an author-built tree of any depth raises
``RecursionError``, and the work stays linear.

Chromium: ``tests/06_browser/test_tree_construction_browser.py``.
"""

from __future__ import annotations

import asyncio
import random
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ux_dom import Document
from ux_dom.dom import defHTML, div, iframe, span
from ux_dom.dom.src.parse_html import MAX_TREE_DEPTH, Tree, tokenize_html
from ux_dom.response import sanitize_html, sanitize_html_stream

# Input -> sanitized output. Each output parses in Chromium to the DOM the
# input parses to (``test_tree_construction_browser.py``).
IMPLIED = [
    ("<p>one<p>two<p>three", "<p>one</p><p>two</p><p>three</p>"),
    ("<ul><li>a<li>b<li>c</ul>", "<ul><li>a</li><li>b</li><li>c</li></ul>"),
    (
        "<ol><li>a<ol><li>b<li>c</ol><li>d</ol>",
        "<ol><li>a<ol><li>b</li><li>c</li></ol></li><li>d</li></ol>",
    ),
    ("<ul><li><p>a<li>b</ul>", "<ul><li><p>a</p></li><li>b</li></ul>"),
    ("<li>a<div><li>b</div>", "<li>a<div></div></li><li>b</li>"),
    (
        "<dl><dt>a<dd>b<dt>c<dd>d</dl>",
        "<dl><dt>a</dt><dd>b</dd><dt>c</dt><dd>d</dd></dl>",
    ),
    ("<dd>a<div><dt>b", "<dd>a<div></div></dd><dt>b</dt>"),
    (
        "<select><option>a<option>b<optgroup label=x><option>c</select>",
        '<select><option>a</option><option>b</option><optgroup label="x">'
        "<option>c</option></optgroup></select>",
    ),
    (
        "<select><option>a<hr><option>b</select>",
        "<select><option>a</option><hr><option>b</option></select>",
    ),
    (
        "<select><option><p>a<option>b</select>",
        "<select><option><p>a</p></option><option>b</option></select>",
    ),
    ("<p><select><p>a", "<p><select><p>a</p></select></p>"),
    ("<option>a<option>b", "<option>a</option><option>b</option>"),
    (
        "<ruby>a<rt>b<rp>(<rt>c</ruby>",
        "<ruby>a<rt>b</rt><rp>(</rp><rt>c</rt></ruby>",
    ),
    (
        "<table><tr><td>a<td>b<tr><td>c</table>",
        "<table><tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr>"
        "</tbody></table>",
    ),
    (
        "<table><caption>c<tr><th>h</table>",
        "<table><caption>c</caption><tbody><tr><th>h</th></tr></tbody></table>",
    ),
    (
        "<table><col><tr><td>a</table>",
        "<table><colgroup><col></colgroup><tbody><tr><td>a</td></tr></tbody>"
        "</table>",
    ),
    (
        "<table><thead><tr><th>h<tbody><tr><td>a<tfoot><tr><td>f</table>",
        "<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>a</td></tr>"
        "</tbody><tfoot><tr><td>f</td></tr></tfoot></table>",
    ),
    (
        "<table><td>a<table><td>b</table>c</table>",
        "<table><tbody><tr><td>a<table><tbody><tr><td>b</td></tr></tbody>"
        "</table>c</td></tr></tbody></table>",
    ),
    ("<table><table>", "<table></table><table></table>"),
    ("<button>a<button>b", "<button>a</button><button>b</button>"),
    ("<h1>a<h2>b", "<h1>a</h1><h2>b</h2>"),
    ("<h3>a</h4>b", "<h3>a</h3>b"),
    ("<p>a<div>b</div>c", "<p>a</p><div>b</div>c"),
    ("<p>a<ul><li>b</ul>", "<p>a</p><ul><li>b</li></ul>"),
    ("<p>a<hr>b", "<p>a</p><hr>b"),
    ("<p>a<pre>b</pre>", "<p>a</p><pre>b</pre>"),
    (
        "<p>a<table><tr><td>b</table>",
        "<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table>",
    ),
    ("<section>a<p>b<section>c", "<section>a<p>b</p><section>c</section></section>"),
    (
        "<details><summary>s<p>a<summary>t</details>",
        "<details><summary>s<p>a</p><summary>t</summary></summary></details>",
    ),
    ("<p>a</p></p>b", "<p>a</p><p></p>b"),
    ("x</br>y", "x<br>y"),
    ("<span>a<div>b</span>c</div>d", "<span>a<div>bc</div>d</span>"),
    ("<form>a<form>b</form>c</form>", "<form>ab</form>c"),
    ("<form><div>a</form>b", "<form><div>ab</div></form>"),
    ("<div/>x", "<div>x</div>"),
    ("<p/>x<p>y", "<p>x</p><p>y</p>"),
    ("<svg><p>a</svg>b", "<svg></svg><p>ab</p>"),
    ("<p>a<svg><p>b", "<p>a<svg></svg></p><p>b</p>"),
    ("<li>a<svg><li>b", "<li>a<svg></svg></li><li>b</li>"),
    ("<svg><desc><p>a<p>b</desc></svg>", "<svg><desc><p>a</p><p>b</p></desc></svg>"),
    (
        "<svg><g><option>a<option>b</svg>",
        "<svg><g><option>a<option>b</option></option></g></svg>",
    ),
]


def _depth(root) -> int:
    deepest, stack = 0, [(root, 0)]
    while stack:
        node, depth = stack.pop()
        deepest = max(deepest, depth)
        stack.extend((c, depth + 1) for c in node.children if c.name)
    return deepest


def _chunks(text: str, seed: int) -> list[str]:
    rng = random.Random(seed)
    cuts = sorted(rng.sample(range(1, len(text)), min(len(text) - 1, 40)))
    return [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)])]


def _stream(chunks) -> str:
    return "".join(sanitize_html_stream(iter(chunks)))


@pytest.mark.parametrize("src,expected", IMPLIED)
def test_end_tags_are_implied_as_a_browser_implies_them(src, expected):
    assert sanitize_html(src) == expected
    assert _stream(list(src)) == expected


def test_paragraphs_are_siblings_not_nested():
    """The display bug of #125: Chromium built 5 ``<p>`` from the output."""
    out = sanitize_html("<p>one<p>two<p>three")
    assert out.count("<p>") == 3 and "<p>one</p>" in out


def test_tree_is_capped_at_chromiums_depth():
    """Chromium: ``<i>`` x 600 gives 512 levels; ``n512`` .. ``n600`` are
    children of ``n511``, and each text stays in its own element."""
    root = tokenize_html("".join(f"<i>t{i}" for i in range(1, 601)))
    assert MAX_TREE_DEPTH == 512 and _depth(root) == 512
    node = root
    for _ in range(511):
        node = node.children[-1]
    kids = [c for c in node.children if c.name]
    assert [c.children[0].data for c in kids] == [f"t{i}" for i in range(512, 601)]


# Shapes that nest without end tags. ``<div>`` / ``<b>`` / ``<span>`` /
# custom / svg nest in a browser too (up to the cap); ``<li>`` / ``<p>`` /
# ``<td>`` / ``<option>`` do not.
DEEP = {
    "div": lambda n: "<div>a" * n,
    "b": lambda n: "<b>a " * n,
    "span close": lambda n: "<span>" * n + "x" + "</span>" * n,
    "li": lambda n: "<ul>" + "<li>item" * n,
    "p": lambda n: "<p>x" * n,
    "custom": lambda n: "<x-y>a" * n,
    "svg": lambda n: "<svg>" + "<g>" * n + "</svg>",
    "table": lambda n: "<table><tr><td><table>" * (n // 4),
    "select": lambda n: "<select>" + "<option>o" * n,
}


@pytest.mark.parametrize("n", [600, 5_000, 20_000])
@pytest.mark.parametrize("shape", sorted(DEEP))
def test_deep_input_never_raises_recursion_error(shape, n):
    text = DEEP[shape](n)
    whole = sanitize_html(text)
    assert _depth(tokenize_html(text)) <= MAX_TREE_DEPTH
    assert _stream(_chunks(text, n)) == whole
    assert "".join(node.__render__(pretty=False) for node in defHTML(text)) == whole
    assert iframe(srcdoc=text).__render__(pretty=False).startswith("<iframe srcdoc=")


@pytest.mark.parametrize("n", [600, 20_000])
def test_deep_parsed_tree_renders_in_a_document(n):
    page = Document(head=[], body=[])(div(*defHTML("<span>" * n + "x")))
    html = page.__render__()
    assert html.count("<span>") == n and "x" in html


def _deep_author_tree(n: int):
    node = div("x")
    for _ in range(n - 1):
        node = div(node)
    return node


def _arender(node, pretty: bool) -> str:
    async def go():
        return "".join([t async for t in node.__async_render__(pretty=pretty)])

    return asyncio.run(go())


@pytest.mark.parametrize("n", [600, 5_000, 20_000])
def test_deep_author_tree_renders(n):
    """A tree built with the DOM API has no cap: it renders at any depth."""
    tree = _deep_author_tree(n)
    flat = "<div>" * n + "x" + "</div>" * n
    assert tree.__render__(pretty=False) == flat
    assert _arender(tree, False) == flat
    pretty = tree.__render__(pretty=True)
    assert pretty.count("<div>") == n and _arender(tree, True) == pretty
    page = Document(head=[], body=[])(tree).__render__()
    assert page.count("<div>") == n
    assert span not in tree and len(tree.get(div)) == n - 1


@pytest.mark.parametrize("shape", sorted(DEEP))
def test_parse_time_is_linear_in_depth(shape):
    def seconds(n):
        text = DEEP[shape](n)
        start = time.perf_counter()
        sanitize_html(text)
        return time.perf_counter() - start

    small, large = seconds(5_000), seconds(20_000)
    assert large < 8 * small + 0.5, (shape, small, large)  # quadratic is 16x


# Inputs whose naive scope checks walk the whole stack once per tag.
ADVERSARIAL = {
    "p below a table": lambda n: "<p><table>" + "<div>" * n,
    "end tags under foreign": lambda n: "<svg>" + "<g>" * n + "</x>" * n,
    "end tags under special": lambda n: "<span>" + "<div>" * n + "</span>" * n,
    "li below a div": lambda n: "<li>" + "<div>" * n + "<li>" * n,
    "form re-push": lambda n: ("<form>" + "<div>" * 50 + "</form>") * (n // 50),
    "table cells": lambda n: "<table>" + "<td>x" * n,
}


@pytest.mark.parametrize("shape", sorted(ADVERSARIAL))
def test_tree_construction_work_is_linear(shape, monkeypatch):
    pushes = []
    push = Tree._push

    def counted(self, node):
        pushes.append(1)
        return push(self, node)

    monkeypatch.setattr(Tree, "_push", counted)
    text = ADVERSARIAL[shape](20_000)
    start = time.perf_counter()
    tokenize_html(text)
    elapsed = time.perf_counter() - start
    assert len(pushes) <= 2 * text.count("<"), (shape, len(pushes))
    assert elapsed < 5, (shape, elapsed)


TAGS = (
    "p div span li ul ol dl dt dd h1 h2 b i a em table tbody thead tfoot tr "
    "td th caption colgroup col select option optgroup ruby rb rt rp rtc "
    "button form svg g desc foreignObject math mi annotation-xml template "
    "pre hr br img input x-y"
).split()
PIECE = st.one_of(
    st.sampled_from(TAGS).map(lambda t: f"<{t}>"),
    st.sampled_from(TAGS).map(lambda t: f"</{t}>"),
    st.sampled_from(TAGS).map(lambda t: f"<{t}/>"),
    st.sampled_from(["x", " ", "<img src=x onerror=alert(1)>", "<script>x"]),
)


@settings(max_examples=400, deadline=None)
@given(st.lists(PIECE, min_size=1, max_size=40), st.integers(1, 30))
def test_fuzzed_nesting_is_bounded_and_streams_equal(pieces, repeat):
    text = "".join(pieces) * repeat
    root = tokenize_html(text)
    assert _depth(root) <= MAX_TREE_DEPTH
    whole = sanitize_html(text)
    assert "onerror" not in whole and "<script" not in whole
    assert _stream(_chunks(text, repeat)) == whole
