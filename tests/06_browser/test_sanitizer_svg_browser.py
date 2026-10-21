"""Live Chromium: camelCase SVG names kept by the string sanitizer (#104).

Each kept name, in lower, upper and camel case, goes through ``defHTML``
inside ``<svg>`` with a child and a sibling. Chromium parses the output; its
element tree (``localName``, ``namespaceURI``, nesting) must hold the SVG
element with its case, so an unwrapped or misnamed element fails. The
dropped names leave no element. Exact strings:
``tests/07_resilience/test_html_svg_names.py``.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ux_dom.dom.src.html_string import _sanitized_html

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "dom_tree_harness.mjs"
SVG_NS = "http://www.w3.org/2000/svg"

KEPT = ["clipPath", "linearGradient", "radialGradient", "textPath"]
DROPPED = ["animateMotion", "animateTransform", "foreignObject", "set"]
SPELLINGS = {"lower": str.lower, "upper": str.upper, "camel": lambda n: n}


def _svg(*children):
    return [["svg", SVG_NS, list(children)]]


def _cases():
    """``(label, sanitized html, expected Chromium tree)``."""
    cases = []
    for name in KEPT:
        for spelling, spell in SPELLINGS.items():
            tag = spell(name)
            src = f"<svg><{tag} id=x><rect></rect></{tag}><circle></circle></svg>"
            tree = _svg([name, SVG_NS, [["rect", SVG_NS, []]]], ["circle", SVG_NS, []])
            cases.append((f"{name} {spelling}", _sanitized_html(src), tree))
    for name in DROPPED:
        src = f"<svg><{name}><rect></rect></{name}><circle></circle></svg>"
        cases.append((name, _sanitized_html(src), _svg(["circle", SVG_NS, []])))
    return cases


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


class TestSanitizerSvgBrowser(unittest.TestCase):
    def test_chromium_builds_the_kept_svg_elements(self):
        cases = _cases()
        dom = _browser(sorted({html for _, html, _ in cases}))
        for label, html, tree in cases:
            with self.subTest(label):
                self.assertEqual(dom[html], tree, html)


if __name__ == "__main__":
    unittest.main()
