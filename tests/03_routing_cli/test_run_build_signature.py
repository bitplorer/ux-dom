"""run_build has no parameters it cannot honour (no silent no-ops)."""

import inspect

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from ux_dom.cli.build import run_build
from ux_dom.cli.cli import app as cli_app


@pytest.mark.parametrize("name", ["minify", "skip_tailwind"])
def test_dead_parameters_are_gone(name):
    assert name not in inspect.signature(run_build).parameters


@pytest.mark.parametrize(
    "kw", [{"minify": True}, {"minify": False}, {"skip_tailwind": True}]
)
def test_passing_a_removed_parameter_is_a_type_error(kw, tmp_path):
    with pytest.raises(TypeError):
        run_build(cwd=tmp_path, **kw)


def test_cli_build_has_no_skip_tailwind_option():
    build = get_command(cli_app).commands["build"]
    opts = {o for p in build.params for o in getattr(p, "opts", [])}
    assert "--skip-tailwind" not in opts
    result = CliRunner().invoke(cli_app, ["build", "--skip-tailwind"])
    assert result.exit_code != 0
