"""ADR 0003 rule 4 absence lock: uxdom doctor checks no product rows.

Rule 3 scope: no port, ``DEBUG``, ``.env`` or scaffold marker. Product readiness is
``uxcompose doctor --prod [--port N]`` (ux-compose #128); scaffolding is
``uxcompose create-app``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from helpers import ScaffoldOptions, create_app
from ux_dom.cli.cli import app
from ux_dom.cli.doctor import run_doctor


@pytest.fixture
def debug_app(tmp_path: Path) -> Path:
    root = create_app(
        ScaffoldOptions("pr", dest=tmp_path / "pr", force=True, with_tailwind=False)
    )
    (root / "app" / "settings.py").write_text("DEBUG = True\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("option", [["--prod"], ["--port", "8080"]])
def test_product_options_are_unknown(option: list[str]):
    result = CliRunner().invoke(app, ["doctor", *option])
    assert result.exit_code == 2, result.output
    assert "No such option" in result.output


@pytest.mark.parametrize("kwarg", [{"prod": True}, {"port": 8080}])
def test_run_doctor_takes_no_product_parameters(kwarg: dict):
    with pytest.raises(TypeError):
        run_doctor(**kwarg)


def test_doctor_reports_no_product_rows(debug_app: Path):
    (debug_app / ".env").write_text("SECRET=x\n", encoding="utf-8")
    names = {c.name for c in run_doctor(cwd=debug_app).checks}
    assert not {n for n in names if n.startswith(("port:", "prod:"))}, names


def test_doctor_reads_no_scaffold_marker(debug_app: Path, tmp_path: Path):
    marker = '{"template": "x", "with_channel": true}'
    (debug_app / ".ux_dom-scaffold.json").write_text(marker, encoding="utf-8")
    names = {c.name for c in run_doctor(cwd=debug_app).checks}
    assert not names & {"scaffold", "product-scaffold"}, names

    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / ".ux_dom-scaffold.json").write_text(marker, encoding="utf-8")
    assert run_doctor(cwd=bare).project_root is None

