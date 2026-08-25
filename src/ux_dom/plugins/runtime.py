# Copyright (c) 2026 ux-dom
"""Built-in Contribution plugins — single copy, **safe file URLs only**."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional, Sequence

from ux_dom.plugins.contribution import StaticArtifact
from ux_dom.plugins.safe_static import SafeStaticFile

ServeMode = Literal["package_mount", "dual_copy", "webassets"]

XELEMENT_STATIC_PREFIX = "/ux-dom/static"
XELEMENT_JS_URL = f"{XELEMENT_STATIC_PREFIX}/x_element.js"


class XElementRuntime:
    """
    Serve ``x_element.js`` from the installed package — **one file**, not a dir.

    Security: ``served_files()`` registers only ``x_element.js``. App never
    mounts ``ux_dom/scripts/`` as a directory (would expose ``__init__.py``).
    """

    plugin_kind = "contribution"
    name = "ux_dom.xelement"

    def __init__(self, *, serve: ServeMode = "package_mount") -> None:
        if serve == "webassets":
            import warnings

            warnings.warn(
                "XElementRuntime(serve='webassets') is the dual-copy hatch; "
                "prefer serve='package_mount' (default) or serve='dual_copy'. "
                "This is NOT ux_compose.assets.WebAssets.",
                stacklevel=2,
            )
            serve = "dual_copy"
        self.serve = serve

    def served_files(self) -> Sequence[SafeStaticFile]:
        if self.serve != "package_mount":
            return ()
        return (
            SafeStaticFile.from_package(
                "ux_dom.scripts",
                "x_element.js",
                url=XELEMENT_JS_URL,
                plugin=self.name,
                content_type="application/javascript",
            ),
        )


    def artifacts(self) -> Sequence[StaticArtifact]:
        if self.serve == "package_mount":
            return ()
        from ux_dom.plugins.contribution import artifact_from_callable
        from ux_dom.scripts import x_element_js_text

        return (
            artifact_from_callable(
                key="runtime",
                disk_path="assets/js/x_element.js",
                public_path="/assets/js/x_element.js",
                loader=x_element_js_text,
                inject="head",
                defer=True,
            ),
        )

    def document_head(self) -> Sequence[Any]:
        if self.serve != "package_mount":
            return ()
        from ux_dom.dom import script

        return (script(src=XELEMENT_JS_URL, defer=True),)

    def document_body(self) -> Sequence[Any]:
        return ()


class UxChannelRuntime:
    """
    **ux-channel** client tags — package static URLs, or channel mount.

    Brand: PyPI ``ux-channel`` · import ``ux_channel`` · CLI ``uxchannel``.

    Default: **tags only** (same URLs as ``ch.scripts()``); channel host serves
    bytes. Set ``mount_via_ux_dom=True`` only if channel static is not mounted.

    This is a **Document contribution** (script tags). It is *not*
    ``ux_channel.Channel`` (the action control plane).
    """

    plugin_kind = "contribution"
    name = "ux_channel"

    def __init__(
        self,
        *,
        serve: ServeMode = "package_mount",
        path: str = "/ux-channel",
        bridge: bool = True,
        inspector: bool = False,
        mount_via_ux_dom: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        mount_via_ux_dom:
            **False (default)** — channel's own ``attach``/FastAPI mount serves
            ``GET {path}/static/*``. ux-dom only injects the same ``<script>``
            tags as ``ch.scripts()``. No second copy, no second mount.

            **True** — only if you are *not* mounting channel static (rare):
            ux-dom registers allowlisted ``SafeStaticFile`` routes for the same
            URLs (still one file on disk in site-packages).
        """
        import importlib

        from ux_dom.plugins.package_static import ux_channel_static

        try:
            importlib.import_module("ux_channel")
        except ImportError as e:
            raise ImportError(
                "UxChannelRuntime requires ux-channel "
                "(pip install 'ux-channel>=0.1.0')"
            ) from e
        self._inner = ux_channel_static(
            serve=serve, path=path, bridge=bridge, inspector=inspector
        )
        self.serve = serve
        self.path = path
        self.mount_via_ux_dom = mount_via_ux_dom
        if not mount_via_ux_dom and serve == "package_mount":
            self._inner.mount_package = ""

    @classmethod
    def optional(cls, **kwargs: Any) -> Optional["UxChannelRuntime"]:
        try:
            return cls(**kwargs)
        except ImportError:
            return None

    def served_files(self) -> Sequence[SafeStaticFile]:
        if not self.mount_via_ux_dom:
            return ()
        return self._inner.served_files()


    def artifacts(self) -> Sequence[StaticArtifact]:
        return self._inner.artifacts()

    def document_head(self) -> Sequence[Any]:
        return self._inner.document_head()

    def document_body(self) -> Sequence[Any]:
        return self._inner.document_body()

    def scripts_html(self) -> str:
        return self._inner.scripts_html()
