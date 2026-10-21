"""ADR 0003 rule 4 absence lock: ``uxdom build`` writes no runnable bundle.

Runnable bundles are ``uxcompose build --package/--archive`` (ux-compose #130). The
removed bundle path was ``<out>/<project name>``, so ``--out ..`` cleared the project
(#101).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ux_dom.cli import static_assets
from ux_dom.cli.build import run_build
from ux_dom.cli.cli import app


@pytest.mark.parametrize(
    "option", [["--package"], ["-p"], ["--archive"], ["--out", "x"], ["--name", "x"]]
)
def test_bundle_options_are_unknown(option: list[str]):
    result = CliRunner().invoke(app, ["build", *option])
    assert result.exit_code == 2, result.output
    assert "No such option" in result.output


@pytest.mark.parametrize(
    "kwarg",
    [{"package": True}, {"archive": True}, {"out_dir": Path("x")}, {"package_name": "x"}],
)
def test_run_build_takes_no_bundle_parameters(kwarg: dict):
    with pytest.raises(TypeError):
        run_build(**kwarg)


@pytest.mark.parametrize("name", ["write_runnable_package", "collect_package_files"])
def test_bundle_writers_are_gone(name: str):
    assert not hasattr(static_assets, name)


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
