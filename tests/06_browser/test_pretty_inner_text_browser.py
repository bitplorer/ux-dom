"""Live Chromium: pretty and flat renders display the same text (#79)."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ux_dom import Fragment
from ux_dom.dom import b, div, em, li, p, pre, ul

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
]


class TestPrettyInnerTextBrowser(unittest.TestCase):
    def test_pretty_and_flat_display_the_same_text(self):
        require_browser()
        pretty = [str(node) for node in CORPUS]
        flat = [node.__render__(pretty=False) for node in CORPUS]
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
        n = len(CORPUS)
        for i in range(n):
            with self.subTest(flat=flat[i]):
                self.assertEqual(texts[i], texts[n + i], pretty[i])


if __name__ == "__main__":
    unittest.main()
