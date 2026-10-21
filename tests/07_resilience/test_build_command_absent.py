"""ADR 0003 rule 4 absence lock: ``uxdom`` has no ``build`` command (#109).

The product build is ``uxcompose build`` (CSS, ``import:app:asgi`` and, with
``--package/--archive``, the runnable bundle of ux-compose #130). The removed
``uxdom build`` once cleared the project with ``--package --out ..`` (#101).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from ux_dom.cli.cli import app


@pytest.mark.parametrize("args", [["build"], ["build", "--help"], ["build", "--skip-import"]])
def test_build_is_no_such_command(args: list[str]):
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 2, result.output
    assert "No such command 'build'" in result.output


def test_build_is_not_registered():
    assert "build" not in get_command(app).commands


@pytest.mark.parametrize("module", ["ux_dom.cli.build", "ux_dom.cli.static_assets"])
def test_build_modules_are_gone(module: str):
    with pytest.raises(ImportError):
        importlib.import_module(module)


def test_out_parent_cannot_delete_the_project(tmp_path: Path, monkeypatch):
    proj = tmp_path / "parent" / "proj"
    (proj / "app").mkdir(parents=True)
    (proj / "app" / "main.py").write_text("app = object()\n", encoding="utf-8")
    (proj / ".env").write_text("SECRET=1\n", encoding="utf-8")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(app, ["build", "--package", "--out", ".."])
    assert result.exit_code == 2, result.output
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before
