"""uxdom CLI messages reach the user; doctor reports the real ux-channel import."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from typer.testing import CliRunner

from ux_dom.cli.cli import app
from ux_dom.cli.doctor import run_doctor


def test_ui_lists_components():
    result = CliRunner().invoke(app, ["ui"])
    assert result.exit_code == 0, result.output
    assert "Button" in result.stdout


def test_ui_has_no_dead_action_option():
    result = CliRunner().invoke(app, ["ui", "--help"])
    assert result.exit_code == 0, result.output
    assert "--action" not in result.output


def test_lint_failure_is_reported(tmp_path: Path):
    (tmp_path / "app").mkdir()
    result = CliRunner().invoke(app, ["lint", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "app/document.py" in result.stdout
    assert "missing" in result.stdout


def test_add_error_goes_to_stderr():
    result = CliRunner().invoke(app, ["add", "nope", "x"])
    assert result.exit_code == 2
    assert "kind must be" in result.stderr
    assert "kind must be" not in result.stdout


def test_doctor_broken_ux_channel_is_not_ok(tmp_path: Path, monkeypatch):
    pkg = tmp_path / "ux_channel"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("raise RuntimeError('broken install')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "ux_channel", raising=False)
    importlib.invalidate_caches()

    report = run_doctor(cwd=tmp_path, port=59992)
    check = next(c for c in report.checks if c.name == "ux-channel")
    assert check.ok is False
    assert check.level == "warn"
    assert "RuntimeError" in check.detail
    assert "broken install" in check.detail
