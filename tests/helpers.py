"""Shared test helpers.

``create_app`` here writes a **pure-dom experiment tree** for tests.
It is not a product scaffold. Product apps: ``uxcompose create-app``.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Optional


def available_templates() -> tuple[str, ...]:
    """Experiment helper only — product templates live on uxcompose."""
    return ("minimal",)


class ScaffoldOptions:
    """Test-only options for the experiment tree writer."""

    app_name: str = "app"
    dest: Optional[Path] = None
    force: bool = False
    with_tailwind: bool = False
    with_channel: bool = False
    with_hmr: bool = False
    with_csp: bool = True
    template: str = "minimal"

    def __init__(
        self,
        app_name: str | Path | None = None,
        dest: Path | str | None = None,
        *,
        force: bool = False,
        with_tailwind: bool = False,
        with_channel: bool = False,
        with_hmr: bool = False,
        with_csp: bool = True,
        template: str = "minimal",
        **_ignored,
    ):
        self.app_name = str(app_name or "app")
        self.dest = Path(dest) if dest is not None else None
        self.force = force
        self.with_tailwind = with_tailwind
        self.with_channel = with_channel
        self.with_hmr = with_hmr
        self.with_csp = with_csp
        self.template = template or "minimal"


_DOCUMENT_PY = '''\
from __future__ import annotations

from ux_dom import Document
from ux_dom.runtime import XElement, Csp

document = Document(head=[], body=[], ensure_csrf_token=False).use(
    XElement(),
    {csp}
)

def page(*children, page_title: str = "experiment"):
    return document(*children)
'''

_MAIN_PY = '''\
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.document import document
from ux_dom.routing.core import DirectoryRoutes
from ux_dom.routing.adapters.fastapi import mount

PACKAGE = Path(__file__).resolve().parent
app = FastAPI(title="{title}")
document.mount(app)

core = DirectoryRoutes(PACKAGE, base_directory="routes")
core.discover()
mount(core, app)


@app.get("/health")
def health():
    return JSONResponse({{"ok": True, "app": "{title}"}})
'''

_SETTINGS_PY = '''\
from pathlib import Path

DEBUG = True
APP_TITLE = "{title}"
WITH_CSP = {csp}
BASE = Path(__file__).resolve().parent.parent
'''

_INDEX_PY = '''\
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div

from app.document import page


class Index(Component):
    routes = ["get"]

    def render(self, *args, **kwargs):
        return div("index", id="index-root")

    @classmethod
    def get(cls):
        return page(cls().render(), page_title="Index")
'''

_ABOUT_PY = '''\
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import div

from app.document import page


class About(Component):
    routes = ["get"]

    def render(self, *args, **kwargs):
        return div("about", id="about-root")

    @classmethod
    def get(cls):
        return page(cls().render(), page_title="About")
'''


def create_app(opts: ScaffoldOptions) -> Path:
    """Write a pure-dom experiment tree. Not a product scaffold."""
    if opts.dest is None:
        raise ValueError("ScaffoldOptions.dest is required")
    root = Path(opts.dest)
    if root.exists() and any(root.iterdir()) and not opts.force:
        raise FileExistsError(f"{root} exists (pass force=True)")
    root.mkdir(parents=True, exist_ok=True)
    app = root / "app"
    routes = app / "routes"
    routes.mkdir(parents=True, exist_ok=True)
    (app / "__init__.py").write_text("", encoding="utf-8")
    (routes / "__init__.py").write_text("", encoding="utf-8")
    title = opts.app_name
    csp = "Csp.auto()" if opts.with_csp else "Csp.dev()"
    (app / "document.py").write_text(
        _DOCUMENT_PY.format(csp=csp), encoding="utf-8"
    )
    (app / "main.py").write_text(_MAIN_PY.format(title=title), encoding="utf-8")
    (app / "settings.py").write_text(
        _SETTINGS_PY.format(title=title, csp=str(bool(opts.with_csp))),
        encoding="utf-8",
    )
    (routes / "index.py").write_text(_INDEX_PY, encoding="utf-8")
    (routes / "about.py").write_text(_ABOUT_PY, encoding="utf-8")
    (root / "README.md").write_text(
        f"# {title}\n\nPure-dom experiment tree (tests only).\n"
        "Product apps: `uxcompose create-app`.\n",
        encoding="utf-8",
    )
    return root


@contextmanager
def scaffolded_app(
    name: str = "app",
    *,
    template: str = "minimal",
    with_tailwind: bool = False,
    with_channel: bool = False,
) -> Iterator[Path]:
    """Yield a temporary experiment tree (force=True)."""
    with TemporaryDirectory() as td:
        root = create_app(
            ScaffoldOptions(
                name,
                dest=Path(td) / name,
                force=True,
                template=template,
                with_tailwind=with_tailwind,
                with_channel=with_channel,
            )
        )
        yield root
