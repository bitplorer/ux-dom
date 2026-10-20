"""Live Chromium: pretty and flat renders compute the same values (#88).

Each page is rendered pretty and flat. The values the browser derives from
raw text and preformatted bodies (JS template literals, a regex built from
one, string continuations, CSS ``content`` strings, textarea values, ``pre``
text) must be equal. Exact strings: ``tests/01_core/test_pretty_raw_text_verbatim.py``.

#93 already keeps the bodies of the inline raw text elements flat. Elements
matched only by name (``xmp``, ``listing``, ``plaintext``, an upper-case
``PRE``) are fixed by #88; ``RAW_TEXT_PAGES`` guards the rest.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ux_dom.dom import (
    div,
    iframe,
    noscript,
    p,
    pre,
    script,
    span,
    style,
    textarea,
    title,
)
from ux_dom.dom.src.ext import Tags
from ux_dom.dom.src.html_string import create_dynamic_element
from ux_dom.dom.src.svgtags import svg

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "raw_text_value_harness.mjs"


def _tag(name):
    return type(name, (Tags,), {"tagname": name})


def _probe(name):
    return span(className="probe " + name)


JS = (
    "__out.tpl = `line1\n  line2\n`;\n"
    "__out.re = [/ a  b /.test('x a  b y'), new RegExp(`^x\n  y$`).test('x\\n  y')];\n"
    "__out.cont = 'a\\\n   b';\n"
)
# Constructable stylesheet: CSS in a JS template literal (web components).
SHEET = (
    "const sheet = new CSSStyleSheet();\n"
    "sheet.replaceSync(`.c3::before { content: 'x\\\\\n    y'; }`);\n"
    "document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];\n"
)

# Elements the HTML parser matches by name, written by a class it does not
# know (dynamic, custom or upper-case): pretty indented their bodies.
NAMED_PAGES = {
    "xmp": lambda: div(create_dynamic_element("xmp")("a\n  b")),
    "listing": lambda: div(create_dynamic_element("listing")("\na\n  b")),
    "PRE": lambda: div(_tag("PRE")("a\n  b"), _tag("PRE")(div(p("c"), p("d")))),
    # <plaintext> has no end tag: it holds the rest of the page, so it is last.
    "plaintext": lambda: create_dynamic_element("plaintext")("a\n  b"),
}

RAW_TEXT_PAGES = {
    "script": lambda: div(script(JS)),
    "svg-script": lambda: div(svg(script("__out.svg = `p\n  q`;"))),
    "style": lambda: div(style(".c1::before { content: 'a\\\n  b'; }"), _probe("c1")),
    "svg-style": lambda: div(
        svg(style(".c2::before { content: 's\\\n  t'; }")), _probe("c2")
    ),
    "css-in-js": lambda: div(script(SHEET), _probe("c3")),
    "textarea": lambda: div(
        textarea("\nfirst\n  second\n"), _tag("TEXTAREA")("a\n  b")
    ),
    "pre": lambda: div(
        pre("\ncode\n  indented"),
        pre(span("a"), span("b")),
        pre(div(p("a"), p("b"))),
    ),
    "text-state": lambda: div(title("a\n  b"), iframe("c\n  d"), noscript("e\n  f")),
}


def _values(pages):
    """``(pretty, flat)`` browser values per page name."""
    require_browser()
    names = list(pages)
    pretty = [str(pages[n]()) for n in names]
    flat = [pages[n]().__render__(pretty=False) for n in names]
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps(pretty + flat),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    results = json.loads(proc.stdout)
    n = len(names)
    return dict(zip(names, results[:n])), dict(zip(names, results[n:])), pretty


class TestPrettyRawTextBrowser(unittest.TestCase):
    def assertSameValues(self, pages):
        got, want, pretty = _values(pages)
        for i, name in enumerate(pages):
            with self.subTest(page=name):
                self.assertEqual(got[name], want[name], pretty[i])
        return want

    def test_name_matched_bodies_keep_their_text(self):
        want = self.assertSameValues(NAMED_PAGES)
        # HTML drops one newline right after <listing> (and <pre>, <textarea>).
        self.assertEqual(want["xmp"]["texts"], ["a\n  b"])
        self.assertEqual(want["listing"]["texts"], ["a\n  b"])
        self.assertEqual(want["PRE"]["texts"], ["a\n  b", "cd"])
        self.assertTrue(want["plaintext"]["texts"][0].startswith("a\n  b</plaintext>"))

    def test_raw_text_values_match(self):
        want = self.assertSameValues(RAW_TEXT_PAGES)
        # The flat render is the author's text: check it is what the page says.
        self.assertEqual(
            want["script"]["out"],
            {"tpl": "line1\n  line2\n", "re": [True, True], "cont": "a   b"},
        )
        self.assertEqual(want["svg-script"]["out"], {"svg": "p\n  q"})
        self.assertEqual(want["style"]["before"], ['"a  b"'])
        self.assertEqual(want["svg-style"]["before"], ['"s  t"'])
        self.assertEqual(want["css-in-js"]["before"], ['"x    y"'])
        self.assertEqual(want["textarea"]["values"], ["first\n  second\n", "a\n  b"])
        self.assertEqual(want["pre"]["texts"], ["code\n  indented", "ab", "ab"])
        self.assertEqual(want["text-state"]["texts"], ["a\n  b", "c\n  d", "e\n  f"])


if __name__ == "__main__":
    unittest.main()
