"""scripts/changelog.py: per-PR fragments in changelog.d/ (check, preview, release)."""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "changelog.py"

CHANGELOG = """# Changelog

## Unreleased

- existing entry

## 0.1.0 — first

- old
"""


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    d = tmp_path / "changelog.d"
    d.mkdir()
    (d / "README.md").write_text("# not a fragment\n", encoding="utf-8")
    (d / "71-csp.fixed.md").write_text("- **Fix:** a bug.\n", encoding="utf-8")
    (d / "chore-tool.added.md").write_text(
        "- A tool.\n  Second line.\n", encoding="utf-8"
    )
    return tmp_path


def test_repo_fragments_pass_check():
    r = _run(ROOT, "--check")
    assert r.returncode == 0, r.stderr


def test_check_accepts_valid_fragments(repo: Path):
    r = _run(repo, "--check")
    assert r.returncode == 0, r.stderr
    assert "2 fragment(s) OK" in r.stdout


@pytest.mark.parametrize(
    "name, body",
    [
        ("71-csp.fix.md", "- typo type\n"),  # unknown type
        ("71-csp.md", "- no type\n"),
        ("Upper.fixed.md", "- bad slug\n"),
        ("a.b.fixed.md", "- dotted slug\n"),
        ("71-csp.fixed.txt", "- wrong suffix\n"),
        ("71-empty.fixed.md", "  \n\n"),
        ("71-prose.fixed.md", "not a bullet\n"),
        ("71-blank.fixed.md", "- \n"),  # empty bullet
        ("71-blank2.fixed.md", "- ok\n-   \n"),
    ],
)
def test_check_rejects_bad_fragments(repo: Path, name: str, body: str):
    (repo / "changelog.d" / name).write_text(body, encoding="utf-8")
    r = _run(repo, "--check")
    assert r.returncode == 1
    assert f"changelog.d/{name}" in r.stderr


def test_preview_keeps_existing_lines_then_typed_sections(repo: Path):
    r = _run(repo, "--preview")
    assert r.returncode == 0, r.stderr
    assert r.stdout == (
        "## Unreleased\n\n- existing entry\n\n"
        "### Added\n\n- A tool.\n  Second line.\n\n"
        "### Fixed\n\n- **Fix:** a bug.\n"
    )
    # preview is read-only
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == CHANGELOG
    assert len(list((repo / "changelog.d").iterdir())) == 3


def test_release_folds_fragments_and_deletes_them(repo: Path):
    r = _run(repo, "--release", "1.2.3")
    assert r.returncode == 0, r.stderr
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == (
        "# Changelog\n\n## Unreleased\n\n"
        f"## 1.2.3 — {today}\n\n- existing entry\n\n"
        "### Added\n\n- A tool.\n  Second line.\n\n"
        "### Fixed\n\n- **Fix:** a bug.\n\n"
        "## 0.1.0 — first\n\n- old\n"
    )
    assert [p.name for p in (repo / "changelog.d").iterdir()] == ["README.md"]
    # a second release has nothing left to fold
    again = _run(repo, "--release", "1.2.4")
    assert again.returncode == 1
    assert "nothing to release" in again.stderr


def test_release_refuses_invalid_fragments_and_versions(repo: Path):
    (repo / "changelog.d" / "bad.fix.md").write_text("- x\n", encoding="utf-8")
    assert _run(repo, "--release", "1.2.3").returncode == 1
    (repo / "changelog.d" / "bad.fix.md").unlink()
    r = _run(repo, "--release", "1.2")
    assert r.returncode == 1 and "X.Y.Z" in r.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == CHANGELOG


def test_repo_copy_release_round_trip(tmp_path: Path):
    """Release on a temp copy of the real CHANGELOG.md keeps every existing line."""
    shutil.copy(ROOT / "CHANGELOG.md", tmp_path / "CHANGELOG.md")
    shutil.copytree(ROOT / "changelog.d", tmp_path / "changelog.d")
    before = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert _run(tmp_path, "--release", "9.9.9").returncode == 0
    after = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert after.count("## 9.9.9 — ") == 1
    missing = [ln for ln in before.splitlines() if ln.strip() and ln not in after]
    assert missing == []


def test_release_refuses_existing_version(repo: Path):
    r = _run(repo, "--release", "0.1.0")
    assert r.returncode == 1
    assert "already has a '## 0.1.0' section" in r.stderr
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == CHANGELOG
    assert len(list((repo / "changelog.d").iterdir())) == 3


def test_fragments_sort_numerically(repo: Path):
    d = repo / "changelog.d"
    for n in ("100", "71", "9"):
        (d / f"{n}.changed.md").write_text(f"- pr {n}\n", encoding="utf-8")
    r = _run(repo, "--preview")
    assert r.returncode == 0, r.stderr
    assert "### Changed\n\n- pr 9\n- pr 71\n- pr 100\n" in r.stdout


# UTC-12 lags UTC's date when the UTC hour is < 12; UTC+14 leads it when >= 10.
# One of the two always differs from UTC, so the pair always discriminates.
@pytest.mark.parametrize("tz", ["Etc/GMT+12", "Etc/GMT-14"])
def test_release_heading_uses_utc_date(repo: Path, tz: str):
    """The heading date is the UTC date, whatever the local timezone."""
    env = {**os.environ, "TZ": tz}
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repo), "--release", "1.2.3"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    assert f"## 1.2.3 — {today}\n" in (repo / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )
