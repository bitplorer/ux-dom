"""ADR 0004 absence lock: the uxdom CLI has one name per thing.

``uxdom info`` (an alias of ``uxdom doctor``), the ``ux_dom`` second name for the Typer
app and the ``open_hint`` / ``flamegraph_hint`` profile names are gone.
"""

from __future__ import annotations

import inspect

import pytest
from typer.main import get_command
from typer.testing import CliRunner

import ux_dom.cli
import ux_dom.cli.cli
from ux_dom.cli.cli import app
from ux_dom.cli.profile import format_profile_report, run_profile


def test_info_is_no_such_command():
    result = CliRunner().invoke(app, ["info"])
    assert result.exit_code == 2, result.output
    assert "No such command 'info'" in result.output
    assert "info" not in get_command(app).commands


@pytest.mark.parametrize("module", [ux_dom.cli, ux_dom.cli.cli])
def test_app_has_one_name(module):
    assert not hasattr(module, "ux_dom")
    assert not hasattr(module, "ux_dom_logger")
    assert "ux_dom" not in getattr(module, "__all__", ())


def test_profile_has_no_open_hint():
    assert "open_hint" not in inspect.signature(run_profile).parameters


def test_profile_hint_is_named_for_speedscope():
    text = format_profile_report({"speedscope_hint": "see speedscope"})
    assert "see speedscope" in text
    assert "flamegraph_hint" not in inspect.getsource(run_profile)
