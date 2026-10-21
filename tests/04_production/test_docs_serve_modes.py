"""Docs cite ``uxcompose serve`` with a real mode (ADR 0003).

ux-compose ``cli/serve.py`` rejects anything but ``dev`` / ``prod`` /
``restart-channel`` as the first argument, so ``uxcompose serve app:asgi``
and ``uxcompose serve --hmr`` are dead examples.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_BAD = re.compile(r"uxcompose serve +(?!(?:dev|prod|restart-channel)\b)([\w:.-]+)")
# Released history may quote old commands.
_SKIP = {"CHANGELOG.md"}


def _files() -> list[Path]:
    out = [
        p
        for p in ROOT.rglob("*.md")
        if not {".git", ".venv", "node_modules", "changelog.d"} & set(p.parts)
    ]
    out += list((ROOT / "src" / "ux_dom").rglob("*.py"))
    return [p for p in out if p.name not in _SKIP]


class TestServeExamplesNameAMode(unittest.TestCase):
    def test_no_modeless_serve_examples(self):
        bad = [
            f"{p.relative_to(ROOT)}: uxcompose serve {m.group(1)}"
            for p in _files()
            for m in _BAD.finditer(p.read_text(encoding="utf-8", errors="replace"))
        ]
        self.assertEqual(bad, [], "use `uxcompose serve dev|prod`:\n" + "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
