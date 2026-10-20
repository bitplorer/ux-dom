"""F-21: the Fragment example in docs/guides/SNIPPETS.md must run as written."""

from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

SNIPPETS = Path(__file__).resolve().parents[2] / "docs" / "guides" / "SNIPPETS.md"
HEADING = "### Fragment fans attrs onto children"


def _fragment_snippet() -> str:
    text = SNIPPETS.read_text(encoding="utf-8")
    assert HEADING in text, f"{HEADING!r} missing from {SNIPPETS}"
    section = text.split(HEADING, 1)[1].split("\n### ", 1)[0]
    blocks = re.findall(r"```python\n(.*?)```", section, re.S)
    assert len(blocks) == 1, f"expected one python block under {HEADING!r}"
    return blocks[0]


def test_fragment_classname_snippet_runs_as_documented():
    ns: dict[str, object] = {}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(_fragment_snippet(), str(SNIPPETS), "exec"), ns)
    html = out.getvalue()
    assert html == ns["tree"].__render__() + "\n"  # type: ignore[attr-defined]
    # The doc claims class="row" lands on each child.
    assert html.count('class="row"') == 2, html
    assert html.count("<span") == 2 and "A" in html and "B" in html
