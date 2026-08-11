# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""PluginHub + App — explicit composition (contributions = browser surface)."""

from __future__ import annotations

import threading

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

from ux_dom.plugins.contribution import StaticArtifact
from ux_dom.plugins.protocols import (
    AssetsPlugin,
    ControlPlugin,
    HmrPlugin,
    HostPlugin,
    ResponsePlugin,
    RoutingPlugin,
    StylePlugin,
)


@dataclass
class MaterializedFile:
    plugin: str
    key: str
    disk_path: str
    public_path: str
    path: Path
    sha256: str
    action: str
    size: int


@dataclass
class MaterializeReport:
    root: Path
    files: list[MaterializedFile] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(f.path.is_file() for f in self.files)


@dataclass
class PluginHub:
    """Ordered plugin registry — single source of truth for browser surface.

    **Contributions** (static files + document head/body) are registered
    explicitly via ``App.use``. Controls that implement ``artifacts`` /
    ``document_head`` / ``document_body`` are also contributions.

    Thread-safety: register at startup only.
    """

    hosts: dict[str, HostPlugin] = field(default_factory=dict)
    routing: dict[str, RoutingPlugin] = field(default_factory=dict)
    responses: dict[str, ResponsePlugin] = field(default_factory=dict)
    assets: dict[str, AssetsPlugin] = field(default_factory=dict)
    styles: dict[str, StylePlugin] = field(default_factory=dict)
    hmr: dict[str, HmrPlugin] = field(default_factory=dict)
    controls: dict[str, ControlPlugin] = field(default_factory=dict)
    # Ordered contribution plugins (name → plugin). Controls also listed here.
    contributions: dict[str, Any] = field(default_factory=dict)
    _order: list[tuple[str, str]] = field(default_factory=list)
    _contrib_order: list[str] = field(default_factory=list)

    def add_host(self, plugin: HostPlugin) -> None:
        self.hosts[plugin.name] = plugin
        self._order.append(("host", plugin.name))

    def add_routing(self, plugin: RoutingPlugin) -> None:
        self.routing[plugin.name] = plugin
        self._order.append(("routing", plugin.name))

    def add_response(self, plugin: ResponsePlugin) -> None:
        self.responses[plugin.name] = plugin
        self._order.append(("response", plugin.name))

    def add_assets(self, plugin: AssetsPlugin) -> None:
        self.assets[plugin.name] = plugin
        self._order.append(("assets", plugin.name))

    def add_style(self, plugin: StylePlugin) -> None:
        self.styles[plugin.name] = plugin
        self._order.append(("style", plugin.name))

    def add_hmr(self, plugin: HmrPlugin) -> None:
        self.hmr[plugin.name] = plugin
        self._order.append(("hmr", plugin.name))

    def add_control(self, plugin: ControlPlugin) -> None:
        self.controls[plugin.name] = plugin
        self._order.append(("control", plugin.name))
        # Controls are browser-surface contributions when they expose shell APIs
        self._register_contribution(plugin)

    def add_contribution(self, plugin: Any) -> None:
        """Register a ContributionPlugin (static + document)."""
        self._register_contribution(plugin)
        self._order.append(("contribution", plugin.name))

    def _register_contribution(self, plugin: Any) -> None:
        name = getattr(plugin, "name", None)
        if not name:
            raise TypeError(f"contribution plugin missing name: {plugin!r}")
        if name not in self.contributions:
            self._contrib_order.append(name)
        self.contributions[name] = plugin

    def summary(self) -> list[str]:
        return [f"{kind}:{name}" for kind, name in self._order]

    # ── browser surface (decade-stable API) ─────────────────────────────

    def iter_contributions(self) -> list[Any]:
        return [
            self.contributions[n]
            for n in self._contrib_order
            if n in self.contributions
        ]

    def all_artifacts(self) -> list[tuple[str, StaticArtifact]]:
        out: list[tuple[str, StaticArtifact]] = []
        for plugin in self.iter_contributions():
            arts = getattr(plugin, "artifacts", None)
            if arts is None:
                continue
            for a in arts() or ():
                out.append((plugin.name, a))
        return out

    def shell_fragments(self, *, dedupe: bool = True) -> tuple[list[Any], list[Any]]:
        """Ordered head/body nodes for the HTML shell.

        Per contribution plugin, order is:

        1. Auto-tags from artifacts with inject=head|body
        2. Explicit ``document_head()`` / ``document_body()``

        When ``dedupe=True`` (default), external ``script[src]`` / ``link[href]``
        are unique by URL (first wins). Prevents double injection if the same
        runtime is contributed twice or both artifacts and document_* emit tags.
        """
        head: list[Any] = []
        body: list[Any] = []
        for plugin in self.iter_contributions():
            arts = getattr(plugin, "artifacts", lambda: ())()
            for a in arts or ():
                node = a.html_node()
                if node is None:
                    continue
                if a.inject == "head":
                    head.append(node)
                elif a.inject == "body":
                    body.append(node)
            if hasattr(plugin, "document_head"):
                head.extend(list(plugin.document_head() or ()))
            if hasattr(plugin, "document_body"):
                body.extend(list(plugin.document_body() or ()))
        if dedupe:
            from ux_dom.plugins.dedupe import dedupe_dom_nodes

            head = dedupe_dom_nodes(head)
            body = dedupe_dom_nodes(body)
        return head, body

    def served_static_files(self) -> list:
        """Validated SafeStaticFile list from contributions."""
        from ux_dom.plugins.safe_static import collect_served_files

        return collect_served_files(self)


    def materialize(self, root: Path | str) -> MaterializeReport:
        """Write all contribution artifacts under app root (build / deploy)."""
        root = Path(root).resolve()
        report = MaterializeReport(root=root)
        for plugin_name, art in self.all_artifacts():
            data = art.bytes()
            path = root / art.disk_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file():
                if path.read_bytes() == data:
                    action = "unchanged"
                else:
                    path.write_bytes(data)
                    action = "updated"
            else:
                path.write_bytes(data)
                action = "wrote"
            report.files.append(
                MaterializedFile(
                    plugin=plugin_name,
                    key=art.key,
                    disk_path=art.disk_path,
                    public_path=art.public_path,
                    path=path,
                    sha256=hashlib.sha256(data).hexdigest(),
                    action=action,
                    size=len(data),
                )
            )
        return report


_default_hub: Optional[PluginHub] = None
_HUB_LOCK = threading.Lock()


def get_hub() -> PluginHub:
    global _default_hub
    with _HUB_LOCK:
        if _default_hub is None:
            _default_hub = PluginHub()
        return _default_hub


def set_hub(hub: PluginHub) -> None:
    global _default_hub
    with _HUB_LOCK:
        _default_hub = hub


def _mount_package_static(app: Any, hub: PluginHub) -> None:
    """Install allowlisted package file routes (never directory StaticFiles)."""
    from ux_dom.plugins.safe_static import (
        UnsafeStaticError,
        collect_served_files,
        install_safe_static,
    )

    try:
        files = collect_served_files(hub)
    except UnsafeStaticError:
        # fail closed — do not mount anything unsafe
        return
    install_safe_static(app, files)


@dataclass
class App:
    """Feature registry + ASGI wiring — **not** the HTML shell.

    **Document is the single source of truth** for the page shell
    (``head`` / ``body`` / runtimes / ``document.mount(app)``).

    ``App`` only registers *what* plugins exist (hub). Prefer::

        document = Document(...).use(XElement(), Htmx(), Csp.auto())
        app = FastAPI(...); document.mount(app)
        # or: document.mount(fastapi_app)

    ``App.web(...).build()`` still works for plugin wiring. If you pass
    ``document=`` into ``App``, that instance is mounted via
    ``document.mount`` — App does **not** own head/body placement.
    """

    document: Any = (
        None  # optional Document instance for mount only — never place tags here
    )
    assets: Any = None
    debug: bool = False
    hub: PluginHub = field(default_factory=PluginHub)
    _built: Any = None

    def use(self, *plugins: Any) -> "App":
        """Register one or many plugins. ``None`` entries are skipped."""
        for plugin in plugins:
            self._use_one(plugin)
        return self

    def _use_one(self, plugin: Any) -> None:
        if plugin is None:
            return

        kind = getattr(plugin, "plugin_kind", None)

        # Contribution-only plugins (XElementRuntime, UxChannelRuntime)
        if kind == "contribution" or (
            kind is None
            and hasattr(plugin, "artifacts")
            and hasattr(plugin, "document_head")
            and hasattr(plugin, "document_body")
            and not hasattr(plugin, "wire")
            and not hasattr(plugin, "mount")
        ):
            self.hub.add_contribution(plugin)
            return

        if kind == "control" or (
            kind is None
            and isinstance(plugin, ControlPlugin)
            and hasattr(plugin, "wire")
        ):
            self.hub.add_control(plugin)
        elif kind == "routing" or (
            kind is None
            and isinstance(plugin, RoutingPlugin)
            and hasattr(plugin, "include")
        ):
            self.hub.add_routing(plugin)
        elif kind == "response" or (
            kind is None
            and isinstance(plugin, ResponsePlugin)
            and hasattr(plugin, "wrap")
        ):
            self.hub.add_response(plugin)
        elif kind == "assets" or (
            kind is None
            and isinstance(plugin, AssetsPlugin)
            and hasattr(plugin, "layout")
        ):
            self.hub.add_assets(plugin)
        elif kind == "style" or (
            kind is None
            and isinstance(plugin, StylePlugin)
            and hasattr(plugin, "stylesheet_href")
        ):
            self.hub.add_style(plugin)
        elif kind == "hmr" or (
            kind is None
            and isinstance(plugin, HmrPlugin)
            and hasattr(plugin, "client_script")
        ):
            self.hub.add_hmr(plugin)
        elif kind == "host" or isinstance(plugin, HostPlugin):
            self.hub.add_host(plugin)
        else:
            raise TypeError(
                f"unknown plugin type {type(plugin)!r}; implement a ux_dom.plugins protocol "
                f"(ContributionPlugin, ControlPlugin, HostPlugin, …)"
            )

    # ── intention-revealing shortcuts (wrap .use) ─────────────────────────

    def xelement(self, **kwargs: Any) -> "App":
        """Ship XElement runtime (safe package file route + script tag)."""
        from ux_dom.plugins.runtime import XElementRuntime

        return self.use(XElementRuntime(**kwargs))

    def channel(self, **kwargs: Any) -> "App":
        """uxchannel tags (optional; no-op if package missing)."""
        from ux_dom.plugins.runtime import UxChannelRuntime

        return self.use(UxChannelRuntime.optional(**kwargs))

    def htmx(self, **kwargs: Any) -> "App":
        from ux_dom.plugins.control import HtmxControl

        kwargs.setdefault("middleware", True)
        kwargs.setdefault("version", "2.0.4")
        return self.use(HtmxControl(**kwargs))

    def csp(self, **kwargs: Any) -> "App":
        """CSP nonces via middleware — see ``docs/security/CSP.md``."""
        from ux_dom.plugins.csp import Csp

        return self.use(Csp(**kwargs))

    def fastapi(self, **kwargs: Any) -> "App":
        from ux_dom.plugins.host import FastAPIHost

        if "debug" not in kwargs:
            kwargs["debug"] = self.debug
        return self.use(FastAPIHost(**kwargs))

    def routes(
        self,
        package_dir: Any = None,
        *,
        base_directory: str = "routes",
        prefix: str = "",
        **kwargs: Any,
    ) -> "App":
        from pathlib import Path

        from ux_dom.plugins.routing import DirectoryRouting

        if package_dir is None:
            raise TypeError("routes(package_dir=...) is required")
        return self.use(
            DirectoryRouting(
                package_dir=Path(package_dir),
                base_directory=base_directory,
                prefix=prefix,
                **kwargs,
            )
        )

    def plugins(self, *plugins: Any) -> "App":
        """Alias of ``use(*plugins)`` — read as “install these features”."""
        return self.use(*plugins)

    @classmethod
    def web(
        cls,
        *,
        title: str = "ux-dom",
        debug: bool = False,
        package_dir: Any = None,
        base_directory: str = "routes",
        xelement: bool = True,
        channel: bool = False,
        htmx: bool = True,
        csp: bool = False,
        document: Any = None,
        assets: Any = None,
        htmx_version: str = "2.0.4",
        **host_kwargs: Any,
    ) -> "App":
        """
        Batteries-included builder for the common ASGI app.

        ::

            # Prefer: document = Document(...).use(...); app = FastAPI(...); document.mount(app)
            app = App.web(
                title="Shop",
                package_dir=Path(__file__).parent,
                channel=True,
                csp=True,
            ).build()
        """
        self = cls(debug=debug, document=document, assets=assets)
        if xelement:
            self.xelement()
        if channel:
            self.channel()
        if htmx:
            self.htmx(version=htmx_version)
        if csp:
            self.csp()
        self.fastapi(title=title, **host_kwargs)
        if package_dir is not None:
            self.routes(package_dir=package_dir, base_directory=base_directory)
        return self

    def use_host(self, plugin: HostPlugin) -> "App":
        self.hub.add_host(plugin)
        return self

    def use_routing(self, plugin: RoutingPlugin) -> "App":
        self.hub.add_routing(plugin)
        return self

    def use_control(self, plugin: ControlPlugin) -> "App":
        self.hub.add_control(plugin)
        return self

    def use_style(self, plugin: StylePlugin) -> "App":
        self.hub.add_style(plugin)
        return self

    def use_hmr(self, plugin: HmrPlugin) -> "App":
        self.hub.add_hmr(plugin)
        return self

    def shell_fragments(self) -> tuple[list[Any], list[Any]]:
        """Low-level: ``(head_tags, body_tags)`` from hub. Prefer Document."""
        return self.hub.shell_fragments()

    def runtime_tags(self) -> tuple[list[Any], list[Any]]:
        """Alias of ``shell_fragments`` — clearer name (head, body)."""
        return self.hub.shell_fragments()

    def materialize_assets(self, root: Path | str) -> MaterializeReport:
        return self.hub.materialize(root)

    def build(self) -> Any:
        """Publish hub → host → Document.mount (if any) → routing → controls.

        Head/body placement stays on ``Document`` only. App never injects tags.
        """
        set_hub(self.hub)
        app = self._built
        for name, host in self.hub.hosts.items():
            app = host.mount(
                app,
                settings=None,
                hub=self.hub,
                debug=self.debug,
                assets=self.assets,
            )
            self._built = app
        # Document is SSoT: it mounts its own runtimes/static/middleware
        doc = self.document
        if doc is not None and hasattr(doc, "mount") and app is not None:
            try:
                if hasattr(doc, "hub"):
                    doc.hub = self.hub
                doc.mount(app)
            except Exception:
                pass
        for name, routing in self.hub.routing.items():
            if app is not None:
                routing.include(app)
        for name, control in self.hub.controls.items():
            if app is not None:
                control.mount(app)
        if app is not None:
            _mount_package_static(app, self.hub)
        set_hub(self.hub)
        return app

    def plugin_summary(self) -> Sequence[str]:
        return self.hub.summary()
