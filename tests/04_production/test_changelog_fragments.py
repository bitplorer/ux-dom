"""scripts/changelog.py: per-PR fragments in changelog.d/ (check, preview, release)."""
from __future__ import annotations

import datetime
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
    (d / "chore-tool.added.md").write_text("- A tool.\n  Second line.\n", encoding="utf-8")
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
    today = datetime.date.today().isoformat()
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
