# Copyright (c) 2023–2026 UX-DOM
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""uxdom CLI — pure Document / render tooling only.

Product lifecycle (create-app · build · serve · deploy) lives on **uxcompose** only.
See docs/internals/SYSTEM.md, docs/guides/CLI.md and ux-compose FLOW:
https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md

XElement is served from the installed package at ``/ux-dom/static/x_element.js``
(no app copy).
"""
from pathlib import Path

from typer import Option, Typer, echo

app = Typer(
    help=(
        "uxdom — pure Document/render tooling. "
        "Product lifecycle: uxcompose. "
        "XElement URL: /ux-dom/static/x_element.js"
    ),
    no_args_is_help=True,
)


@app.command("doctor")
def doctor_cmd(
    path: str = Option(None, "--path"),
    json_out: bool = Option(False, "--json"),
):
    """Document / package / env health (pure-dom)."""
    import json as _json

    from ux_dom.cli.doctor import format_report, run_doctor

    report = run_doctor(cwd=Path(path) if path else None)
    if json_out:
        print(_json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))
    raise SystemExit(0 if report.ok else 1)


@app.command("lint")
def lint_cmd(path: str = Option(None, "--path")):
    """Document convention checks."""
    from ux_dom.cli.lint import lint_project

    issues = lint_project(Path(path) if path else None)
    errors = [i for i in issues if i.level == "error"]
    if not issues:
        echo("lint: clean")
        raise SystemExit(0)
    for i in issues:
        echo(f"[{i.level}] {i.path}: {i.message}")
    raise SystemExit(1 if errors else 0)


@app.command("profile")
def profile_cmd(
    out: Path = Option(None, "--out"),
    rounds: int = Option(60, "--rounds"),
    warmup: int = Option(6, "--warmup"),
    profile_rounds: int = Option(30, "--profile-rounds"),
    json_out: bool = Option(False, "--json"),
):
    """Render p95 / self-time profile (pure-dom)."""
    from ux_dom.cli.profile import format_profile_report, run_profile

    report = run_profile(
        out=out, rounds=rounds, warmup=warmup, profile_rounds=profile_rounds
    )
    if json_out:
        import json as _json

        print(_json.dumps(report, indent=2))
    else:
        print(format_profile_report(report))


@app.command("dashboard")
def dashboard_cmd(
    out: Path = Option(None, "--out"),
    rounds: int = Option(40, "--rounds"),
    warmup: int = Option(4, "--warmup"),
    profile_rounds: int = Option(15, "--profile-rounds"),
):
    """Render DX dashboard."""
    from ux_dom.cli.dashboard import run_dashboard

    report = run_dashboard(
        out=out, rounds=rounds, warmup=warmup, profile_rounds=profile_rounds
    )
    print("uxdom dashboard")
    print(f"open: {report.get('dashboard_html')}")


@app.command("add")
def add_cmd(
    kind: str,
    name: str,
    xkind: str = Option("light", "--xe-kind"),
    force: bool = Option(False, "--force"),
):
    """Add component | xelement | ui. Page routes live on ux-compose."""
    from ux_dom.cli.adders import AddError, add_component, add_xelement

    kind = kind.lower().strip()
    try:
        if kind == "component":
            path = add_component(name, force=force)
        elif kind in ("xelement", "xe", "x-element"):
            if xkind not in ("light", "shadow", "alpine"):
                echo("--xe-kind must be light|shadow|alpine", err=True)
                raise SystemExit(2)
            path = add_xelement(name, kind=xkind, force=force)  # type: ignore[arg-type]
        elif kind == "ui":
            from ux_dom.ui.copy import UiCopyError, copy_component

            dest = Path.cwd() / "app" / "components" / "ui"
            try:
                path = copy_component(name, dest_dir=dest, force=force)
            except UiCopyError as e:
                echo(str(e), err=True)
                raise SystemExit(1) from e
        else:
            echo("kind must be component|xelement|ui", err=True)
            raise SystemExit(2)
    except AddError as e:
        echo(str(e), err=True)
        raise SystemExit(1) from e
    echo(f"wrote {path}")


@app.command("ui")
def ui_cmd(
    channel: bool = Option(False, "--channel"),
):
    """List UI kit components."""
    from ux_dom.ui.catalog import list_components

    items = list_components(channel=True if channel else None)
    for it in items:
        ch = " [channel]" if it.get("channel") else ""
        echo(f"  · {it['name']:<16} {it['description']}{ch}")


if __name__ == "__main__":
    app()
