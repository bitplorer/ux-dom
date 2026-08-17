"""Resolve the Tailwind standalone CLI for ``uxdom serve`` / ``dev`` / ``build``.

Order (first hit wins):

1. ``UXDOM_TAILWIND`` or ``TAILWINDCSS`` (path or command)
2. ``tailwindcss`` on PATH
3. ``pytailwindcss`` bundled standalone (``pip install pytailwindcss``)
4. local ``node_modules/.bin`` / ``@tailwindcss/cli`` (no implicit npx)
5. cached official standalone under ``$XDG_CACHE_HOME/ux-dom/``
6. (only if ``ensure=True``) download the official standalone CLI
7. (only if ``ensure=True`` and download failed) ``npx --yes @tailwindcss/cli``

Never copies library JS. CSS output stays in the app WebAssets tree.
"""
from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

__all__ = [
    "TAILWIND_STANDALONE_VERSION",
    "TailwindResolution",
    "argv_with_io",
    "cache_dir",
    "discover_css_io",
    "ensure_tailwind",
    "resolve_tailwind",
    "resolve_tailwind_argv",
    "standalone_asset_name",
]

# Pinned so serve/dev are reproducible. Override with UXDOM_TAILWIND_VERSION.
TAILWIND_STANDALONE_VERSION = "v4.1.12"


@dataclass(frozen=True)
class TailwindResolution:
    """Resolved CLI argv plus where it came from (doctor / banners)."""

    argv: list[str]
    source: str  # env | path | pytailwindcss | node | cache | download | npx


def cache_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or os.environ.get("UXDOM_CACHE")
    base = Path(root) if root else Path.home() / ".cache"
    return base / "ux-dom"


def standalone_asset_name() -> str:
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"aarch64", "arm64"} else "x64"
    if sysname == "linux":
        return f"tailwindcss-linux-{arch}"
    if sysname == "darwin":
        return f"tailwindcss-macos-{arch}"
    if sysname.startswith("win"):
        return "tailwindcss-windows-x64.exe"
    return f"tailwindcss-linux-{arch}"


def _split_cmd(value: str) -> list[str]:
    return [part for part in value.split() if part]


def _from_env() -> Optional[TailwindResolution]:
    raw = os.environ.get("UXDOM_TAILWIND") or os.environ.get("TAILWINDCSS")
    if not raw:
        return None
    parts = _split_cmd(raw)
    if not parts:
        return None
    if len(parts) == 1 and Path(parts[0]).is_file():
        return TailwindResolution(parts, "env")
    if shutil.which(parts[0]):
        return TailwindResolution(parts, "env")
    if Path(parts[0]).is_file():
        return TailwindResolution(parts, "env")
    return None


def _from_path() -> Optional[TailwindResolution]:
    found = shutil.which("tailwindcss")
    return TailwindResolution([found], "path") if found else None


def _from_pytailwindcss() -> Optional[TailwindResolution]:
    try:
        import pytailwindcss  # type: ignore[import-not-found]
    except Exception:
        return None
    for name in ("get_bin_path", "installed_path", "bin_path"):
        fn = getattr(pytailwindcss, name, None)
        if not callable(fn):
            continue
        try:
            path = fn()
        except Exception:
            continue
        if path and Path(str(path)).exists():
            return TailwindResolution([str(path)], "pytailwindcss")
    try:
        from pytailwindcss.bin import get_bin_path  # type: ignore[import-not-found]

        path = get_bin_path()
        if path and Path(str(path)).exists():
            return TailwindResolution([str(path)], "pytailwindcss")
    except Exception:
        pass
    # Module entry is enough — `python -m pytailwindcss` is the standalone CLI.
    return TailwindResolution([sys.executable, "-m", "pytailwindcss"], "pytailwindcss")


def _from_node_modules(start: Optional[Path] = None) -> Optional[TailwindResolution]:
    """Local install only — never implicit npx (that is an ensure last resort)."""
    cur = Path(start or Path.cwd()).resolve()
    for base in [cur, *cur.parents]:
        bin_ = base / "node_modules" / ".bin" / "tailwindcss"
        if bin_.is_file():
            return TailwindResolution([str(bin_)], "node")
        cli = base / "node_modules" / "@tailwindcss" / "cli"
        index = cli / "dist" / "index.mjs"
        if index.is_file() and shutil.which("node"):
            return TailwindResolution(
                [shutil.which("node") or "node", str(index)], "node"
            )
        if base == base.parent:
            break
    return None


def _cached_binary() -> Optional[Path]:
    name = standalone_asset_name()
    dest = cache_dir() / name
    if dest.is_file() and os.access(dest, os.X_OK):
        return dest
    return None


def _download_standalone(*, timeout: float = 60.0) -> Optional[Path]:
    if os.environ.get("UXDOM_TAILWIND_DOWNLOAD", "1") in {"0", "false", "False"}:
        return None
    name = standalone_asset_name()
    dest = cache_dir() / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    version = os.environ.get("UXDOM_TAILWIND_VERSION", TAILWIND_STANDALONE_VERSION)
    if version in {"latest", ""}:
        url = (
            "https://github.com/tailwindlabs/tailwindcss/releases/"
            f"latest/download/{name}"
        )
    else:
        url = (
            "https://github.com/tailwindlabs/tailwindcss/releases/download/"
            f"{version}/{name}"
        )
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ux-dom/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as fh:
            shutil.copyfileobj(resp, fh)
        tmp.replace(dest)
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return dest
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return None


def _from_npx() -> Optional[TailwindResolution]:
    npx = shutil.which("npx")
    if not npx:
        return None
    return TailwindResolution([npx, "--yes", "@tailwindcss/cli"], "npx")


def resolve_tailwind(
    *,
    cwd: Optional[Path] = None,
    ensure: bool = False,
) -> Optional[TailwindResolution]:
    """Return the first available Tailwind CLI, or None if unavailable."""
    cwd = Path(cwd).resolve() if cwd is not None else None
    for finder in (_from_env, _from_path, _from_pytailwindcss):
        hit = finder()
        if hit:
            return hit
    hit = _from_node_modules(cwd)
    if hit:
        return hit
    cached = _cached_binary()
    if cached:
        return TailwindResolution([str(cached)], "cache")
    if ensure:
        downloaded = _download_standalone()
        if downloaded:
            return TailwindResolution([str(downloaded)], "download")
        npx = _from_npx()
        if npx:
            return npx
    return None


def resolve_tailwind_argv(
    *,
    cwd: Optional[Path] = None,
    ensure: bool = False,
) -> Optional[list[str]]:
    """Return argv prefix for the Tailwind CLI, or None if unavailable."""
    hit = resolve_tailwind(cwd=cwd, ensure=ensure)
    return list(hit.argv) if hit else None


def ensure_tailwind(*, cwd: Optional[Path] = None) -> list[str]:
    """Like ``resolve_tailwind_argv(ensure=True)`` but raises if missing."""
    argv = resolve_tailwind_argv(cwd=cwd, ensure=True)
    if not argv:
        raise FileNotFoundError(
            "Tailwind CLI not found. Install one of: "
            "pip install pytailwindcss  ·  "
            "npm i -D @tailwindcss/cli  ·  "
            "or put `tailwindcss` on PATH. "
            "Serve can also download the official standalone CLI "
            "(set UXDOM_TAILWIND_DOWNLOAD=0 to disable)."
        )
    return argv


def argv_with_io(
    argv: Sequence[str],
    *,
    input_css: Path,
    output_css: Path,
    minify: bool = False,
    watch: bool = False,
) -> list[str]:
    out = list(argv)
    out.extend(["-i", str(input_css), "-o", str(output_css)])
    if minify:
        out.append("--minify")
    elif watch:
        out.append("--watch")
    return out


def discover_css_io(root: Path) -> Optional[tuple[Path, Path]]:
    """Resolve input/output CSS the same way create-app + WebAssets do."""
    assets = root / "assets"
    input_css = assets / "css" / "input.css"
    if not input_css.is_file():
        alt = assets / "input.css"
        if alt.is_file():
            input_css = alt
        elif (root / "app" / "tailwindcss.py").is_file():
            input_css = assets / "css" / "input.css"
        else:
            return None
    output_css = assets / "static" / "file" / "css" / "output.css"
    output_css.parent.mkdir(parents=True, exist_ok=True)
    return input_css, output_css
