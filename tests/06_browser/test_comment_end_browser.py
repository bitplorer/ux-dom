"""Live Chromium: a comment ends where the browser ends it (#124).

For every string up to ``<!--`` plus 7 characters of ``-``, ``!``, ``>``
and ``a`` (``--!>``, ``--->``, ``<!-->``, ``<!--->``, unfinished ends, ...),
Chromium's parse (``parse_roundtrip_harness.mjs``) equals ``tokenize_html``'s
comments and text, and ``sanitize_html`` of the string parses in Chromium to
that text with the comments left out. Exact tokens:
``tests/07_resilience/test_comment_end.py``.
"""

from __future__ import annotations

import itertools
import json
import subprocess
import unittest
from html import escape
from pathlib import Path

from ux_dom.dom.src.parse_html import Comment, tokenize_html
from ux_dom.response import sanitize_html

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "parse_roundtrip_harness.mjs"


def _cases() -> list[str]:
    return [
        "<!--" + "".join(tail)
        for n in range(8)
        for tail in itertools.product("-!>a", repeat=n)
    ]


def _serialized(text: str, comments: bool) -> str:
    """What ``innerHTML`` gives back for ``tokenize_html``'s nodes."""
    out = []
    for node in tokenize_html(text):
        if not isinstance(node, Comment):
            out.append(escape(node.data, quote=False))
        elif comments:
            out.append(f"<!--{node.data}-->")
    return "".join(out)


def _chromium(snippets: list[str]) -> list[str]:
    require_browser()
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps(snippets),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return [r["html"] for r in json.loads(proc.stdout)]


class TestCommentEndBrowser(unittest.TestCase):
    def test_comments_and_text_match_chromium(self):
        cases = _cases()
        sanitized = [sanitize_html(t) for t in cases]
        seen = _chromium(cases + sanitized)
        parsed, reparsed = seen[: len(cases)], seen[len(cases) :]
        wrong = [
            (t, got, _serialized(t, True))
            for t, got in zip(cases, parsed)
            if got != _serialized(t, True)
        ]
        self.assertEqual(wrong, [])
        lost = [
            (t, got, _serialized(t, False))
            for t, got in zip(cases, reparsed)
            if got != _serialized(t, False)
        ]
        self.assertEqual(lost, [])


if __name__ == "__main__":
    unittest.main()
