"""Live Chromium: the string parser builds Chromium's tree (#125).

Two checks over the implied-end-tag corpus of
``tests/07_resilience/test_html_tree_construction.py``, deep inputs, and
seeded random nesting:

* the element tree ``tokenize_html`` builds (names and namespaces) is the
  tree Chromium builds from the same string (``dom_tree_harness.mjs``);
* ``sanitize_html`` of the string parses in Chromium to the DOM the string
  itself parses to (``parse_roundtrip_harness.mjs``).

The random nesting leaves out what the parser does not model (the adoption
agency for formatting elements, foster parenting, the form element pointer,
table parts outside a table), named in ``parse_html.Tree``.
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import unittest
from pathlib import Path

from ux_dom.dom.src.html_string import _ALLOWED_TAGS
from ux_dom.dom.src.parse_html import tokenize_html
from ux_dom.response import sanitize_html

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / "tests" / "browser" / "dom_tree_harness.mjs"
ROUNDTRIP = ROOT / "tests" / "browser" / "parse_roundtrip_harness.mjs"
NS = {
    "html": "http://www.w3.org/1999/xhtml",
    "svg": "http://www.w3.org/2000/svg",
    "math": "http://www.w3.org/1998/Math/MathML",
}

CORPUS = [
    "<p>one<p>two<p>three",
    "<ul><li>a<li>b<li>c</ul>",
    "<ol><li>a<ol><li>b<li>c</ol><li>d</ol>",
    "<ul><li><p>a<li>b</ul>",
    "<li>a<div><li>b</div>",
    "<dl><dt>a<dd>b<dt>c<dd>d</dl>",
    "<dd>a<div><dt>b",
    "<select><option>a<option>b<optgroup label=x><option>c</select>",
    "<select><option>a<hr><option>b</select>",
    "<select><option><p>a<option>b</select>",
    "<select><option>a<input>b</select>",
    "<p><select><p>a",
    "<option>a<option>b",
    "<ruby>a<rt>b<rp>(<rt>c</ruby>",
    "<ruby>a<rb>b<rt>c<rtc>d<rt>e<rb>f</ruby>",
    "<table><tr><td>a<td>b<tr><td>c</table>",
    "<table><caption>c<tr><th>h</table>",
    "<table><col><tr><td>a</table>",
    "<table><colgroup><col><col><tr><td>a</table>",
    "<table><thead><tr><th>h<tbody><tr><td>a<tfoot><tr><td>f</table>",
    "<table><td>a<table><td>b</table>c</table>",
    "<table><tr><td><p>a<td>b</table>",
    "<table><table>",
    "<button>a<button>b",
    "<button><div><button>x",
    "<h1>a<h2>b",
    "<h1><div><h2>a",
    "<h3>a</h4>b",
    "<p>a<div>b</div>c",
    "<p>a<ul><li>b</ul>",
    "<p>a<hr>b",
    "<p>a<pre>b</pre>",
    "<p>a<address>b",
    "<p>a<table><tr><td>b</table>",
    "<p>a<button><p>b",
    "<section>a<p>b<section>c",
    "<details><summary>s<p>a<summary>t</details>",
    "<p>a</p></p>b",
    "x</br>y",
    "<span>a<div>b</span>c</div>d",
    "<form>a<form>b</form>c</form>",
    "<form><div>a</form>b",
    "<div/>x",
    "<p/>x<p>y",
    "<svg/>x",
    "<svg><p>a</svg>b",
    "<p>a<svg><p>b",
    "<li>a<svg><li>b",
    "<svg><desc><p>a<p>b</desc></svg>",
    "<svg><g><option>a<option>b</svg>",
    "<p>a<svg><font color=red>b",
    "<math><mi><p>a</math>",
    "<math><annotation-xml><p>a",
]
DEEP = [
    "<div>" * 600 + "x",
    "".join(f"<i>t{i}" for i in range(600)),
    "<ul>" + "<li>item" * 600,
    "<p>x" * 600,
    "<span>" * 2000 + "y",
    "<form>" + "<div>" * 600 + "</form>z",
    "<svg>" + "<g>" * 700 + "</svg>q",
]
# Random nesting over what the parser models.
BODY = (
    "p div li ul ol dl dt dd h1 h2 h3 section span option optgroup select "
    "ruby rb rt rp rtc button hr br svg g desc foreignObject math mi pre "
    "address details summary blockquote nav"
).split()
CELL = "tr td th tbody thead tfoot caption".split()


def _body(rng: random.Random, n: int) -> str:
    out = []
    for _ in range(n):
        r, tag = rng.random(), rng.choice(BODY)
        out.append(
            f"<{tag}>" if r < 0.55 else f"</{tag}>" if r < 0.8 else rng.choice("xy ")
        )
    return "".join(out)


def _table(rng: random.Random) -> str:
    """Table parts only in table context; content only in cells."""
    out = ["<table>"]
    for _ in range(rng.randint(1, 6)):
        tag = rng.choice(CELL)
        out.append(f"<{tag}>")
        if tag in ("td", "th", "caption"):
            out.append(_body(rng, rng.randint(0, 4)))
    out.append("</table>")
    return "".join(out)


def _fuzz() -> list[str]:
    rng = random.Random(125)
    return [_body(rng, rng.randint(2, 14)) for _ in range(500)] + [
        _table(rng) for _ in range(200)
    ]


def _names(html: str) -> set[str]:
    return {name.lower() for name in re.findall(r"</?([a-zA-Z][\w-]*)", html)}


def _model(node) -> list:
    return [
        [c.name.lower(), NS[c.namespace], _model(c)] for c in node.children if c.name
    ]


def _lower(tree: list) -> list:
    return [[name.lower(), ns, _lower(kids)] for name, ns, kids in tree]


def _run(harness: Path, snippets: list[str]) -> list:
    require_browser()
    proc = subprocess.run(
        [NODE, str(harness)],
        cwd=str(ROOT),
        input=json.dumps(snippets),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


class TestTreeConstructionBrowser(unittest.TestCase):
    def test_parsed_tree_is_chromiums(self):
        snippets = CORPUS + _fuzz()
        trees = _run(TREE, snippets)
        wrong = [
            s
            for s, tree in zip(snippets, trees)
            if _model(tokenize_html(s)) != _lower(tree)
        ]
        self.assertEqual(wrong, [])

    def test_sanitized_output_parses_to_the_same_dom(self):
        snippets = CORPUS + DEEP + _fuzz()
        # A tag off the allowlist (``rb``, ``mi``, …) is unwrapped, which
        # changes the DOM on purpose: keep strings of allowlisted tags only.
        kept = [s for s in snippets if _names(s) <= _ALLOWED_TAGS]
        self.assertGreater(len(kept), 300)
        raw = _run(ROUNDTRIP, kept)
        clean = _run(ROUNDTRIP, [sanitize_html(s) for s in kept])
        wrong = [s for s, a, b in zip(kept, raw, clean) if a["html"] != b["html"]]
        self.assertEqual(wrong, [])


if __name__ == "__main__":
    unittest.main()
