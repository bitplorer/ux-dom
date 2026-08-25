# Copyright (c) 2026 ux-dom
"""Facade over ``PluginHub`` contributions.

Prefer the first-class API::

    from ux_dom.plugins import App, XElementRuntime, shell_fragments
    App().use(XElementRuntime())...
    hub.shell_fragments()
    hub.materialize(root)

These helpers exist so older call sites keep working without a second registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

from ux_dom.plugins.hub import PluginHub, get_hub
from ux_dom.plugins.runtime import UxChannelRuntime, XElementRuntime
from ux_dom.plugins.shell import shell_fragments as _shell_fragments

__all__ = [
    "compose_document_parts",
    "sync_assets",
    "ensure_default_contributions",
    "apply_to_document",
    "register_js",
    "register_css",
]


def ensure_default_contributions(hub: Optional[PluginHub] = None) -> PluginHub:
    """Ensure ``XElementRuntime`` is registered (idempotent by name)."""
    h = hub or get_hub()
    if "ux_dom.xelement" not in h.contributions:
        h.add_contribution(XElementRuntime())
    return h


def compose_document_parts(
    *extra_head: Any,
    hub: Any = None,
    extra_body: Sequence[Any] = (),
    include_core: bool = True,
    include_ux_channel: bool = False,
    include_controls: bool = True,
) -> tuple[list[Any], list[Any]]:
    h = hub or get_hub()
    if include_core:
        ensure_default_contributions(h)
    if include_ux_channel and "ux_channel" not in h.contributions:
        ch = UxChannelRuntime.optional()
        if ch is not None:
            h.add_contribution(ch)
    return _shell_fragments(h, *extra_head, extra_body=extra_body)


def sync_assets(
    root: Path,
    *,
    hub: Optional[PluginHub] = None,
    include_core: bool = True,
    include_ux_channel: bool = False,
    **_ignored: Any,
) -> Any:
    h = hub or get_hub()
    if include_core:
        ensure_default_contributions(h)
    if include_ux_channel and "ux_channel" not in h.contributions:
        ch = UxChannelRuntime.optional()
        if ch is not None:
            h.add_contribution(ch)
    return h.materialize(root)


def apply_to_document(document: Any, *, hub: Any = None, **kwargs: Any) -> Any:
    head, body = compose_document_parts(hub=hub, **kwargs)
    if head:
        existing = getattr(document, "head", None)
        document.head = (
            list(head)
            if existing is None
            else (list(existing) if isinstance(existing, list) else [existing])
            + list(head)
        )
    if body:
        existing = getattr(document, "body", None)
        document.body = (
            list(body)
            if existing is None
            else (list(existing) if isinstance(existing, list) else [existing])
            + list(body)
        )
    return document


def register_js(
    plugin: str,
    filename: str,
    *,
    source: Any,
    placement: str = "body",
    defer: bool = True,
    hub: Optional[PluginHub] = None,
    **attributes: str,
) -> Any:
    """Register one ad-hoc JS contribution on the hub (prefer a real plugin class)."""
    from ux_dom.plugins.contribution import StaticArtifact, artifact_from_path

    h = hub or get_hub()
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).is_file()):
        art = artifact_from_path(
            plugin=plugin,
            key=filename,
            path=Path(source),
            disk_path=f"assets/js/vendor/{plugin}/{filename}",
            public_path=f"/assets/js/vendor/{plugin}/{filename}",
            inject=placement,  # type: ignore[arg-type]
            defer=defer,
            attrs=attributes,
        )
    else:
        text = source if isinstance(source, str) else bytes(source).decode()

        def _load(t: str = text) -> bytes:
            return t.encode("utf-8")

        art = StaticArtifact(
            key=filename,
            disk_path=f"assets/js/vendor/{plugin}/{filename}",
            public_path=f"/assets/js/vendor/{plugin}/{filename}",
            loader=_load,
            inject=placement,  # type: ignore[arg-type]
            defer=defer,
            attrs=attributes,
        )

    class _OneShot:
        plugin_kind = "contribution"
        name = f"adhoc.{plugin}.{filename}"

        def artifacts(self):
            return (art,)

        def document_head(self):
            return ()

        def document_body(self):
            return ()

    h.add_contribution(_OneShot())
    return art


def register_css(
    plugin: str,
    filename: str,
    *,
    source: Any,
    placement: str = "head",
    hub: Optional[PluginHub] = None,
    **attributes: str,
) -> Any:
    from ux_dom.plugins.contribution import StaticArtifact

    h = hub or get_hub()
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).is_file()):
        data = Path(source).read_bytes()
    else:
        data = source.encode() if isinstance(source, str) else bytes(source)

    def _load(b: bytes = data) -> bytes:
        return b

    art = StaticArtifact(
        key=filename,
        disk_path=f"assets/css/vendor/{plugin}/{filename}",
        public_path=f"/assets/css/vendor/{plugin}/{filename}",
        loader=_load,
        inject=placement,  # type: ignore[arg-type]
        tag="link",
        content_type="text/css",
        attrs=attributes,
    )

    class _OneShot:
        plugin_kind = "contribution"
        name = f"adhoc.css.{plugin}.{filename}"

        def artifacts(self):
            return (art,)

        def document_head(self):
            return ()

        def document_body(self):
            return ()

    h.add_contribution(_OneShot())
    return art
