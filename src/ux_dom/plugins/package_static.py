# Copyright (c) 2026 ux-dom
"""
Packaged static — **one copy**: the installed library in site-packages.

First principle
---------------
If ``pip install ux-channel`` (or ux_dom) put JS in the package, **do not copy**
it into ``assets/``. Dual copies cause version skew and wasted build steps.

ux-channel pattern (gold standard)::

    package static/  →  StaticFiles mount  →  ch.scripts() tags in Document

ux-dom mirrors that for every library contribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence


Inject = Literal["head", "body", "none"]


@dataclass(frozen=True)
class PackagedFile:
    package: str
    resource: str
    public_name: str
    inject: Inject = "head"
    defer: bool = True
    async_: bool = False
    kind: Literal["js", "css"] = "js"
    attrs: Mapping[str, str] = field(default_factory=dict)

@dataclass
class PackageStaticContribution:
    """
    Browser contribution from an **installed** package — single copy.

      * ``served_files()`` → exact file routes (safe; no dir listing)
      * tags point at that URL; nothing is copied into the app
    """

    name: str
    files: Sequence[PackagedFile]
    public_url_prefix: str = ""
    plugin_kind: str = "contribution"

    def __post_init__(self) -> None:
        if not self.public_url_prefix:
            self.public_url_prefix = f"/ux-pkg/{self.name}/static"

    def served_files(self):
        """Explicit allowlisted files only (never a directory mount)."""
        from ux_dom.plugins.safe_static import SafeStaticFile

        out = []
        prefix = self.public_url_prefix.rstrip("/")
        for f in self.files:
            pkg = f.package
            url = f"{prefix}/{f.public_name}"
            out.append(
                SafeStaticFile.from_package(
                    pkg,
                    f.resource,
                    url=url,
                    plugin=self.name,
                    content_type=(
                        "text/css" if f.kind == "css" else "application/javascript"
                    ),
                )
            )
        return tuple(out)


    def document_head(self) -> Sequence[Any]:
        return self._tags("head")

    def document_body(self) -> Sequence[Any]:
        return self._tags("body")

    def _tags(self, placement: str) -> list[Any]:
        from ux_dom.dom import link, script

        out: list[Any] = []
        prefix = self.public_url_prefix.rstrip("/")
        for f in self.files:
            if f.inject != placement:
                continue
            url = f"{prefix}/{f.public_name}"
            if f.kind == "css":
                link_kw: dict = {"rel": "stylesheet", "href": url, **dict(f.attrs)}
                out.append(link(**link_kw))
            else:
                script_kw: dict = {"src": url, **dict(f.attrs)}
                if f.defer:
                    script_kw["defer"] = True
                if f.async_:
                    script_kw["async"] = True
                out.append(script(**script_kw))
        return out

    def scripts_html(self) -> str:
        return "\n".join(
            str(n) for n in list(self.document_head()) + list(self.document_body())
        )


def static_from_package(
    name: str,
    package: str,
    resources: Sequence[str | tuple[str, Inject]],
    *,
    public_url_prefix: str = "",
    inject_default: Inject = "head",
    resource_prefix: str = "static/",
) -> PackageStaticContribution:
    files: list[PackagedFile] = []
    for item in resources:
        if isinstance(item, tuple):
            res_name, inj = item
        else:
            res_name, inj = item, inject_default
        resource = (
            res_name
            if "/" in res_name or res_name.startswith(resource_prefix)
            else f"{resource_prefix}{res_name}"
        )
        public = Path(res_name).name
        kind = "css" if public.endswith(".css") else "js"
        files.append(
            PackagedFile(
                package=package,
                resource=resource,
                public_name=public,
                inject=inj,
                kind=kind,  # type: ignore[arg-type]
            )
        )
    if not public_url_prefix:
        public_url_prefix = f"/ux-pkg/{name}/static"
    return PackageStaticContribution(
        name=name,
        files=files,
        public_url_prefix=public_url_prefix,
    )


def ux_channel_static(
    *,
    path: str = "/ux-channel",
    bridge: bool = True,
    inspector: bool = False,
) -> PackageStaticContribution:
    """Mirror ``ch.scripts()`` — single copy from installed ux_channel package."""
    resources: list[str | tuple[str, Inject]] = [("ux-channel.js", "head")]
    if bridge:
        resources.append(("ux-bridge.js", "head"))
    if inspector:
        resources.append(("ux-inspector.js", "head"))
    return static_from_package(
        "ux_channel",
        "ux_channel",
        resources,
        public_url_prefix=f"{path.rstrip('/')}/static",
    )
