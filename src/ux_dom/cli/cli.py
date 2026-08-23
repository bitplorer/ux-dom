# Copyright (c) 2023–2026 UX-DOM
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""uxdom CLI — pure Document / render tooling only.

Product lifecycle (create-app · serve · deploy) lives on **uxcompose** only.
See docs/internals/SYSTEM.md and ux-compose docs/FLOW.md / docs/CLI.md.
"""
from pathlib import Path

from typer import Option, Typer

from ux_dom.utils.logger import ux_dom_logger

app = Typer(
    help=(
        "uxdom — pure Document/render tooling. "
        "Product apps: uxcompose create-app | serve | deploy"
    ),
    no_args_is_help=True,
)


@app.command("doctor")
def doctor_cmd(
    path: str = Option(None, "--path"),
    port: int = Option(8080, "--port"),
    prod: bool = Option(False, "--prod"),
    json_out: bool = Option(False, "--json"),
):
    """Document / package / env health (pure-dom)."""
    import json as _json
    from pathlib import Path as P

    from ux_dom.cli.doctor import format_report, run_doctor

    report = run_doctor(cwd=P(path) if path else None, port=port, prod=prod)
    if json_out:
        print(_json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))
    raise SystemExit(0 if report.ok else 1)


@app.command("info")
def info_cmd(
    path: str = Option(None, "--path"),
    port: int = Option(8080, "--port"),
    prod: bool = Option(False, "--prod"),
    json_out: bool = Option(False, "--json"),
):
    """Alias of doctor."""
    doctor_cmd(path=path, port=port, prod=prod, json_out=json_out)


@app.command("lint")
def lint_cmd(path: str = Option(None, "--path")):
    """Document convention checks."""
    from pathlib import Path as P
    from ux_dom.cli.lint import lint_project

    issues = lint_project(P(path) if path else None)
    errors = [i for i in issues if i.level == "error"]
    if not issues:
        ux_dom_logger.info("lint: clean")
        raise SystemExit(0)
    for i in issues:
        ux_dom_logger.info(f"[{i.level}] {i.path}: {i.message}")
    raise SystemExit(1 if errors else 0)


@app.command("build")
def build_cmd(
    skip_tailwind: bool = Option(False, "--skip-tailwind"),
    skip_import: bool = Option(False, "--skip-import"),
    skip_static_sync: bool = Option(False, "--skip-static-sync"),
    package: bool = Option(False, "--package", "-p"),
    archive: bool = Option(False, "--archive"),
    out_dir: str = Option(None, "--out"),
    name: str = Option(None, "--name"),
    json_out: bool = Option(False, "--json"),
):
    """Tailwind / static verify for Document trees."""
    import json as _json
    from pathlib import Path as _P

    from ux_dom.cli.build import format_build_report, run_build

    try:
        report = run_build(
            skip_tailwind=skip_tailwind,
            skip_import=skip_import,
            skip_static_sync=skip_static_sync,
            package=package or archive,
            archive=archive,
            out_dir=_P(out_dir) if out_dir else None,
            package_name=name,
        )
    except FileNotFoundError as e:
        ux_dom_logger.error(str(e))
        raise SystemExit(1) from e
    if json_out:
        print(_json.dumps(report.to_dict(), indent=2))
    else:
        print(format_build_report(report))
    raise SystemExit(0 if report.ok else 1)


@app.command("profile")
def profile_cmd(
    out: Path = Option(None, "--out"),
    rounds: int = Option(60, "--rounds"),
    warmup: int = Option(6, "--warmup"),
    profile_rounds: int = Option(30, "--profile-rounds"),
    json_out: bool = Option(False, "--json"),
):
    """Render p95 / flamegraph (pure-dom)."""
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
    methods: str = Option("get", "--methods"),
):
    """Add component | xelement | ui. Product page units → ux-compose routes/."""
    from ux_dom.cli.adders import AddError, add_component, add_route, add_xelement

    kind = kind.lower().strip()
    try:
        if kind == "component":
            path = add_component(name, force=force)
        elif kind == "route":
            ux_dom_logger.info(
                "product page units prefer ux-compose routes/; "
                "writing a pure-dom DirectoryRoutes stub only"
            )
            path = add_route(name, force=force, methods=methods)
        elif kind in ("xelement", "xe", "x-element"):
            if xkind not in ("light", "shadow", "alpine"):
                ux_dom_logger.error("--xe-kind must be light|shadow|alpine")
                raise SystemExit(2)
            path = add_xelement(name, kind=xkind, force=force)  # type: ignore[arg-type]
        elif kind == "ui":
            from pathlib import Path as P
            from ux_dom.ui.copy import UiCopyError, copy_component

            dest = P.cwd() / "app" / "components" / "ui"
            try:
                path = copy_component(name, dest_dir=dest, force=force)
            except UiCopyError as e:
                ux_dom_logger.error(str(e))
                raise SystemExit(1) from e
        else:
            ux_dom_logger.error("kind must be component|route|xelement|ui")
            raise SystemExit(2)
    except AddError as e:
        ux_dom_logger.error(str(e))
        raise SystemExit(1) from e
    ux_dom_logger.info(f"wrote {path}")


@app.command("ui")
def ui_cmd(
    action: str = Option("list"),
    channel: bool = Option(False, "--channel"),
):
    """List UI kit components."""
    from ux_dom.ui.catalog import list_components

    items = list_components(channel=True if channel else None)
    for it in items:
        ch = " [channel]" if it.get("channel") else ""
        ux_dom_logger.info(f"  · {it['name']:<16} {it['description']}{ch}")


ux_dom = app

if __name__ == "__main__":
    app()
