# Copyright (c) 2026 ux-dom
"""
Decade-stable **Contribution** contract for static files + Document shell.

First principles
----------------
Anything that affects the **browser surface** of a ux-dom app is a Contribution:

1. **Artifacts** — files the app serves (JS/CSS); ux-dom emits their tags.
2. **Head / body** — DOM nodes injected into the HTML shell.

**Primary registration:** ``document.use(plugin)`` on a ``Document`` instance
(ordered, explicit). That is the production SSoT for head/body tags and
``mount`` hooks.

**Optional:** ``App.use(plugin)`` → ``PluginHub`` for tests/hubs. Document can
merge hub tags only if ``include_runtimes=True`` (not the default path).

Runtimes attach in order::

    document = Document(head=[], body=[]).use(
        XElement(),          # ships + injects x_element.js
        Channel.optional(),  # companion package when installed
        Csp.auto(),
    )
    document.mount(app)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Literal,
    Mapping,
    Protocol,
    Sequence,
    runtime_checkable,
)

Inject = Literal["head", "body", "none"]
TagKind = Literal["script", "link", "none"]


@dataclass(frozen=True)
class StaticArtifact:
    """One static file a plugin needs as a tag; the app serves the file.

    Parameters
    ----------
    key:
        Stable id within the plugin (``runtime``, ``bridge``).
    public_path:
        URL the app serves the file at (``/assets/js/app.js``).
    inject:
        Whether to auto-emit a tag in head/body (``none`` = no tag).
    tag:
        HTML tag kind for injection.
    """

    key: str
    public_path: str
    inject: Inject = "head"
    tag: TagKind = "script"
    defer: bool = True
    async_: bool = False
    media: str = "all"
    attrs: Mapping[str, str] = field(default_factory=dict)
    content_type: str = "application/javascript"

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
