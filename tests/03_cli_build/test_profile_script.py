"""scripts/profile_p95.py is a thin alias for ``uxdom profile``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "profile_p95.py"


def test_forwards_cli_options(tmp_path):
    out = tmp_path / "p95"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out",
            str(out),
            "--rounds",
            "3",
            "--warmup",
            "1",
            "--profile-rounds",
            "2",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "latency.json").is_file()


def test_runs_from_a_plain_checkout():
    """Without an install, ``ux_dom`` is found under ``src/`` (not the repo root).

    The dev venv has an editable install, so a subprocess cannot show this;
    the path is checked statically.
    """
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'ROOT / "src"' in text
