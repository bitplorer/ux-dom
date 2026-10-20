"""Live Chromium: parsing an HTML string keeps its whitespace (#96).

Each input goes through every string-to-node path (the parser, the fragment
sanitizer, document mode, ``Fragment``) and is rendered flat. Chromium parses
the input and the render; the DOM it builds (``innerHTML``), the text it shows
(``innerText``) and each ``<textarea>`` value must be the same.

Each sanitizer render is also compared with Chromium's ``innerHTML`` of the
input as a string. (The parser's own AST re-emits its source, so markup-like
text in a ``textarea`` stays unescaped there.) The one allowed difference: a text node in ``pre`` / ``textarea`` /
``listing`` holds the body as written, so the newline that the browser drops
right after the start tag is still there. Rendering it is what keeps the next
newline (``<pre>\\n\\nx``), which Chromium's own serialization loses.
Exact strings: ``tests/01_core/test_parse_whitespace.py``.
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import unittest
from pathlib import Path

from ux_dom import Fragment
from ux_dom.dom.src.html_string import _sanitized_html
from ux_dom.dom.src.parse_html import tokenize_html

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "parse_roundtrip_harness.mjs"

PATHS = {
    "parse": lambda s: tokenize_html(s).render(),
    "sanitize": _sanitized_html,
    "document": lambda s: _sanitized_html(s, document=True),
    "fragment": lambda s: Fragment(s).__render__(pretty=False),
}

CORPUS = [
    "<pre>\n\n  a\tb  \n</pre>",
    "<pre>\nx</pre>",
    "<pre>\n</pre>",
    "<pre>a\r\nb\rc\r\n</pre>",
    "<pre>\r\n\r\nx</pre>",
    "<pre>\r\rx</pre>",
    "<pre>  lead\n\ttab\n\n</pre>",
    "<pre><b>x</b>  <i>y</i>\n  z</pre>",
    "<pre>\n<span>  a</span>\n</pre>",
    "<pre><b>\nx</b></pre>",
    "<textarea>\n\n x  \t y\n\n</textarea>",
    "<textarea>\nx</textarea>",
    "<textarea>a\r\nb\rc</textarea>",
    "<textarea>\r\n\r\nx</textarea>",
    "<textarea>  <b>x</b>  &amp; </textarea>",
    "<listing>\n\n  a\n\tb\n</listing>",
    "<listing>\r\n x</listing>",
    "a <b>x</b> c",
    "a\n<b>x</b>\nc",
    "<p>a\n<b>x</b>\n<i>y</i></p>",
    "<p><b>x</b> <i>y</i></p>",
    "<p><b>x</b>\t<i>y</i></p>",
    "<p><b><i>a</i> </b> <u>b</u></p>",
    "<p>foo\n</p>",
    "<p>\n  one\n  <em>two</em>\n  three\n</p>",
    "<p>a\r\n<b>b</b>\rc</p>",
    "<p>  \t  </p>",
    "<span>a</span>\n<span>b</span>",
    "<ul>\n  <li>a</li>\n  <li>b <b>c</b></li>\n</ul>",
    "<div>\n  <p>x</p>\n\n  <p>y</p>\n</div>",
    "\n\n<p>x</p>\n\n",
    "x\t\ty",
    "  a  ",
    "\r\n",
]

# Raw text: ``script`` is dropped by the sanitizer and ``style`` is kept in
# document mode, so each runs only through the paths that keep it.
RAW_TEXT = {
    "<script>var a = 1;\r\n\tif (a  <  2) {}\r  </script>": ("parse",),
    "<script>\n\n  x = `a\n  b`\n</script>": ("parse",),
    "<style>\r\np  >  b {\tcolor: red }\r\n</style>": ("parse", "document"),
    "<style>\n\n  a::before { content: 'x  y' }\n</style>": ("parse", "document"),
}

_TEXT = ["a", "bc", " ", "  ", "\t", "\n", "\r\n", "\r", "\n\n", " \t ", "&amp;"]
_SPACE = [" ", "\n", "\r\n", "\t", "\n  "]
_INLINE = ["b", "i", "em", "span", "code"]
_BLOCK = ["pre", "textarea", "listing", "p", "div", "ul"]
# What each element holds; the rest hold inline content.
_CONTENT = {"div": "block", "ul": "ul", "textarea": "textarea"}


def _text(rng):
    return "".join(rng.choice(_TEXT) for _ in range(rng.randint(1, 5)))


def _node(rng, depth, context):
    """A well-formed tree, so the two parsers build the same elements."""
    if depth == 0 or context == "textarea":
        return _text(rng)
    if context == "ul":
        return f"<li>{_nodes(rng, depth - 1, 'block')}</li>"
    kind = rng.choice(["text", *_INLINE, *(_BLOCK if context == "block" else ())])
    if kind == "text":
        return _text(rng)
    return f"<{kind}>{_nodes(rng, depth - 1, _CONTENT.get(kind, 'inline'))}</{kind}>"


def _nodes(rng, depth, context):
    parts = [_node(rng, depth, context) for _ in range(rng.randint(1, 3))]
    # List items are separated by whitespace, as indented source has them.
    return (rng.choice(_SPACE) if context == "ul" else "").join(parts)


def _generated(count=150, seed=96):
    rng = random.Random(seed)
    return [_nodes(rng, 3, "block") for _ in range(count)]


_FIRST_NEWLINE = re.compile(r"(<(?:pre|textarea|listing)>)\n")


def _cases():
    cases = [(path, s) for s in CORPUS + _generated() for path in PATHS]
    cases += [(path, s) for s, paths in RAW_TEXT.items() for path in paths]
    return [(path, s, PATHS[path](s)) for path, s in cases]


def _browser(snippets):
    require_browser()
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps(snippets),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return dict(zip(snippets, json.loads(proc.stdout)))


class TestParseWhitespaceBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _cases()
        snippets = sorted({s for case in cls.cases for s in case[1:]})
        cls.dom = _browser(snippets)

    def test_render_builds_the_same_dom(self):
        for path, source, render in self.cases:
            with self.subTest(path=path, source=source):
                self.assertEqual(self.dom[render], self.dom[source], render)

    def test_sanitized_render_is_chromiums_inner_html(self):
        for path, source, render in self.cases:
            if path == "parse":
                continue
            with self.subTest(path=path, source=source):
                self.assertEqual(
                    _FIRST_NEWLINE.sub(r"\1", render), self.dom[source]["html"]
                )

    def test_oracle_sees_the_whitespace(self):
        # Guard the oracle itself: these are the browser's own values.
        dom = self.dom
        self.assertEqual(dom["<pre>\n\n  a\tb  \n</pre>"]["text"], "\n  a\tb  \n")
        self.assertEqual(dom["<textarea>a\r\nb\rc</textarea>"]["values"], ["a\nb\nc"])
        self.assertEqual(dom["<p><b>x</b> <i>y</i></p>"]["text"], "x y")
        self.assertEqual(dom["a\n<b>x</b>\nc"]["text"], "a x c")


if __name__ == "__main__":
    unittest.main()
