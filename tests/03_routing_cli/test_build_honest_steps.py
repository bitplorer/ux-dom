"""uxdom build reports only checks that can fail, and surfaces sync errors."""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers import ScaffoldOptions, create_app
from ux_dom.cli import static_assets
from ux_dom.cli.build import run_build
from ux_dom.plugins.hub import PluginHub, get_hub, set_hub
from ux_dom.plugins.runtime import XElementRuntime


class _BrokenStaticHub(PluginHub):
    def served_static_files(self) -> list:
        raise RuntimeError("bad static mount")


@pytest.fixture
def app_root(tmp_path: Path) -> Path:
    return create_app(
        ScaffoldOptions("hb", dest=tmp_path / "hb", force=True, with_tailwind=False)
    )


@pytest.fixture
def broken_hub():
    hub = _BrokenStaticHub()
    hub.add_contribution(XElementRuntime())
    previous = get_hub()
    set_hub(hub)
    yield hub
    set_hub(previous)


def test_build_has_no_hard_coded_green_steps(app_root: Path):
    rep = run_build(cwd=app_root, skip_import=True)
    names = {s.name for s in rep.steps}
    assert not names & {"assets-mount", "css", "css-artifacts"}, names


def test_sync_error_makes_sync_report_not_ok(app_root: Path, broken_hub):
    rep = static_assets.sync_runtime_assets(app_root, hub=broken_hub)
    assert rep.ok is False
    assert any("bad static mount" in e for e in rep.errors)


def test_sync_error_fails_the_build(app_root: Path, broken_hub):
    rep = run_build(cwd=app_root, skip_import=True)
    step = next(s for s in rep.steps if s.name == "static-sync")
    assert step.ok is False
    assert "bad static mount" in step.detail
    assert rep.ok is False


def test_package_build_syncs_once(app_root: Path, tmp_path: Path, monkeypatch):
    calls = []
    real = static_assets.sync_runtime_assets

    def counting(*a, **kw):
        calls.append(a)
        return real(*a, **kw)

    monkeypatch.setattr(static_assets, "sync_runtime_assets", counting)
    rep = run_build(
        cwd=app_root,
        skip_import=True,
        package=True,
        out_dir=tmp_path / "dist-out",
        package_name="hb",
    )
    assert rep.ok, rep.to_dict()
    assert len(calls) == 1
