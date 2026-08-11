# Copyright (c) 2023–2026 UX-DOM
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


# import black
"""uxdom CLI super-command for **ux-dom**.

Brand lines
-----------
| Layer | Name |
|-------|------|
| **PyPI / pip** | ``ux-dom`` |
| **Import** | ``ux_dom`` |
| **CLI** | ``uxdom`` |

Console entry: ``uxdom <subcommand>`` · ``python -m ux_dom``.

Side-effect policy:
* Read-only: templates, examples, ui, plugins, doctor, lint
* profile: writes only under reports/p95/ (or --out); no app source changes
* dashboard: writes reports/dx/ (graphs); no app source changes
* create-app: --yes skips confirm only; overwrite requires --force
* add/deploy: refuse overwrite without --force
* dev: does not dual-copy x_element.js; --tailwind may write CSS
* build: single-copy verify; dist only with --package/--archive

See docs/guides/CLI.md and docs/internals/DESIGN_CANON.md section 8.
"""
from pathlib import Path
from string import Template

from typer import Option, Typer

from ux_dom import WebAssets
from ux_dom.utils.logger import ux_dom_logger
from ux_dom.cli.scaffold import (
    ScaffoldOptions,
    available_templates,
    create_app as scaffold_create,
)

app = Typer(
    help="uxdom — CLI for ux-dom 0.1 (PyPI: ux-dom · import: ux_dom)",
    no_args_is_help=True,
)


class _Template(Template):
    delimiter = "$variable::"


INDEX_TEMP = _Template("""
from ux_dom.dom import *
from $variable::app_name.document import document

class Index(Component):
    def render(self, *args, **kwargs):
        return document(div(*args, **kwargs))
""")

FASTAPI_INDEX_TEMP = _Template("""
from ux_dom.dom import *
from $variable::app_name.api import api
from $variable::app_name.document import document

class Index(Component):
    def render(self, *args, **kwargs):
        return document(*args, **kwargs)

@api.get("/")
def index():
    return Index(div("Hello World"))
    """)


API_TEMP = _Template("""
from $variable::app_name.index import Index

async def home(scope, receive, send):
    assert scope["type"] == "http"
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html"],
            ],
        }
    )
    await send({"type": "http.response.body", "body": str(Index("Hello, world!")).encode()})
    """)

FASTAPI_API_TEMP = _Template("""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from ux_dom.routing.fastapi import DirectoryRouter, HTMLRoute, StreamingRoute

from $variable::app_name import settings


@asynccontextmanager
async def lifespan(api: FastAPI):
    if settings.DEBUG:
        # adding browser reloading
        api.add_websocket_route(
            path=settings.hot_reload_route.url_path,
            route=settings.hot_reload_route,
            name=settings.hot_reload_route.url_name,
        )
    if settings.DEBUG:
        await settings.hot_reload_route.startup()
    yield
    if settings.DEBUG:
        await settings.hot_reload_route.shutdown()


api = FastAPI(
    debug=settings.DEBUG,
    default_response_class=HTMLResponse,
    title="$variable::app_name",
    lifespan=lifespan,
)
api.router.route_class = StreamingRoute
app_router = DirectoryRouter(package_dir=Path(__file__).resolve().parent)
api.include_router(app_router)

# In older versions of FastAPI we can use hot reloader as follows
# 
# if settings.DEBUG:
#     # adding browser reloading
#     api.add_websocket_route(
#         path=settings.hot_reload_route.url_path,
#         route=settings.hot_reload_route,
#         name=settings.hot_reload_route.url_name,
#     )
#     api.add_event_handler("startup", settings.hot_reload_route.startup)
#     api.add_event_handler("shutdown", settings.hot_reload_route.shutdown)

api.mount(
    "/css",
    StaticFiles(directory=settings.webassets.static.css, check_dir=False),
    name="css",
)
api.mount(
    "/js",
    StaticFiles(directory=settings.webassets.static.js, check_dir=False),
    name="js",
)
api.mount(
    "/image",
    StaticFiles(directory=settings.webassets.static.image, check_dir=False),
    name="image",
)
api.mount(
    "/font",
    StaticFiles(directory=settings.webassets.static.font, check_dir=False),
    name="font",
)
    """)


FASTAPI_ROUTES_TEMP = _Template("""
from $variable::app_name.index import api
    """)

SERVER_TEMP = _Template("""
HAS_UVICORN = True
 
try:
    import uvicorn
except ImportError:
    pass
    HAS_UVICORN = False
    
if __name__ == "__main__":
    if HAS_UVICORN:
        uvicorn.run(
            "$variable::app_name.api:home",
            host="127.0.0.1",
            port=8081,
            reload=True,
            # ssl_keyfile='../$variable::app_name/key.pem',
            # ssl_certfile='../$variable::app_name/cert.pem'
        )
    """)


FASTAPI_SERVER_TEMP = _Template("""
HAS_UVICORN = True
 
try:
    import uvicorn
except ImportError:
    pass
    HAS_UVICORN = False
    
if __name__ == "__main__":
    if HAS_UVICORN:
        uvicorn.run(
            "$variable::app_name.routes:api",
            host="127.0.0.1",
            port=8081,
            reload=True,
            # ssl_keyfile='../$variable::app_name/key.pem',
            # ssl_certfile='../$variable::app_name/cert.pem'
        )
    """)


DOCUMENT_TEMP = _Template("""
from ux_dom import Document
from ux_dom.dom import link, raw, uniqueid, meta, script
from ux_dom.scripts import x_element_js
from $variable::app_name import settings
from $variable::app_name.tailwindcss import tailwind

__all__ = ["document"]


document = Document(
    webassets=settings.webassets,
    head=[
        meta(http_equiv="cache-control", content="no-cache") if settings.DEBUG else "",
        meta(http_equiv="expires", content="0") if settings.DEBUG else "",
        meta(http_equiv="pragma", content="no-cache") if settings.DEBUG else "",
        link(href=f"/css/{tailwind.output_css}?v={uniqueid()}", rel="stylesheet"),
    ],
    body=[
        script(
            src=f"/js/{x_element_js().save(file_or_dir=settings.webassets.static.js)}"
        ),
        raw(settings.hot_reload_route.script() if settings.DEBUG and settings.HAS_WEB_SOCK else ""),
    ],
)
""")

SETTINGS_TEMP = _Template("""
from ux_dom import WebAssets
from pathlib import Path

HAS_WEB_SOCK = True

try:
    from fastapi.websockets import WebSocket
except ImportError:
    from ux_dom.web_io import WebSocketProtocol

    class WebSocket(WebSocketProtocol):  # type: ignore
        # this WebSocket is just a placeholder, install websockets, FastAPI or
        # any other library that supports Websocket to actually import it.
        pass
        
    HAS_WEB_SOCK = False
    
BASE_DIR = Path(__file__).parent
DEBUG = True
webassets = WebAssets(base_dir=BASE_DIR, sub_dir="$variable::asset_dir", dry_run=not DEBUG)


if DEBUG:
    from ux_dom import reloader

    # hot reloading via websocket instance

    async def tailwind_watcher():
        from $variable::app_name.tailwindcss import tailwind

        await tailwind.async_run()

    hot_reload_route = reloader.HotReloadWebSocketRoute(
        websocket_type=WebSocket,
        watch_paths=[
            reloader.WatchPath("./$variable::app_name", on_reload=[tailwind_watcher]),
        ],
        url_path="/hot-reload",
        url_name="hot_reload",
        reconnect_interval=1,
    )
""")

TAILWIND_TEMP = _Template("""
from $variable::app_name import settings
from ux_dom import TailwindCommand

tailwind = TailwindCommand(
    file_path=__file__,
    webassets=settings.webassets,
    # input_css=settings.INPUT_CSS_FILE,
    # output_css=settings.OUTPUT_CSS_FILE,
    minify=not settings.DEBUG,
)

if __name__ == "__main__":
    tailwind.run()
""")


@app.command("create-app")
def create_app_cmd(
    app_name: str,
    template: str = Option(
        "minimal", "--template", "-t", help="minimal | shop | live | tutorial"
    ),
    dest: str = Option(
        None, "--dest", "-d", help="Target directory (default: ./APP_NAME)"
    ),
    no_tailwind: bool = Option(False, "--no-tailwind"),
    channel: bool = Option(False, "--channel", help="Include ux-channel"),
    no_hmr: bool = Option(False, "--no-hmr"),
    no_csp: bool = Option(
        False, "--no-csp", help="Skip CSP middleware (not recommended)."
    ),
    force: bool = Option(False, "--force", help="Overwrite existing scaffold files in dest"),
    yes: bool = Option(False, "--yes", "-y", help="Skip confirmation (does not overwrite; use --force to overwrite)"),
):
    """Scaffold a new uxdom app (Vue/CRA-style).

    Examples::

        uxdom create-app myapp
        uxdom create-app myapp --template shop
        uxdom create-app myapp --template live
        uxdom create-app myapp --channel --dest ./apps/myapp
        uxdom create-app myapp --no-tailwind
        uxdom create-app myapp --no-csp
    """
    from pathlib import Path as P
    import sys

    if template not in available_templates():
        ux_dom_logger.error(
            f"unknown template {template!r}; choose from {available_templates()}"
        )
        raise SystemExit(2)

    target = P(dest).resolve() if dest else (P.cwd() / app_name)
    # Intent gates:
    # * Interactive: confirm unless --yes / --force
    # * Non-interactive (CI/scripts): require --yes or --force (no silent create)
    # * Overwrite non-empty dest: only --force (NOT --yes alone)
    if not yes and not force:
        if sys.stdin.isatty():
            ans = input(f"Create app {app_name!r} at {target}? [y/N] ").strip().lower()
            if ans not in ("y", "yes"):
                ux_dom_logger.info("cancelled")
                raise SystemExit(0)
        else:
            ux_dom_logger.error(
                "non-interactive create-app requires --yes "
                "(add --force only if overwriting an existing tree)"
            )
            raise SystemExit(2)

    opts = ScaffoldOptions(
        app_name=app_name,
        dest=target,
        template=template,
        with_tailwind=not no_tailwind,
        with_channel=channel or template == "live",
        with_hmr=not no_hmr,
        with_csp=not no_csp,
        force=force,  # never implied by --yes
    )
    try:
        root = scaffold_create(opts)
    except FileExistsError as e:
        ux_dom_logger.error(str(e))
        raise SystemExit(1) from e

    ux_dom_logger.info(f"created {root}")
    ux_dom_logger.info("next:")
    ux_dom_logger.info(f"  cd {root}")
    ux_dom_logger.info("  pip install -r requirements.txt")
    if opts.with_channel:
        ux_dom_logger.info("  pip install 'ux-channel>=0.1.0'")
    ux_dom_logger.info("  uxdom doctor")
    ux_dom_logger.info("  uxdom dev app.main:app --port 8080")
    ux_dom_logger.info("  # see QUICKSTART.md / docs/TUTORIAL.md")


@app.command("templates")
def list_templates():
    """List create-app templates."""
    for name in available_templates():
        ux_dom_logger.info(name)




@app.command()
def dev(
    app_import: str = Option(
        "app.main:app",
        help="ASGI import path module:attr (create-app default: app.main:app)",
    ),
    host: str = Option("0.0.0.0", "--host"),
    port: int = Option(8080, "--port"),
    no_reload: bool = Option(False, "--no-reload"),
    tailwind: bool = Option(
        False,
        "--tailwind",
        help="Also run `python -m app.tailwindcss` once before start (if present)",
    ),
):
    """Run a uxdom ASGI app (uvicorn) — day-1 local server.

    Examples::

        cd myapp && uxdom dev
        uxdom dev app.main:app --port 8080
        uxdom dev --no-reload
        uxdom dev --tailwind
    """
    try:
        import uvicorn
    except ImportError as e:
        ux_dom_logger.error(
            "uvicorn is required for `uxdom dev`. "
            "Install with: pip install 'ux-dom[fastapi]'"
        )
        raise SystemExit(1) from e

    if tailwind:
        import subprocess
        import sys
        from pathlib import Path as P

        tw = P("app/tailwindcss.py")
        if tw.is_file():
            ux_dom_logger.info("building Tailwind via app.tailwindcss …")
            subprocess.run([sys.executable, "-m", "app.tailwindcss"], check=False)
        else:
            ux_dom_logger.warning("no app/tailwindcss.py — skip --tailwind")

    reload = not no_reload
    # Ensure project root is importable (create-app layout: app.main:app)
    import os
    from pathlib import Path as _P

    cwd = str(_P.cwd().resolve())
    os.environ["PYTHONPATH"] = (
        cwd + os.pathsep + os.environ["PYTHONPATH"]
        if os.environ.get("PYTHONPATH")
        else cwd
    )
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    ux_dom_logger.info(f"starting {app_import} on {host}:{port} reload={reload}")
    ux_dom_logger.info("tip: uxdom doctor · uxdom build · docs: QUICKSTART.md")
    uvicorn.run(app_import, host=host, port=port, reload=reload)


@app.command("doctor")
def doctor_cmd(
    port: int = Option(8080, "--port", help="Port to probe for availability"),
    prod: bool = Option(False, "--prod", help="Extra production checks"),
    json_out: bool = Option(False, "--json", help="Machine-readable report"),
):
    """Check Python, deps, x_element.js, and current project health."""
    import json as _json
    from ux_dom.cli.doctor import format_report, run_doctor

    report = run_doctor(port=port, prod=prod)
    if json_out:
        print(_json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))
    raise SystemExit(0 if report.ok else 1)




@app.command("dashboard")
def dashboard_cmd(
    out: Path = Option(None, "--out", help="Output directory (default: ./reports/dx)"),
    rounds: int = Option(40, "--rounds"),
    warmup: int = Option(4, "--warmup"),
    profile_rounds: int = Option(15, "--profile-rounds"),
):
    """First-class DX: render p95 graphs → reports/dx/dashboard.html."""
    from ux_dom.cli.dashboard import run_dashboard

    report = run_dashboard(
        out=out, rounds=rounds, warmup=warmup, profile_rounds=profile_rounds
    )
    print("uxdom dashboard")
    print("=" * 40)
    print("Brand lines")
    print("  PyPI / pip : ux-dom")
    print("  import     : ux_dom")
    print("  CLI        : uxdom")
    print("-" * 40)
    for lat in report.get("latencies") or []:
        print(f"  {lat['name']:<28} p95={lat['p95_ms']}")
    print("-" * 40)
    print(f"open: {report.get('dashboard_html')}")
    print("SVG graphs · no CDN · pair with uxchannel dashboard for control plane")
    print("=" * 40)


@app.command("profile")
def profile_cmd(
    out: Path = Option(
        None,
        "--out",
        help="Output directory (default: ./reports/p95)",
    ),
    rounds: int = Option(60, "--rounds", help="Latency samples per bench"),
    warmup: int = Option(6, "--warmup", help="Warmup iterations"),
    profile_rounds: int = Option(
        30, "--profile-rounds", help="cProfile / flamegraph iterations"
    ),
    json_out: bool = Option(False, "--json", help="Print latency JSON to stdout"),
):
    """First-class DX: p95 latency + flamegraph artifacts (reports/p95)."""
    from ux_dom.cli.profile import format_profile_report, run_profile

    report = run_profile(
        out=out,
        rounds=rounds,
        warmup=warmup,
        profile_rounds=profile_rounds,
    )
    if json_out:
        import json as _json

        print(_json.dumps(report, indent=2))
    else:
        print(format_profile_report(report))


@app.command("add")
def add_cmd(
    kind: str,
    name: str,
    xkind: str = Option(
        "light", "--xe-kind", help="For xelement: light | shadow | alpine"
    ),
    force: bool = Option(False, "--force", help="Overwrite existing generated file"),
    methods: str = Option("get", "--methods", help="Comma HTTP methods for routes"),
):
    """Generate a component, DirectoryRouter route, or XElement stub.

    Examples::

        uxdom add component Card
        uxdom add route settings
        uxdom add route users/[id]
        uxdom add xelement Badge --xe-kind shadow
        uxdom add ui Button
        uxdom add ui Card
    """
    from ux_dom.cli.adders import AddError, add_component, add_route, add_xelement

    kind = kind.lower().strip()
    try:
        if kind == "component":
            path = add_component(name, force=force)
        elif kind == "route":
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


@app.command("lint")
def lint_cmd(
    path: str = Option(None, "--path", help="Project root (default: cwd)"),
):
    """Static convention checks (XElement attrs, document runtime, routes)."""
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


@app.command("examples")
def examples_cmd(
    list_only: bool = Option(True, "--list", help="List bundled example apps"),
):
    """List production example apps shipped with this source tree."""
    from pathlib import Path as P

    # installed package: parents[1] is ux_dom; examples live at repo root
    candidates = [
        P(__file__).resolve().parents[2] / "examples",
        P.cwd() / "examples",
    ]
    ex = next((c for c in candidates if c.is_dir()), None)
    if ex is None:
        ux_dom_logger.info("examples/ not found (install from source/zip for demos)")
        raise SystemExit(0)
    ux_dom_logger.info(f"examples under {ex}")
    for child in sorted(ex.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            readme = child / "README.md"
            blurb = ""
            if readme.is_file():
                line = readme.read_text(encoding="utf-8").splitlines()
                blurb = next(
                    (L for L in line if L.strip() and not L.startswith("#")), ""
                )[:80]
            ux_dom_logger.info(f"  · {child.name}/  {blurb}")
    ux_dom_logger.info(
        "run e.g. PYTHONPATH=.:examples/xelement_kit uvicorn app.main:app --app-dir examples/xelement_kit"
    )


@app.command("build")
def build_cmd(
    skip_tailwind: bool = Option(False, "--skip-tailwind"),
    skip_import: bool = Option(False, "--skip-import"),
    skip_static_sync: bool = Option(
        False,
        "--skip-static-sync",
        help="Do not re-copy x_element.js from the ux_dom package",
    ),
    package: bool = Option(
        False,
        "--package",
        "-p",
        help="Write runnable tree to dist/<name>/ (app + assets + run.sh)",
    ),
    archive: bool = Option(
        False,
        "--archive",
        help="Also/write dist/<name>.tar.gz (implies --package)",
    ),
    out_dir: str = Option(
        None,
        "--out",
        help="Package output directory (default: ./dist)",
    ),
    name: str = Option(None, "--name", help="Package folder/archive name"),
    json_out: bool = Option(False, "--json"),
):
    """Production build: sync static JS, Tailwind, import check, optional package.

    Static JS model: x_element.js is copied from the installed ux_dom package into
    assets/js/ and served at /assets/js/x_element.js (see docs/ASSETS.md).

    Examples::

        uxdom build
        uxdom build --package
        uxdom build --archive --name myapp
        uxdom build --skip-tailwind --package --out /tmp/dist
    """
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


@app.command("deploy")
def deploy_cmd(
    provider: str = Option(
        "docker",
        "--provider",
        "-p",
        help="docker | fly | render | railway | vps | checklist",
    ),
    force: bool = Option(False, "--force", help="Overwrite existing deploy files"),
    app_name: str = Option(None, "--name", help="Service/app name override"),
    json_out: bool = Option(False, "--json"),
):
    """Prepare deploy configs (does not upload). Run `uxdom build` first.

    Examples::

        uxdom deploy --provider docker
        uxdom deploy -p fly --name my-ux_dom-app
        uxdom deploy -p checklist
        uxdom deploy -p vps --force
    """
    import json as _json
    from ux_dom.cli.deploy import format_deploy_result, prepare_deploy

    provider = provider.lower().strip()
    allowed = {"docker", "fly", "render", "railway", "vps", "checklist"}
    if provider not in allowed:
        ux_dom_logger.error(f"provider must be one of {sorted(allowed)}")
        raise SystemExit(2)
    try:
        result = prepare_deploy(
            provider,  # type: ignore[arg-type]
            force=force,
            app_name=app_name,
        )
    except FileNotFoundError as e:
        ux_dom_logger.error(str(e))
        raise SystemExit(1) from e
    if json_out:
        print(_json.dumps(result.to_dict(), indent=2))
    else:
        print(format_deploy_result(result))
    raise SystemExit(0)


@app.command("ui")
def ui_cmd(
    action: str = Option("list", help="list | docs"),
    channel: bool = Option(False, "--channel", help="Only show channel-bridge entries"),
):
    """List shadcn-style uxdom UI kit components (optional; pure Tailwind).

    Install/copy into your app::

        uxdom add ui Button
        uxdom add ui Card --force

    Live morph (optional)::

        from ux_dom.ui.channel_bridge import stamp_region, live_button
    """
    from ux_dom.ui.catalog import list_components

    if action not in ("list", "docs"):
        ux_dom_logger.error("action must be list|docs")
        raise SystemExit(2)
    items = list_components(channel=True if channel else None)
    if channel:
        items = list_components(channel=True)
    else:
        items = list_components()
    ux_dom_logger.info(
        "ux-dom UI kit (import from ux_dom.ui or copy with: uxdom add ui NAME)"
    )
    for it in items:
        ch = " [channel]" if it["channel"] else ""
        ux_dom_logger.info(f"  · {it['name']:<16} {it['description']}{ch}")
    ux_dom_logger.info("docs: docs/UI.md")


@app.command()
def plugins():
    """List registered plugins on the default hub (if any were used)."""
    from ux_dom.plugins import get_hub

    summary = get_hub().summary()
    if not summary:
        ux_dom_logger.info("no plugins registered on default hub")
    else:
        for line in summary:
            ux_dom_logger.info(line)


ux_dom = app  # Typer app export (import path stability)
# console_scripts: uxdom = ux_dom.cli:app

if __name__ == "__main__":
    app()  # pragma: no cover
    # cli(uicli, *sys.argv[1:])
