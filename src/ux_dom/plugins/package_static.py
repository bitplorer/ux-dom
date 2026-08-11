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

``serve="webassets"`` remains as an **escape hatch** only (air-gapped tree
without site-packages). Prefer ``package_mount`` (default).
"""

from __future__ import annotations

import importlib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

from ux_dom.plugins.contribution import StaticArtifact

ServeMode = Literal["package_mount", "webassets"]
Inject = Literal["head", "body", "none"]


def resolve_package_resource(package: str, resource: str) -> Path:
    mod = importlib.import_module(package)
    base = Path(mod.__file__).resolve().parent  # type: ignore[arg-type]
    path = base / resource
    if path.is_file():
        return path
    alt = base.parent / package.split(".")[0] / resource
    if alt.is_file():
        return alt
    raise FileNotFoundError(f"package resource not found: {package}:{resource}")


def package_dir(package: str, subdir: str = "") -> Path:
    mod = importlib.import_module(package)
    base = Path(mod.__file__).resolve().parent  # type: ignore[arg-type]
    d = base / subdir if subdir else base
    if not d.is_dir():
        raise FileNotFoundError(f"package dir not found: {package}:{subdir or '.'}")
    return d


def loader_for(package: str, resource: str) -> Callable[[], bytes]:
    path = resolve_package_resource(package, resource)

    def _load(p: Path = path) -> bytes:
        return p.read_bytes()

    return _load


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

    def disk_path_under_assets(self, plugin: str) -> str:
        sub = "js" if self.kind == "js" else "css"
        return f"assets/{sub}/vendor/{plugin}/{self.public_name}"

    def public_path_webassets(self, plugin: str) -> str:
        sub = "js" if self.kind == "js" else "css"
        return f"/assets/{sub}/vendor/{plugin}/{self.public_name}"


@dataclass
class PackageStaticContribution:
    """
    Browser contribution from an **installed** package — single copy.

    Default ``serve="package_mount"``:
      * ``served_files()`` → exact file routes (safe; no dir listing)
      * tags point at that URL
      * ``artifacts()`` empty → ``uxdom build`` does **not** duplicate files
    """

    name: str
    files: Sequence[PackagedFile]
    serve: ServeMode = "package_mount"
    public_url_prefix: str = ""
    mount_package: str = ""
    mount_subdir: str = "static"
    plugin_kind: str = "contribution"

    def __post_init__(self) -> None:
        if not self.public_url_prefix:
            self.public_url_prefix = f"/ux-pkg/{self.name}/static"
        if not self.mount_package and self.files:
            self.mount_package = self.files[0].package
        if self.serve == "webassets":
            warnings.warn(
                f"PackageStaticContribution({self.name!r}): serve='webassets' "
                "duplicates files already in site-packages. Prefer package_mount "
                "(default) unless you have an air-gapped tree without pip packages.",
                stacklevel=2,
            )

    def served_files(self):
        """Explicit allowlisted files only (never a directory mount)."""
        if self.serve != "package_mount":
            return ()
        from ux_dom.plugins.safe_static import SafeStaticFile

        out = []
        prefix = self.public_url_prefix.rstrip("/")
        for f in self.files:
            # resource may be static/foo.js — package is mount_package or f.package
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


    def artifacts(self) -> Sequence[StaticArtifact]:
        if self.serve == "package_mount":
            return ()
        arts: list[StaticArtifact] = []
        for f in self.files:
            arts.append(
                StaticArtifact(
                    key=f.public_name,
                    disk_path=f.disk_path_under_assets(self.name),
                    public_path=f.public_path_webassets(self.name),
                    loader=loader_for(f.package, f.resource),
                    inject=f.inject,
                    tag="script" if f.kind == "js" else "link",
                    defer=f.defer,
                    async_=f.async_,
                    attrs=dict(f.attrs),
                    content_type=(
                        "application/javascript" if f.kind == "js" else "text/css"
                    ),
                )
            )
        return tuple(arts)

    def document_head(self) -> Sequence[Any]:
        return self._tags("head")

    def document_body(self) -> Sequence[Any]:
        return self._tags("body")

    def _tags(self, placement: str) -> list[Any]:
        if self.serve == "webassets":
            return []  # artifacts auto-tag
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
        if self.serve == "webassets":
            nodes = [a.html_node() for a in self.artifacts()]
            return "\n".join(str(n) for n in nodes if n is not None)
        return "\n".join(
            str(n) for n in list(self.document_head()) + list(self.document_body())
        )


def static_from_package(
    name: str,
    package: str,
    resources: Sequence[str | tuple[str, Inject]],
    *,
    serve: ServeMode = "package_mount",
    public_url_prefix: str = "",
    inject_default: Inject = "head",
    resource_prefix: str = "static/",
    mount_subdir: str = "static",
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
        serve=serve,
        public_url_prefix=public_url_prefix,
        mount_package=package,
        mount_subdir=mount_subdir,
    )


def ux_channel_static(
    *,
    serve: ServeMode = "package_mount",
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
        serve=serve,
        public_url_prefix=f"{path.rstrip('/')}/static",
        mount_subdir="static",
    )
