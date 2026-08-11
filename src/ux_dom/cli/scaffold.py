"""
Create-app scaffolder — Vue / CRA-style project generator for ux-dom.

    uxdom create-app myapp
    uxdom create-app myapp --template shop --with-channel
    uxdom create-app myapp --template live

Generates a runnable app with plugins, DirectoryRouter, Tailwind, optional
ux-channel, example routes, and production-oriented layout.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ux_dom.cli.scaffold_check import (
    assert_scaffold_ok,
    validate_scaffold,
)

__all__ = ["ScaffoldOptions", "create_app", "available_templates", "validate_scaffold"]


def available_templates() -> list[str]:
    return ["minimal", "shop", "live", "tutorial"]


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip())
    s = s.strip("_").lower() or "app"
    if s[0].isdigit():
        s = "app_" + s
    return s


@dataclass
class ScaffoldOptions:
    app_name: str
    dest: Optional[Path] = None
    template: str = "minimal"  # minimal | shop | live
    with_tailwind: bool = True
    with_channel: bool = False
    with_hmr: bool = True
    with_csp: bool = True  # Csp.auto() on document by default
    force: bool = False
    python: str = "3.14"

    def __post_init__(self) -> None:
        self.app_name = _slug(self.app_name)
        if self.template not in available_templates():
            raise ValueError(
                f"unknown template {self.template!r}; "
                f"choose from {available_templates()}"
            )
        if self.template == "live":
            self.with_channel = True
        if self.dest is None:
            self.dest = Path.cwd() / self.app_name
        else:
            self.dest = Path(self.dest).resolve()


def _write(path: Path, content: str, *, force: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return False
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")
    return True


def _sub(text: str, ctx: dict) -> str:
    out = text
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def create_app(opts: ScaffoldOptions) -> Path:
    """Materialize a new ux-dom app project. Returns project root."""
    root = opts.dest
    assert root is not None
    if root.exists() and any(root.iterdir()) and not opts.force:
        raise FileExistsError(
            f"{root} is not empty. Pass --force to overwrite scaffold files."
        )
    root.mkdir(parents=True, exist_ok=True)

    title = opts.app_name.replace("_", " ").title()
    channel_dep = "ux-channel>=0.1.0\n" if opts.with_channel else ""
    channel_install = (
        "pip install 'ux-channel>=0.1.0'  # or: pip install -e /path/to/ux-channel\n"
        if opts.with_channel
        else ""
    )
    tailwind_hint = (
        "# Tailwind: DEBUG builds via plugin; production:\n"
        "#   python -m app.tailwindcss\n"
        if opts.with_tailwind
        else ""
    )
    ctx = {
        "app_name": opts.app_name,
        "AppTitle": title,
        "python": opts.python,
        "secret_placeholder": f"{opts.app_name}-dev-secret-key-32chars-min!!",
        "template": opts.template,
        "channel_dep": channel_dep,
        "channel_install": channel_install,
        "tailwind_hint": tailwind_hint,
        "tailwind_status": "on" if opts.with_tailwind else "off",
        "hmr_status": "on (DEBUG)" if opts.with_hmr else "off",
        "channel_status": "on" if opts.with_channel else "off",
        "with_tailwind_bool": "True" if opts.with_tailwind else "False",
        "with_channel_bool": "True" if opts.with_channel else "False",
        "with_hmr_bool": "True" if opts.with_hmr else "False",
        "with_csp_bool": "True" if opts.with_csp else "False",
        "csp_status": "on (auto)" if opts.with_csp else "off",
    }

    # Template-specific nav / home links
    if opts.template == "shop":
        ctx["nav_extra"] = (
            'link("Shop", "/shop/Shop", "shop"),\n'
            '                    link("Cart", "/cart/Cart", "cart"),'
        )
        ctx["home_links"] = (
            'li(a("Shop catalog", href="/shop/Shop", className="text-sky-600 underline")),\n'
            '                li(a("Cart", href="/cart/Cart", className="text-sky-600 underline")),'
        )
        ctx["default_active_about"] = "shop"
    elif opts.template == "tutorial":
        ctx["nav_extra"] = (
            'link("HTMX", "/htmx_demo/HtmxDemo", "htmx"),\n'
            '                    link("XElement", "/xelement_demo/XelementDemo", "xe"),\n'
            '                    link("Recipes", "/recipes/Recipes", "recipes"),'
        )
        ctx["home_links"] = (
            'li(a("1. About (components)", href="/about/About", className="text-sky-600 underline")),\n'
            '                li(a("2. HTMX partial", href="/htmx_demo/HtmxDemo", className="text-sky-600 underline")),\n'
            '                li(a("3. XElement light DOM", href="/xelement_demo/XelementDemo", className="text-sky-600 underline")),\n'
            '                li(a("4. Recipes", href="/recipes/Recipes", className="text-sky-600 underline")),'
        )
        ctx["default_active_about"] = "about"
    elif opts.template == "live":
        ctx["nav_extra"] = 'link("Live", "/live/Live", "live"),'
        ctx["home_links"] = (
            'li(a("Live counter", href="/live/Live", className="text-sky-600 underline")),'
        )
        ctx["default_active_about"] = "live"
    else:
        ctx["nav_extra"] = 'link("About", "/about/About", "about"),'
        ctx["home_links"] = (
            'li(a("About", href="/about/About", className="text-sky-600 underline")),'
        )
        if opts.with_channel:
            ctx[
                "nav_extra"
            ] += '\n                    link("Channel", "/channel_demo/ChannelDemo", "channel"),'
            ctx["home_links"] += (
                '\n                li(a("Channel demo", href="/channel_demo/ChannelDemo", '
                'className="text-sky-600 underline")),'
            )
        ctx["default_active_about"] = "about"

    files: dict[str, str] = {
        ".gitignore": _GITIGNORE,
        ".env.example": _sub(_ENV_EXAMPLE, ctx),
        "requirements.txt": _sub(_REQUIREMENTS, ctx),
        "pyproject.toml": _sub(_PYPROJECT, ctx),
        "README.md": _sub(_README, ctx),
        "app/__init__.py": f'"""{opts.app_name} application package."""\n',
        "app/settings.py": _sub(_SETTINGS, ctx),
        "app/document.py": _sub(_DOCUMENT, ctx),
        "app/main.py": _sub(_MAIN, ctx),
        "app/components/__init__.py": '"""Shared UI components."""\n',
        "app/components/layout.py": _sub(_LAYOUT, ctx),
        "app/routes/__init__.py": '"""File-based routes for DirectoryRouter."""\n',
        "app/routes/index.py": _sub(_ROUTE_INDEX, ctx),
    }

    if opts.template == "shop":
        files["app/routes/shop.py"] = _sub(_ROUTE_SHOP, ctx)
        files["app/routes/cart.py"] = _sub(_ROUTE_CART, ctx)
    elif opts.template == "live":
        files["app/channel_app.py"] = _sub(_CHANNEL_APP, ctx)
        files["app/routes/live.py"] = _sub(_ROUTE_LIVE, ctx)
    elif opts.template == "tutorial":
        files["app/routes/about.py"] = _sub(_ROUTE_ABOUT, ctx)
        files["app/routes/htmx_demo.py"] = _sub(_ROUTE_TUTORIAL_HTMX, ctx)
        files["app/routes/xelement_demo.py"] = _sub(_ROUTE_TUTORIAL_XELEMENT, ctx)
        files["app/components/x_hello.py"] = _sub(_COMPONENT_TUTORIAL_XHELLO, ctx)
        files["app/routes/recipes.py"] = _sub(_ROUTE_TUTORIAL_RECIPES, ctx)
    else:
        files["app/routes/about.py"] = _sub(_ROUTE_ABOUT, ctx)
        if opts.with_channel:
            files["app/channel_app.py"] = _sub(_CHANNEL_APP_MINIMAL, ctx)
            files["app/routes/channel_demo.py"] = _sub(_ROUTE_CHANNEL_DEMO, ctx)

    # XElement JS is served from installed ux_dom package (single copy):
    #   GET /ux-dom/static/x_element.js  via XElementRuntime mount
    # Do NOT copy into assets/ — dual copies skew after pip upgrade.

    if opts.with_tailwind:
        files["assets/css/input.css"] = _INPUT_CSS
        files["tailwind.config.js"] = _TAILWIND_CONFIG
        files["app/tailwindcss.py"] = _sub(_TAILWIND_RUNNER, ctx)

    files[".ux_dom-scaffold.json"] = json.dumps(
        {
            "app_name": opts.app_name,
            "template": opts.template,
            "with_tailwind": opts.with_tailwind,
            "with_channel": opts.with_channel,
            "with_hmr": opts.with_hmr,
            "with_csp": opts.with_csp,
            "generator": "uxdom create-app",
        },
        indent=2,
    )

    for rel, content in files.items():
        _write(root / rel, content, force=opts.force)

    # Hard fail if the generator produced a broken tree (placeholders, syntax, CSP…).
    assert_scaffold_ok(root, expect_template=opts.template)
    return root


# ── templates ─────────────────────────────────────────────────────────────

_GITIGNORE = """\
__pycache__/
*.py[cod]
.venv/
venv/
.env
dist/
build/
*.egg-info/
.pytest_cache/
.mypy_cache/
assets/css/output.css
node_modules/
.DS_Store
"""

_ENV_EXAMPLE = """\
DEBUG=1
UX_CHANNEL_SECRET={{secret_placeholder}}
# REDIS_URL=redis://localhost:6379/0
"""

_REQUIREMENTS = """\
# Generated by `uxdom create-app`
ux-dom[fastapidev]>=0.1.0
fastapi>=0.103
uvicorn[standard]>=0.18
python-multipart>=0.0.6
{{channel_dep}}\
"""

_PYPROJECT = """\
[project]
name = "{{app_name}}"
version = "0.1.0"
description = "{{AppTitle}} — ux-dom app"
requires-python = ">={{python}},<3.15"
dependencies = [
  "ux-dom[fastapidev]>=0.1.0",
  "fastapi>=0.103",
  "uvicorn[standard]>=0.18",
  "python-multipart>=0.0.6",
]

[project.optional-dependencies]
channel = ["ux-channel>=0.1.0"]
dev = ["pytest>=7.0", "httpx>=0.24"]

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]
"""

_README = """\
# {{AppTitle}}

Scaffolded with **`uxdom create-app`** (template: `{{template}}`).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
{{channel_install}}
{{tailwind_hint}}
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
# or: uxdom dev app.main:app --port 8080
```

Open http://127.0.0.1:8080/

## Layout

```
app/
  main.py           # plugin composition + ASGI app
  document.py       # Document shell
  settings.py       # DEBUG, assets paths
  components/       # shared layout / UI
  routes/           # DirectoryRouter (Next-style file routes)
  channel_app.py    # uxchannel boot (if enabled)
assets/css/         # Tailwind input (if enabled)
```

## Batteries

| Feature | Status |
|---------|--------|
| FastAPI host + StreamingRoute | on |
| DirectoryRouter | on |
| HTMX control | on |
| Tailwind | {{tailwind_status}} |
| HMR (debug) | {{hmr_status}} |
| uxchannel | {{channel_status}} |
| CSP | {{csp_status}} |

## Production

* Set `DEBUG=0` (switches CSP to `Csp.prod()` automatically)
* Channel multi-worker: `UX_CHANNEL_SECRET` + `REDIS_URL`
* CSS: `python -m app.tailwindcss` (minify when not DEBUG)
"""

_SETTINGS = '''\
"""App settings — paths and feature flags."""
from __future__ import annotations

import os
from pathlib import Path

from ux_dom import WebAssets

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DEBUG", "1") not in ("0", "false", "False")

ASSETS_DIR = BASE_DIR / "assets"
CSS_DIR = ASSETS_DIR / "css"
INPUT_CSS = "input.css"
OUTPUT_CSS = "output.css"

# WebAssets: base_dir is the static root served at /css, /js, …
webassets = WebAssets(base_dir=ASSETS_DIR, dry_run=False)

APP_TITLE = "{{AppTitle}}"
WITH_TAILWIND = {{with_tailwind_bool}}
WITH_CHANNEL = {{with_channel_bool}}
WITH_HMR = {{with_hmr_bool}}
# CSP: on by default. Profile follows DEBUG via Csp.auto() in document.py
#   DEBUG=1 → dev (CDN + style attrs) · DEBUG=0 → prod (tight)
WITH_CSP = {{with_csp_bool}}
'''

_DOCUMENT = '''\
"""Two-stage Document — order is deliberate (see HtmlDocument.render).

Stage A (this module): Document(head=…, body=…).use(…)
  → common_head / common_body (after page head / end of body)

Stage B (page()): doc(*content, head=…, body=…)
  → call-time head first in <head>, call-time body early in <body>

    <head>  [B page title/css]  then  [A shared + XElement]
    <body>  content  [B]  placeholders  [A HTMX last]
"""
from __future__ import annotations

from ux_dom import Document
from ux_dom.dom import link, meta, title
from ux_dom.runtime import Channel, Csp, Htmx, XElement

from app import settings

# Stage A — shared chrome + runtimes (common_head / common_body)
# Order: UI runtimes first, then CSP last among shell plugins so middleware
# wraps the app after other mounts (Csp only adds middleware — no head tags).
document = Document(
    head=[
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
    ],
    body=[],  # end-of-body scripts come from Htmx().document_body()
    ensure_csrf_token=False,
    webassets=settings.webassets if settings.WITH_TAILWIND else None,
).use(
    XElement(),  # → common_head (after page title)
    Htmx(middleware=True, version="2.0.4"),  # → common_body (after content)
)

if settings.WITH_CHANNEL:
    _ch = Channel.optional(mount_via_ux_dom=False)
    if _ch is not None:
        document.use(_ch)  # → common_head

# CSP — zero-choice default: Csp.auto() follows settings.DEBUG
#   DEBUG=True  → Csp.dev()  (CDN scripts + style="..." OK)
#   DEBUG=False → Csp.prod() (no CDN hosts, tighter policy)
# Override: document.use(Csp.prod(connect_src=["'self'", "wss://…"]))
# Disable:  settings.WITH_CSP = False
if settings.WITH_CSP:
    document.use(Csp.auto(debug=settings.DEBUG))


def page(*content, page_title: str | None = None):
    """Stage B — page content + call-time head (title, optional CSS)."""
    call_head = [title(page_title or settings.APP_TITLE)]
    if settings.WITH_TAILWIND:
        call_head.append(link(href=f"/css/{settings.OUTPUT_CSS}", rel="stylesheet"))
    # Nonce is applied by HTMLResponse/StreamingResponse stamp — no meta needed.
    return document(*content, head=call_head)
'''

_LAYOUT = '''\
"""Shared page chrome."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, footer, header, main, nav, span


class Shell(Component):
    """Top nav + main slot."""

    def render(self, *children, active: str = "home"):
        def link(label: str, href: str, key: str):
            cls = "nav-link active" if active == key else "nav-link"
            return a(label, href=href, className=cls)

        return div(
            header(
                nav(
                    a("{{AppTitle}}", href="/", className="brand"),
                    link("Home", "/", "home"),
                    {{nav_extra}}
                    className="nav",
                ),
                className="site-header",
            ),
            main(*children, className="site-main", id="content"),
            footer(
                span("Built with ux-dom"),
                className="site-footer",
            ),
            className="shell min-h-screen bg-slate-50 text-slate-900",
            id="app",
        )
'''

_MAIN = '''\
"""
ASGI entry — FastAPI is the process; Document owns the DOM.

    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

Assembly (no hidden builder)::

    app = FastAPI(...)
    document.mount(app)          # runtimes → static + middleware
    DirectoryRouter(...).include(app)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import settings
from app.document import document

PACKAGE = Path(__file__).resolve().parent

# Optional style / HMR lifecycle (kept local — not another framework)
_styles: list = []
_hmr: list = []

if settings.WITH_TAILWIND:
    from ux_dom.plugins.style import TailwindStyle

    _styles.append(
        TailwindStyle(
            settings.webassets,
            file_path=PACKAGE / "main.py",
            input_css=settings.INPUT_CSS,
            output_css=settings.OUTPUT_CSS,
            minify=not settings.DEBUG,
        )
    )

if settings.WITH_HMR and settings.DEBUG:
    from ux_dom.plugins.hmr import HotReload

    _hmr.append(
        HotReload(
            watch_paths=[str(PACKAGE), str(settings.BASE_DIR / "assets")],
        )
    )


@asynccontextmanager
async def _lifespan(application: FastAPI):
    for style in _styles:
        try:
            await style.build(watch=settings.DEBUG)
        except Exception:
            pass
    for hmr in _hmr:
        startup = getattr(hmr, "startup", None)
        if startup is not None:
            await startup()
    yield
    for hmr in _hmr:
        shutdown = getattr(hmr, "shutdown", None)
        if shutdown is not None:
            await shutdown()
    for style in _styles:
        stop = getattr(style, "stop", None)
        if stop is not None:
            await stop()


app = FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG, lifespan=_lifespan)

try:
    from ux_dom.routing.fastapi import StreamingRoute

    app.router.route_class = StreamingRoute
except Exception:
    pass

# Document is SSoT — mounts runtime static (x_element.js) + middleware (CSP, HTMX, …)
document.mount(app)

# File-based routes (DirectoryRouter)
from ux_dom.plugins.routing import DirectoryRouting

DirectoryRouting(package_dir=PACKAGE, base_directory="routes").include(app)

if settings.ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(settings.ASSETS_DIR), check_dir=False),
        name="assets",
    )

for hmr in _hmr:
    route = hmr.asgi_route() if hasattr(hmr, "asgi_route") else None
    if route is not None:
        path, endpoint = route
        name = getattr(hmr, "url_name", getattr(hmr, "name", "hmr"))
        if hasattr(app, "add_api_websocket_route"):
            app.add_api_websocket_route(path, endpoint, name=name)
        elif hasattr(app, "add_websocket_route"):
            app.add_websocket_route(path, endpoint, name=name)

if settings.WITH_CHANNEL:
    try:
        from app.channel_app import attach_channel

        attach_channel(app)
    except ImportError:
        pass


@app.get("/")
def _root():
    return RedirectResponse("/index/Index")


@app.get("/health", response_class=JSONResponse)
def health():
    return {
        "ok": True,
        "app": settings.APP_TITLE,
        "debug": settings.DEBUG,
        "tailwind": settings.WITH_TAILWIND,
        "channel": settings.WITH_CHANNEL,
        "csp": settings.WITH_CSP,
        "runtimes": [getattr(r, "name", type(r).__name__) for r in document.runtimes()],
    }


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    run()
'''

_ROUTE_INDEX = '''\
"""Home route — DirectoryRouter discovers Component.routes."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, h1, li, p, ul

from app.components.layout import Shell
from app.document import page

__all__ = ["Index"]


class Index(Component):
    routes = ["get"]

    def render(self):
        return Shell(
            h1("Welcome to {{AppTitle}}", className="text-3xl font-bold mb-4"),
            p(
                "Scaffolded with ",
                "uxdom create-app",
                ". Edit ",
                "app/routes/",
                " — file-based routing reloads in DEBUG.",
                className="text-slate-600 mb-6",
            ),
            ul(
                {{home_links}}
                className="list-disc pl-6 space-y-1",
            ),
            active="home",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="{{AppTitle}}")
'''

_ROUTE_ABOUT = '''\
"""About page."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div, h1, p

from app.components.layout import Shell
from app.document import page

__all__ = ["About"]


class About(Component):
    routes = ["get"]

    def render(self):
        return Shell(
            h1("About", className="text-2xl font-semibold mb-3"),
            p(
                "This app uses ux-dom Components, DirectoryRouter, HTMX, "
                "and optional Tailwind / uxchannel plugins.",
                className="text-slate-600",
            ),
            active="about",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="About · {{AppTitle}}")
'''

_ROUTE_SHOP = '''\
"""Shop catalog example (template=shop)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, button, div, h1, h2, li, p, span, ul

from app.components.layout import Shell
from app.document import page

__all__ = ["Shop"]

PRODUCTS = [
    {"id": "sku-a", "name": "Aurora Ring", "price": 120},
    {"id": "sku-b", "name": "Nimbus Watch", "price": 340},
    {"id": "sku-c", "name": "Solace Pendant", "price": 89},
]


class Shop(Component):
    routes = ["get"]

    def render(self):
        items = [
            li(
                span(f"{p['name']} — ${p['price']}", className="font-medium"),
                " ",
                a(
                    "View",
                    href=f"/cart/Cart?sku={p['id']}",
                    className="text-sky-600 underline text-sm",
                ),
                id=p["id"],
                className="py-2 border-b border-slate-200",
            )
            for p in PRODUCTS
        ]
        return Shell(
            h1("Shop", className="text-3xl font-bold mb-2"),
            p("HTMX-friendly catalog · pure ux-dom", className="text-slate-600 mb-4"),
            ul(*items, id="catalog", className="mb-6"),
            a("Cart →", href="/cart/Cart", className="text-sky-700 font-semibold"),
            active="home",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Shop · {{AppTitle}}")
'''

_ROUTE_CART = '''\
"""Cart counter with HTMX post partial (template=shop)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import button, div, h1, span

from app.components.layout import Shell
from app.document import page

__all__ = ["Cart"]

_CART = {"n": 0}


class Cart(Component):
    routes = ["get", "post"]

    def render(self):
        return div(
            h1("Cart", className="text-2xl font-bold mb-3"),
            span(f"{_CART['n']} items", id="count", className="badge"),
            button(
                "+1",
                type="button",
                hx_post="/cart/Cart",
                hx_target="#cart-root",
                hx_swap="outerHTML",
                className="ml-3 rounded bg-slate-900 text-white px-3 py-1",
                id="add-btn",
            ),
            id="cart-root",
            className="card",
        )

    @classmethod
    def get(cls):
        return page(Shell(cls(), active="home"), page_title="Cart · {{AppTitle}}")

    @classmethod
    def post(cls):
        _CART["n"] += 1
        return cls()
'''

_CHANNEL_APP = '''\
"""uxchannel boot — live regions + trusted actions (template=live)."""
from __future__ import annotations

import os
from typing import Any

from ux_channel import Channel, ChannelConfig, Region

SECRET = os.environ.get(
    "UX_CHANNEL_SECRET", "{{secret_placeholder}}"
)

STATE: dict[str, Any] = {"n": 0}
_ch: Channel | None = None


def get_channel() -> Channel:
    if _ch is None:
        raise RuntimeError("channel not attached — call attach_channel(app) first")
    return _ch


def attach_channel(app) -> Channel:
    global _ch
    if os.environ.get("REDIS_URL"):
        cfg = ChannelConfig.production(SECRET).with_redis(os.environ["REDIS_URL"])
    else:
        cfg = ChannelConfig.development(secret=SECRET, allow_memory_stores=True)
    _ch = Channel.boot(app, config=cfg)

    class Counter(Region):
        uid = "demo.counter"

        def render(self, ctx=None):
            from ux_dom.dom import span

            return span(
                f"count={STATE['n']}",
                className="badge",
                data_channel_id=self.uid,
            ).__render__(pretty=False)

        @Region.action
        def bump(self):
            STATE["n"] += 1

    counter = Counter(_ch).mount()

    @_ch.on(refresh=[counter], idempotent=False)
    def bump_counter():
        STATE["n"] += 1

    # stash for routes
    _ch._ux_dom_counter = counter  # type: ignore[attr-defined]
    _ch._ux_dom_bump = bump_counter  # type: ignore[attr-defined]
    return _ch
'''

_CHANNEL_APP_MINIMAL = '''\
"""uxchannel attach (optional batteries)."""
from __future__ import annotations

import os

from ux_channel import Channel, ChannelConfig

SECRET = os.environ.get(
    "UX_CHANNEL_SECRET", "{{secret_placeholder}}"
)

_ch = None


def attach_channel(app):
    global _ch
    if os.environ.get("REDIS_URL"):
        cfg = ChannelConfig.production(SECRET).with_redis(os.environ["REDIS_URL"])
    else:
        cfg = ChannelConfig.development(secret=SECRET, allow_memory_stores=True)
    _ch = Channel.boot(app, config=cfg)
    return _ch


def get_channel():
    if _ch is None:
        raise RuntimeError("channel not attached")
    return _ch
'''

_ROUTE_LIVE = '''\
"""Live counter page — ux_dom markup + uxchannel controls (template=live)."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import button, div, h1, p, raw

from app.components.layout import Shell
from app.document import page

__all__ = ["Live"]


class Live(Component):
    routes = ["get"]

    def render(self):
        from app.channel_app import get_channel

        ch = get_channel()
        counter = ch._ux_dom_counter  # type: ignore[attr-defined]
        bump = ch._ux_dom_bump  # type: ignore[attr-defined]
        # Script tags: app/document.py → document.use(Channel) (UxChannelRuntime)
        # Bytes: attach_channel mounts GET /ux-channel/static/* from package (single copy)
        # Do NOT also raw(ch.scripts()) here — that double-injects the same tags.
        return Shell(
            h1("Live Counter", className="text-3xl font-bold mb-3"),
            p("ux-dom buttons · channel trust + region morph", className="mb-4 text-slate-600"),
            div(
                raw(counter()),
                button(
                    "Bump",
                    type="button",
                    className="ml-3 rounded bg-sky-600 text-white px-4 py-2",
                    **ch.control(bump).as_ux_dom(),
                ),
                className="flex items-center gap-3",
            ),
            active="home",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Live · {{AppTitle}}")
'''

_ROUTE_CHANNEL_DEMO = '''\
"""Minimal channel status page when --with-channel on minimal template."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div, h1, p, raw

from app.components.layout import Shell
from app.document import page

__all__ = ["ChannelDemo"]


class ChannelDemo(Component):
    routes = ["get"]

    def render(self):
        try:
            from app.channel_app import get_channel

            get_channel()
            msg = "uxchannel is booted (scripts via document.use(Channel))."
        except Exception as e:
            msg = f"Channel not available: {e}"
        return Shell(
            h1("Channel", className="text-2xl font-semibold mb-2"),
            p(msg, className="text-slate-600"),
            active="home",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="Channel · {{AppTitle}}")
'''

_INPUT_CSS = """\
@tailwind base;
@tailwind components;
@tailwind utilities;

/* App primitives */
@layer components {
  .shell { @apply flex flex-col min-h-screen; }
  .site-header { @apply border-b border-slate-200 bg-white; }
  .nav { @apply max-w-3xl mx-auto flex items-center gap-4 px-4 py-3; }
  .brand { @apply font-bold text-slate-900 mr-4; }
  .nav-link { @apply text-sm text-slate-600 hover:text-slate-900; }
  .nav-link.active { @apply text-sky-700 font-semibold; }
  .site-main { @apply flex-1 max-w-3xl mx-auto w-full px-4 py-8; }
  .site-footer { @apply border-t border-slate-200 text-center text-xs text-slate-500 py-4; }
  .badge { @apply inline-flex items-center rounded-full bg-slate-900 text-white text-sm px-3 py-1; }
  .card { @apply rounded-xl border border-slate-200 bg-white p-4 shadow-sm; }
}
"""

_TAILWIND_CONFIG = """\
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{py,html,js}", "./assets/**/*.{html,js}"],
  theme: { extend: {} },
  plugins: [],
};
"""

_TAILWIND_RUNNER = '''\
"""CLI helper: python -m app.tailwindcss"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ux_dom.settings.commands import TailwindCommand

from app import settings


def main() -> None:
    cmd = TailwindCommand(
        file_path=Path(__file__),
        webassets=settings.webassets,
        input_css=settings.INPUT_CSS,
        output_css=settings.OUTPUT_CSS,
        minify=not settings.DEBUG,
    )
    asyncio.run(cmd.async_run(wait=True))


if __name__ == "__main__":
    main()
'''


# ── tutorial template extras ──────────────────────────────────────────

_ROUTE_TUTORIAL_HTMX = '"""Tutorial: HTMX partial swap."""\nfrom __future__ import annotations\n\nfrom ux_dom import Component\nfrom ux_dom.dom import a, button, div, h1, p, span\n\nfrom app.document import page\n\n__all__ = ["HtmxDemo", "Partial"]\n\n_N = {"v": 0}\n\n\nclass HtmxDemo(Component):\n    routes = ["get"]\n\n    def render(self):\n        return div(\n            a("← Home", href="/index/Index", className="text-sm text-sky-600"),\n            h1("Day 2 · HTMX partials", className="text-2xl font-bold mt-4 mb-2"),\n            p(\n                "Click loads /htmx_demo/Partial into #panel (no full page reload).",\n                className="text-slate-600 mb-4",\n            ),\n            button(\n                "Load partial",\n                type="button",\n                hx_get="/htmx_demo/Partial",\n                hx_target="#panel",\n                hx_swap="innerHTML",\n                className="rounded-lg bg-slate-900 text-white px-4 py-2 text-sm",\n            ),\n            div(\n                span("empty", className="text-slate-400 text-sm"),\n                id="panel",\n                className="mt-4 min-h-[3rem] rounded-xl border border-dashed p-4",\n            ),\n            className="max-w-2xl mx-auto px-4 py-10",\n        )\n\n    @classmethod\n    def get(cls):\n        return page(cls(), page_title="HTMX · Tutorial")\n\n\nclass Partial(Component):\n    routes = ["get"]\n\n    def render(self):\n        _N["v"] += 1\n        return div(\n            p(\n                f"Partial #{_N[\'v\']} — only this fragment was swapped.",\n                className="text-sm text-emerald-700",\n            ),\n            id="partial-root",\n        )\n\n    @classmethod\n    def get(cls):\n        return cls()\n'

_ROUTE_TUTORIAL_XELEMENT = '"""Tutorial: XElement light DOM."""\nfrom __future__ import annotations\n\nfrom ux_dom import Component\nfrom ux_dom.dom import a, div, h1, p\n\nfrom app.components.x_hello import HelloLight\nfrom app.document import page\n\n__all__ = ["XelementDemo"]\n\n\nclass XelementDemo(Component):\n    routes = ["get"]\n\n    def render(self):\n        definition = HelloLight()\n        host = HelloLight()\n        return div(\n            a("← Home", href="/index/Index", className="text-sm text-sky-600"),\n            h1("Day 3 · XElement", className="text-2xl font-bold mt-4 mb-2"),\n            p(\n                "Definition (hidden) + host <x-hello>. Requires XElementRuntime (serves /ux-dom/static/x_element.js).",\n                className="text-slate-600 mb-4 text-sm",\n            ),\n            div(definition, className="hidden"),\n            host,\n            className="max-w-2xl mx-auto px-4 py-10",\n        )\n\n    @classmethod\n    def get(cls):\n        return page(cls(), page_title="XElement · Tutorial")\n'

_COMPONENT_TUTORIAL_XHELLO = '"""Tutorial CustomElement — x-tagname → <x-hello>."""\nfrom __future__ import annotations\n\nfrom dataclasses import dataclass\n\nfrom ux_dom.dom import div, template\nfrom ux_dom.dom.htmlelement import CustomElement\n\n\n@dataclass(eq=False)\nclass HelloLight(CustomElement):\n    def render(self, tag_name: str = "hello"):\n        return template(\n            div(\n                "Hello from XElement (light DOM)",\n                className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm",\n            ),\n            **{"x-tagname": tag_name},\n        )\n'

_ROUTE_TUTORIAL_RECIPES = '"""Tutorial recipes index."""\nfrom __future__ import annotations\n\nfrom ux_dom import Component\nfrom ux_dom.dom import a, code, div, h1, li, p, ul\n\nfrom app.document import page\n\n__all__ = ["Recipes"]\n\n\nclass Recipes(Component):\n    routes = ["get"]\n\n    def render(self):\n        return div(\n            a("← Home", href="/index/Index", className="text-sm text-sky-600"),\n            h1("Recipes", className="text-2xl font-bold mt-4 mb-2"),\n            p(\n                "Copy patterns from docs/guides/COOKBOOK.md as you grow.",\n                className="text-slate-600 mb-4 text-sm",\n            ),\n            ul(\n                li(code("uxdom add component Card")),\n                li(code("uxdom add route settings")),\n                li(code("uxdom add xelement Badge --kind shadow")),\n                li(code("uxdom doctor")),\n                className="list-disc pl-6 text-sm space-y-1",\n            ),\n            className="max-w-2xl mx-auto px-4 py-10",\n        )\n\n    @classmethod\n    def get(cls):\n        return page(cls(), page_title="Recipes · Tutorial")\n'
