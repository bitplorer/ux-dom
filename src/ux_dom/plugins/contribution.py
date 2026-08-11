# Copyright (c) 2026 ux-dom
"""
Decade-stable **Contribution** contract for static files + Document shell.

First principles
----------------
Anything that affects the **browser surface** of a ux-dom app is a Contribution:

1. **Artifacts** — files that must exist under the static tree (JS/CSS).
2. **Head / body** — DOM nodes injected into the HTML shell.

**Primary registration:** ``document.use(plugin)`` on a ``Document`` instance
(ordered, explicit). That is the production SSoT for head/body tags and
``mount`` hooks.

**Optional:** ``App.use(plugin)`` → ``PluginHub`` for tests/hubs. Document can
merge hub tags only if ``include_runtimes=True`` (not the default path).

CDN scripts are still Contributions (empty artifacts, tags in body)::

    document = Document(head=[], body=[]).use(
        XElement(),          # ships + injects x_element.js
        Htmx(cdn=True),      # CDN script
        Channel.optional(),  # companion package when installed
        Csp.auto(),
    )
    document.mount(app)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Callable,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

Inject = Literal["head", "body", "none"]
TagKind = Literal["script", "link", "none"]


@dataclass(frozen=True)
class StaticArtifact:
    """One static file a plugin requires on disk and (optionally) as a tag.

    Parameters
    ----------
    key:
        Stable id within the plugin (``runtime``, ``bridge``).
    disk_path:
        Path relative to the **app root** (``assets/js/x_element.js``).
    public_path:
        URL path after StaticFiles mount (``/assets/js/x_element.js``).
    loader:
        Zero-arg callable returning file bytes (from package data, etc.).
    inject:
        Whether to auto-emit a tag in head/body (``none`` = ship only).
    tag:
        HTML tag kind for injection.
    """

    key: str
    disk_path: str
    public_path: str
    loader: Callable[[], bytes]
    inject: Inject = "head"
    tag: TagKind = "script"
    defer: bool = True
    async_: bool = False
    media: str = "all"
    attrs: Mapping[str, str] = field(default_factory=dict)
    content_type: str = "application/javascript"

    def bytes(self) -> bytes:
        return self.loader()

    def html_node(self) -> Any:
        if self.inject == "none" or self.tag == "none":
            return None
        from ux_dom.dom import link, script

        if self.tag == "link" or self.content_type.startswith("text/css"):
            link_kw: dict[str, Any] = {
                "rel": "stylesheet",
                "href": self.public_path,
                "media": self.media,
            }
            link_kw.update(dict(self.attrs))
            return link(**link_kw)
        script_kw: dict[str, Any] = {"src": self.public_path}
        if self.defer:
            script_kw["defer"] = True
        if self.async_:
            script_kw["async"] = True
        script_kw.update(dict(self.attrs))
        return script(**script_kw)


@runtime_checkable
class ContributionPlugin(Protocol):
    """
    Unified browser-surface plugin (static files + document fragments).

    Implement **only what you need**:

    * ``artifacts()`` — files to ship (may be empty for pure CDN plugins)
    * ``document_head()`` / ``document_body()`` — extra tags (CDN, inline, …)

    Auto-tags for artifacts with ``inject != "none"`` are merged by the hub
    **before** explicit ``document_head``/``document_body`` from the same plugin.
    """

    name: str

    def artifacts(self) -> Sequence[StaticArtifact]: ...

    def document_head(self) -> Sequence[Any]: ...

    def document_body(self) -> Sequence[Any]: ...


def artifact_from_path(
    *,
    plugin: str,
    key: str,
    path: Path,
    disk_path: str,
    public_path: str,
    inject: Inject = "body",
    defer: bool = True,
    attrs: Optional[Mapping[str, str]] = None,
) -> StaticArtifact:
    """Build a StaticArtifact that loads bytes from a filesystem path."""
    path = Path(path)

    def _load(p: Path = path) -> bytes:
        return p.read_bytes()

    return StaticArtifact(
        key=key,
        disk_path=disk_path,
        public_path=public_path,
        loader=_load,
        inject=inject,
        defer=defer,
        attrs=dict(attrs or {}),
    )


def artifact_from_callable(
    *,
    key: str,
    disk_path: str,
    public_path: str,
    loader: Callable[[], str | bytes],
    inject: Inject = "head",
    defer: bool = True,
    attrs: Optional[Mapping[str, str]] = None,
) -> StaticArtifact:
    def _load() -> bytes:
        data = loader()
        return data if isinstance(data, bytes) else data.encode("utf-8")

    return StaticArtifact(
        key=key,
        disk_path=disk_path,
        public_path=public_path,
        loader=_load,
        inject=inject,
        defer=defer,
        attrs=dict(attrs or {}),
    )
