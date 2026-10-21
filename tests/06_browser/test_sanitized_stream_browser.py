"""Live Chromium: sanitized strings and streams run no script (#121).

Every attack string from the sanitizer PRs (#32, #55, #85, #91, #97, #98,
#107, #113, #123, #125; ``tests/sanitizer_corpus.py``) goes through ``sanitize_html``
and through ``sanitize_html_stream`` with 1-character chunks and random split
points. Each distinct output loads in Chromium, which fires every handler,
link, form and animation it can (``exec_oracle_harness.mjs``): 0 executions.
The same harness on the raw attack strings must count executions, so the
oracle is live. Exact strings: ``tests/07_resilience/test_sanitized_stream.py``.
"""

from __future__ import annotations

import json
import random
import subprocess
import unittest
from pathlib import Path

from ux_dom.response import sanitize_html, sanitize_html_stream

from browser_gate import NODE, require_browser
from sanitizer_corpus import corpus

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "exec_oracle_harness.mjs"
SEEDS = range(8)

CONTROLS = [
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<details open ontoggle=alert(1)>",
    "<a href='javascript:alert(1)'>x</a>",
    "<form action='javascript:alert(1)'><button>x</button></form>",
    '<svg><a><animate attributeName="href" to="javascript:hit()" dur="0.05s" '
    'fill="freeze"/><rect width="50" height="50"/></a></svg>',
]


def _chunks(text: str, seed: int) -> list[str]:
    if seed == 0 or len(text) < 2:
        return list(text)
    rng = random.Random(seed)
    cuts = sorted(
        rng.sample(range(1, len(text)), min(len(text) - 1, rng.randint(1, 6)))
    )
    return [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)])]


def _browser(bodies: list[str]) -> dict:
    require_browser()
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps(bodies),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


class TestSanitizedStreamBrowser(unittest.TestCase):
    def test_oracle_counts_raw_attacks(self):
        result = _browser(CONTROLS)
        for html, hits in zip(CONTROLS, result["hits"]):
            with self.subTest(html):
                self.assertGreater(hits, 0)

    def test_no_sanitized_output_runs_script(self):
        outputs: dict[str, str] = {}
        for pr, text in corpus():
            outputs.setdefault(sanitize_html(text), pr)
            for seed in SEEDS:
                streamed = "".join(sanitize_html_stream(_chunks(text, seed)))
                outputs.setdefault(streamed, pr)
        bodies = sorted(outputs)
        result = _browser(bodies)
        ran = [(outputs[b], b) for b, hits in zip(bodies, result["hits"]) if hits]
        self.assertEqual(ran, [])
        self.assertEqual(result["stray"], 0)


if __name__ == "__main__":
    unittest.main()
