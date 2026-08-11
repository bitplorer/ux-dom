# Copyright (c) 2026 ux-dom
"""
Safe package-static serving — **explicit files only**, never raw filesystem roots.

Allowlists (three layers)
-------------------------
1. **URL prefix** — only known static namespaces (not ``/``, ``/app``, …)
2. **Extension** — browser assets only (never ``.py`` / ``.pyc`` / ``.so``)
3. **Containment** — resolved path must stay under the owning package directory

Registration is always **file → URL** (one route per file). Directory mounts
are intentionally unsupported.

See docs/security/SAFE_STATIC.md for the investigation matrix.
"""

from __future__ import annotations

import importlib
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

# ---------------------------------------------------------------------------
# Layer 1 — extensions a browser may load as assets
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = frozenset(
    {
        ".js",
        ".mjs",
        ".cjs",
        ".css",
        ".map",  # source maps (e.g. foo.js.map → suffix .map)
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        # .json intentionally omitted: package.json / manifests can leak metadata.
        # Register JSON only via a future explicit opt-in if needed.
    }
)

# Never serve these even if somehow renamed into ALLOWED_EXTENSIONS by mistake
_CODE_EXTENSIONS = frozenset({".py", ".pyc", ".pyo", ".so", ".dll", ".dylib"})

# ---------------------------------------------------------------------------
# Layer 2 — public URL shape (no path traversal, no app routes)
# ---------------------------------------------------------------------------
# Allowed:
#   /ux-dom/static/<file>
#   /ux-dom/static/<subdir>/<file>     (one or more subdirs of safe tokens)
#   /ux-pkg/<plugin>/static/<file>
#   /ux-channel/static/<file>                   (ux-channel convention)
_SAFE_URL = re.compile(
    r"^/"
    r"(?:"
    r"ux-dom/static|"
    r"ux-pkg/[\w.-]+/static|"
    r"ux-channel/static"
    r")"
    r"(?:/[\w.-]+)+"  # at least one segment; segments are file or subdirs
    r"$"
)

# Path segments that must never appear in the resolved filesystem path
_BLOCKED_FS_SEGMENTS = frozenset(
    {
        ".env",
        ".git",
        ".ssh",
        ".aws",
        "__pycache__",
    }
)


class UnsafeStaticError(ValueError):
    """Raised when a static registration would be unsafe."""


def _package_root(package: str) -> Path:
    mod = importlib.import_module(package)
    file = getattr(mod, "__file__", None)
    if not file:
        raise UnsafeStaticError(f"package {package!r} has no __file__ (namespace?)")
    return Path(file).resolve().parent


def _validate_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("/"):
        raise UnsafeStaticError(f"url must be absolute path starting with /: {url!r}")
    if ".." in url or "\\" in url or "\x00" in url:
        raise UnsafeStaticError(f"url contains path traversal or NUL: {url!r}")
    if "//" in url[1:]:
        raise UnsafeStaticError(f"url contains empty segment: {url!r}")
    if not _SAFE_URL.match(url):
        raise UnsafeStaticError(
            f"url not on allowlist pattern "
            f"(/ux-dom/static/…, /ux-pkg/<name>/static/…, /ux-channel/static/…): {url!r}"
        )
    # final segment should look like a filename with an allowed extension
    name = url.rsplit("/", 1)[-1]
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsafeStaticError(
            f"url filename extension {suffix!r} not in ALLOWED_EXTENSIONS: {url!r}"
        )
    return url


def _validate_file_under_package(file_path: Path, package_root: Path) -> Path:
    path = file_path.resolve()
    root = package_root.resolve()
    try:
        path.relative_to(root)
    except ValueError as e:
        raise UnsafeStaticError(f"file {path} is outside package root {root}") from e
    if not path.is_file():
        raise UnsafeStaticError(f"not a file: {path}")
    for part in path.parts:
        if part in _BLOCKED_FS_SEGMENTS:
            raise UnsafeStaticError(f"refusing path segment {part!r}: {path}")
    suffix = path.suffix.lower()
    if suffix in _CODE_EXTENSIONS:
        raise UnsafeStaticError(f"refusing to serve code artifact: {path}")
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsafeStaticError(
            f"extension {suffix!r} not allowed for package static "
            f"(allowed: {sorted(ALLOWED_EXTENSIONS)})"
        )
    return path


def _validate_resource(resource: str) -> str:
    if not resource or resource.startswith("/") or "\\" in resource or ".." in resource:
        raise UnsafeStaticError(f"unsafe resource path: {resource!r}")
    if "\x00" in resource:
        raise UnsafeStaticError("resource contains NUL")
    # normalize posix-ish relative path
    parts = [p for p in resource.replace("\\", "/").split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        raise UnsafeStaticError(f"unsafe resource path: {resource!r}")
    if any(p in _BLOCKED_FS_SEGMENTS for p in parts):
        raise UnsafeStaticError(f"resource hits blocked segment: {resource!r}")
    return "/".join(parts)


@dataclass(frozen=True)
class SafeStaticFile:
    """One allowlisted file: public URL → package-owned path."""

    url: str
    path: Path
    package_root: Path
    content_type: str = "application/javascript"
    plugin: str = ""
    package: str = ""
    resource: str = ""

    @classmethod
    def from_package(
        cls,
        package: str,
        resource: str,
        *,
        url: str,
        plugin: str = "",
        content_type: Optional[str] = None,
    ) -> "SafeStaticFile":
        resource = _validate_resource(resource)
        url = _validate_url(url)
        root = _package_root(package)
        path = _validate_file_under_package(root / resource, root)
        if content_type is None:
            guessed, _ = mimetypes.guess_type(str(path))
            content_type = guessed or (
                "application/javascript"
                if path.suffix.lower() in {".js", ".mjs", ".cjs"}
                else "application/octet-stream"
            )
        return cls(
            url=url,
            path=path,
            package_root=root,
            content_type=content_type,
            plugin=plugin,
            package=package,
            resource=resource,
        )

    def read_bytes(self) -> bytes:
        # Re-validate containment against original package root (symlink races)
        path = _validate_file_under_package(self.path, self.package_root)
        return path.read_bytes()


def collect_served_files(hub: Any) -> list[SafeStaticFile]:
    """Gather ``served_files()`` from all hub contributions; validate each."""
    out: list[SafeStaticFile] = []
    seen_urls: set[str] = set()
    for plugin in hub.iter_contributions():
        fn = getattr(plugin, "served_files", None)
        if not callable(fn):
            continue
        for item in fn() or ():
            if not isinstance(item, SafeStaticFile):
                raise UnsafeStaticError(
                    f"{getattr(plugin, 'name', plugin)!r} served_files must yield SafeStaticFile"
                )
            _validate_url(item.url)
            _validate_file_under_package(item.path, item.package_root)
            if item.url in seen_urls:
                raise UnsafeStaticError(f"duplicate static url: {item.url}")
            seen_urls.add(item.url)
            out.append(item)
    return out


def install_safe_static(app: Any, files: Sequence[SafeStaticFile]) -> int:
    """Register exact-path GET/HEAD routes. Never directory StaticFiles."""
    if not files:
        return 0

    try:
        from starlette.responses import Response
    except ImportError:
        try:
            from fastapi.responses import Response  # type: ignore
        except ImportError:
            return 0

    def _make_handler(entry: SafeStaticFile):
        async def _serve() -> Response:
            try:
                data = entry.read_bytes()
            except UnsafeStaticError:
                return Response("Forbidden", status_code=403)
            headers = {
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "public, max-age=3600",
                "X-ux-dom-Static": entry.plugin or "package",
            }
            return Response(
                content=data, media_type=entry.content_type, headers=headers
            )

        return _serve

    installed = 0
    for f in files:
        handler = _make_handler(f)
        try:
            if hasattr(app, "add_api_route"):
                app.add_api_route(
                    f.url,
                    handler,
                    methods=["GET", "HEAD"],
                    include_in_schema=False,
                    name=f"ux_dom_safe_static_{installed}",
                )
            elif hasattr(app, "add_route"):
                app.add_route(f.url, handler, methods=["GET", "HEAD"])
            else:
                continue
            installed += 1
        except Exception:
            pass
    return installed


def allowlist_summary() -> dict[str, Any]:
    """Introspection for doctor / docs."""
    return {
        "url_patterns": [
            "/ux-dom/static/<file>",
            "/ux-pkg/<plugin>/static/<file>",
            "/ux-channel/static/<file>",
        ],
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "blocked_fs_segments": sorted(_BLOCKED_FS_SEGMENTS),
        "code_extensions_denied": sorted(_CODE_EXTENSIONS),
    }
