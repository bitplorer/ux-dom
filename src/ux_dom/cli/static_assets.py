# Copyright (c) 2026 ux-dom
"""Static shipping — prefer **single copy** from installed packages.

Library JS (ux_dom XElement, ux-channel, …) is served from site-packages via
``served_files``. ``uxdom build`` verifies packages; it does **not**
duplicate them into ``assets/`` by default.

App-local files (Tailwind CSS, user images) still live under ``assets/``.
"""

from __future__ import annotations

import hashlib
import shutil
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class SyncedFile:
    rel: str
    path: Path
    sha256: str
    bytes: int
    action: str


@dataclass
class SyncReport:
    root: Path
    files: list[SyncedFile] = field(default_factory=list)
    mounts: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        # package mounts don't need files under root
        return True


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _default_hub(*, with_channel: bool = False):
    from ux_dom.plugins.hub import PluginHub
    from ux_dom.plugins.runtime import UxChannelRuntime, XElementRuntime

    hub = PluginHub()
    hub.add_contribution(XElementRuntime())  # package_mount default
    if with_channel:
        ch = UxChannelRuntime.optional()
        if ch is not None:
            hub.add_contribution(ch)
    return hub


def sync_runtime_assets(
    root: Path,
    *,
    force: bool = True,
    hub: Any = None,
    with_channel: bool = False,
    vendor: bool = False,
) -> SyncReport:
    """
    Prepare browser surface for an app root.

    Default (vendor=False)
        Ensure hub has XElementRuntime; record package mount URLs; materialize
        **only** contributions that still use webassets escape hatch.

    vendor=True
        Force materialize of any webassets-mode artifacts (discouraged dual copy).
    """
    root = Path(root).resolve()
    if hub is None:
        from ux_dom.plugins.hub import get_hub

        h = get_hub()
        if not h.contributions:
            h = _default_hub(with_channel=with_channel)
        hub = h

    report = SyncReport(root=root)
    try:
        for f in hub.served_static_files():
            report.mounts.append((f.url, str(f.path)))
            report.notes.append(f"safe file {f.url} → {f.path.name}")
    except Exception as e:
        report.notes.append(f"served_static_files: {e}")

    # Only materialize non-empty artifacts (explicit webassets escape hatch)
    rep = hub.materialize(root)
    for f in rep.files:
        report.files.append(
            SyncedFile(
                rel=f.disk_path,
                path=f.path,
                sha256=f.sha256,
                bytes=f.size,
                action=f.action,
            )
        )
    if not report.mounts and not report.files:
        report.notes.append("no package mounts or webassets artifacts on hub")
    return report


def collect_package_files(root: Path) -> list[Path]:
    root = Path(root).resolve()
    files: list[Path] = []
    exclude = {
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        ".pytest_cache",
        "node_modules",
        ".mypy_cache",
        "dist",
        ".ux_dom-dist",
    }

    def skip(p: Path) -> bool:
        try:
            rel = p.relative_to(root)
        except ValueError:
            return True
        return any(part in exclude or part.endswith(".pyc") for part in rel.parts)

    for base in ("app", "assets"):
        d = root / base
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file() and not skip(p):
                    files.append(p)
    for name in (
        "requirements.txt",
        "pyproject.toml",
        "README.md",
        "tailwind.config.js",
        "Dockerfile",
        "fly.toml",
        "render.yaml",
        "railway.json",
        ".dockerignore",
    ):
        p = root / name
        if p.is_file():
            files.append(p)
    deploy = root / "deploy"
    if deploy.is_dir():
        for p in deploy.rglob("*"):
            if p.is_file() and not skip(p):
                files.append(p)
    return sorted(set(files), key=lambda p: str(p.relative_to(root)))


def write_runnable_package(
    root: Path,
    *,
    out_dir: Optional[Path] = None,
    name: Optional[str] = None,
    archive: bool = False,
) -> Path:
    """
    Runnable app tree. Library JS is **not** vendored — install via pip
    (requirements.txt). Package mounts resolve from site-packages at runtime.
    """
    import json

    root = Path(root).resolve()
    pkg_name = name or root.name
    dist_root = Path(out_dir) if out_dir else root / "dist"
    dest = dist_root / pkg_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    sync = sync_runtime_assets(root, force=True)
    files = collect_package_files(root)
    manifest_files = []
    for src in files:
        rel = src.relative_to(root)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        data = src.read_bytes()
        manifest_files.append(
            {
                "path": str(rel).replace("\\", "/"),
                "sha256": _sha256(data),
                "bytes": len(data),
            }
        )

    run_sh = dest / "run.sh"
    run_sh.write_text(
        """#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-.}:."
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
if [ -d .venv ]; then
  . .venv/bin/activate
fi
# Library JS (x_element.js, ux-channel) comes from pip packages — single copy.
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
""",
        encoding="utf-8",
    )
    run_sh.chmod(0o755)

    (dest / "README.RUN.txt").write_text(
        f"""ux-dom runnable package — {pkg_name}
Generated: {datetime.now(timezone.utc).isoformat()}

Library JavaScript is NOT duplicated into assets/.
Install deps (ux_dom, ux-channel, …) then run — StaticFiles mounts
serve JS from site-packages (single copy).

  pip install -r requirements.txt
  ./run.sh

Package static mounts recorded at build:
{chr(10).join(f'  {p} → {d}' for p, d in sync.mounts) or '  (from App hub at runtime)'}
""",
        encoding="utf-8",
    )

    # ensure requirements mention ux_dom
    req = dest / "requirements.txt"
    if not req.is_file():
        req.write_text("ux-dom>=0.1.0\nfastapi\nuvicorn[standard]\n", encoding="utf-8")

    manifest = {
        "name": pkg_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root),
        "served_files": [
            {"prefix": p, "directory": d} for p, d in sync.mounts
        ],
        "webassets_copies": [
            {"rel": f.rel, "sha256": f.sha256, "action": f.action} for f in sync.files
        ],
        "files": manifest_files,
        "entrypoint": "app.main:app",
        "static_model": "single_copy_from_site_packages",
        "x_element_js_url": "/ux-dom/static/x_element.js",
    }
    (dest / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    if not archive:
        return dest

    dist_root.mkdir(parents=True, exist_ok=True)
    tar_path = dist_root / f"{pkg_name}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(dest, arcname=pkg_name)
    return tar_path
