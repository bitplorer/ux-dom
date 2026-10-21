"""Every ``uxdom …`` line in a docs code block parses as a real command (#128).

``uxdom ui list`` sat in three places and exits 2: the command is ``uxdom ui``.
Each line is parsed by the Click tree, not run, so nothing is written.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest
from typer.main import get_command

from ux_dom.cli import app

ROOT = Path(__file__).resolve().parents[2]
_LINE = re.compile(r"\s*(?:\$ )?uxdom( .*)?$")


def _documented():
    """``(where, argv)`` per ``uxdom`` line in a Markdown code block or a
    docstring of ``src``. Diagram lines such as ``uxdom doctor | lint`` are not
    commands."""
    docs = [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md")]
    found = []
    for path in [*docs, *(ROOT / "src").rglob("*.py")]:
        fenced = path.suffix == ".py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if path.suffix == ".md" and line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            m = _LINE.match(line)
            if fenced and m and "|" not in line:
                argv = shlex.split(m.group(1) or "", comments=True)
                found.append((f"{path.relative_to(ROOT)}:{n}", argv))
    return found


DOCUMENTED = _documented()


def _error(argv):
    """Why ``uxdom *argv`` is not a command, or ``None``. Click parses it; no
    command runs."""
    cmd, name = get_command(app), "uxdom"
    ctx = cmd.make_context(name, [], resilient_parsing=True)
    while argv and not argv[0].startswith("-") and hasattr(cmd, "get_command"):
        name, cmd, argv = argv[0], cmd.get_command(ctx, argv[0]), argv[1:]
        if cmd is None:
            return f"no such command {name!r}"
        ctx = cmd.make_context(name, [], parent=ctx, resilient_parsing=True)
    try:
        cmd.make_context(name, list(argv), parent=ctx.parent)
    except Exception as exc:  # Click's UsageError (2), or Exit (0) for --help
        if getattr(exc, "exit_code", 1):
            return str(exc)
    return None


def test_docs_name_uxdom_commands():
    assert len(DOCUMENTED) >= 10, DOCUMENTED


@pytest.mark.parametrize("argv", ["ui list", "nope", "doctor --nope"])
def test_unknown_command_is_an_error(argv):
    assert _error(argv.split())


@pytest.mark.parametrize(
    "where,argv", DOCUMENTED, ids=[where for where, _ in DOCUMENTED]
)
def test_documented_command_parses(where, argv):
    assert _error(argv) is None, f"{where}: uxdom {shlex.join(argv)}"
