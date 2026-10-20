"""Live Chromium: pretty and flat renders display the same text (#79, #89)."""

from __future__ import annotations

import json
import random
import subprocess
import unittest
from pathlib import Path

from ux_dom import Fragment
import ux_dom.dom as tags
from ux_dom.dom import b, comment, div, em, i, lazy, li, p, pre, q, span, td, ul
from ux_dom.dom.src.htmltags import html_tag

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "inner_text_harness.mjs"

CORPUS = [
    Fragment("a&#39;b"),
    Fragment("<p>AT&T x</p>"),
    Fragment("<p>Tom &amp; Jerry&#33; &copy;2026</p>"),
    Fragment('<p>hello <b>world</b>, see <a href="/x">link</a>.</p>'),
    Fragment("<div>x<span>y</span>z</div>"),
    Fragment("<ul><li>one &lt;two&gt;</li><li>a<em>b</em>c</li></ul>"),
    Fragment("<div><p>a&#39;b <i>c</i>d</p><p>e</p></div>"),
    Fragment("<pre>a&lt;b\n  c&amp;d</pre>"),
    p("a", b("x"), "y"),
    div(p("x", em("y"), "&"), ul(li("1 < 2"), li("a", b("b")))),
    pre("a\n  b", b("x"), "c"),
    p(b("x"), lazy(lambda: "y")),
    p("a", lazy(lambda: b("x")), "c"),
    div(lazy(lambda: span("a")), lazy(lambda: "b&c")),
    div(lazy(lambda: p("a", i("b"))), p("c")),
    div(b("a"), i("b")),
    Fragment("<b>a</b><i>b</i>"),
    div(b("a"), comment("c"), i("b")),
    div(b("a"), p("x"), i("b")),
    div(q("x"), q()),
    div(li(li(), "y"), "x"),
    div("x", p(span(div("y"))), "z"),
    div(td("1"), "w"),
]

TEXT = ["x", "a&#39;b", "AT&T", "y z", " ", "", "w\n  v"]
ELEMENTS = (
    [
        getattr(tags, name)
        for name in """div p section ul ol li h2 blockquote dl dt dd details summary
    fieldset legend span b i a em code label strong q button""".split()
    ]
    + [type("my_el", (html_tag,), {})]
)  # an unknown tag
LEAVES = [
    lambda: tags.br(),
    lambda: tags.img(alt="I"),
    lambda: comment("c"),
    lambda: lazy(lambda: "L"),
    lambda: lazy(lambda: div("d")),
    lambda: Fragment(),
    lambda: tags.select(tags.option("o1"), tags.option("o2")),
]


def random_tree(rng: random.Random, depth: int):
    """Deep, wide and mixed: block, inline, wrappers, tables, misnesting."""
    roll = rng.random()
    if depth <= 0 or roll < 0.22:
        return rng.choice(TEXT)
    if roll < 0.30:
        return rng.choice(LEAVES)()
    kids = [
        random_tree(rng, depth - 1)
        for _ in range(rng.randint(1, rng.choice([2, 4, 7])))
    ]
    if roll < 0.33:
        return pre("q\n  r", *kids[:1])
    if roll < 0.40:
        return Fragment(*kids)
    if roll < 0.43:
        return tags.table(tags.tbody(tags.tr(*(td(k) for k in kids))))
    return rng.choice(ELEMENTS)(*kids)


def fuzz_corpus(n=1200, seed=89):
    rng = random.Random(seed)
    return [
        div(*(random_tree(rng, rng.choice([3, 4, 5])) for _ in range(3)))
        for _ in range(n)
    ]


class TestPrettyInnerTextBrowser(unittest.TestCase):
    def test_pretty_and_flat_display_the_same_text(self):
        self.assertSameText(CORPUS)

    def test_random_trees_display_the_same_text(self):
        self.assertSameText(fuzz_corpus())

    def assertSameText(self, corpus):
        require_browser()
        pretty = [str(node) for node in corpus]
        flat = [node.__render__(pretty=False) for node in corpus]
        proc = subprocess.run(
            [NODE, str(HARNESS)],
            cwd=str(ROOT),
            input=json.dumps(pretty + flat),
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        texts = json.loads(proc.stdout)
        n = len(corpus)
        for i in range(n):
            with self.subTest(flat=flat[i]):
                self.assertEqual(texts[i], texts[n + i], pretty[i])


if __name__ == "__main__":
    unittest.main()
